import pyodbc
import elasticsearch
from elasticsearch import helpers
import os
import urllib3
import warnings
import re
import json
from collections import Counter
import MeCab  # 日本語形態素解析用

# 自己署名証明書の警告を無効化（本番環境では注意）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# SQL Server 接続設定
conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + os.environ['SQL_SERVER'] + ';DATABASE=' + os.environ['SQL_DATABASE'] + ';UID=' + os.environ['SQL_USER'] + ';PWD=' + os.environ['SQL_PASSWORD']

# デバッグ情報: SQL接続開始
print("Connecting to SQL Server...")

try:
    conn = pyodbc.connect(conn_str)
    print("Successfully connected to SQL Server.")
except Exception as e:
    print(f"Failed to connect to SQL Server: {e}")
    raise

# ElasticSearch設定
# 環境変数からホスト名を取得し、ポート443を指定
es_host = os.environ['ELASTICSEARCH_HOST']
print(f"Original Elasticsearch host: {es_host}")

# URLからスキームとホスト名を抽出
url_match = re.match(r'(https?://)([^:/]+)(:[0-9]+)?(/.*)?', es_host)
if url_match:
    scheme = url_match.group(1)
    hostname = url_match.group(2)
    # ポート443を明示的に使用
    es_conn_url = f"{scheme}{hostname}:443"
    print(f"Using Elasticsearch at: {es_conn_url}")
else:
    es_conn_url = es_host
    print(f"Could not parse URL, using as is: {es_conn_url}")

try:
    # ポート443への接続を試みる
    es = elasticsearch.Elasticsearch(
        [es_conn_url], 
        timeout=30, 
        max_retries=5, 
        retry_on_timeout=True,
        verify_certs=False,  # 自己署名証明書の検証をスキップ
        # ポート番号のバリデーションを回避するためのカスタム設定
        port=443
    )
    
    # 接続テスト
    print("Testing Elasticsearch connection...")
    if es.ping():
        print("Successfully connected to Elasticsearch.")
    else:
        print("Could ping Elasticsearch, but no valid response received.")
except Exception as e:
    print(f"Failed to connect to Elasticsearch: {e}")
    raise

# インデックス設定 - keywordsフィールドも適切に設定
index_settings = {
    "settings": {
        "analysis": {
            "analyzer": {
                "ja_analyzer": {
                    "type": "custom",
                    "tokenizer": "kuromoji_tokenizer"
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "PostedNumber": {"type": "keyword"},
            "CreatedAt": {"type": "date"},
            "PostId": {"type": "keyword"},
            "PostedAt": {"type": "date"},
            "PostedUser": {"type": "keyword"},
            "Text": {"type": "text", "analyzer": "ja_analyzer"},
            "DeletedAt": {"type": "date"},
            "PostStatus": {"type": "integer"},
            # HashTagsフィールドとして明示的に定義
            "HashTags": {
                "type": "text", 
                "analyzer": "ja_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            # Keywordsフィールドとして明示的に定義
            "Keywords": {
                "type": "text", 
                "analyzer": "ja_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "Comments": {
                "type": "nested",
                "properties": {
                    "CommentNumber": {"type": "keyword"},
                    "CreatedAt": {"type": "date"},
                    "CommentId": {"type": "keyword"},
                    "CommentedUser": {"type": "keyword"},
                    "Text": {"type": "text", "analyzer": "ja_analyzer"},
                    "CommentedAt": {"type": "date"},
                    "DeletedAt": {"type": "date"}
                }
            }
        }
    }
}

# インデックスが存在するか確認と削除
index_name = 'msprdb-index'
if es.indices.exists(index=index_name):
    print(f"Index {index_name} already exists. Deleting index...")
    es.indices.delete(index=index_name)
    print(f"Index {index_name} deleted.")

# 新しいインデックスを作成
print(f"Creating index: {index_name}")
es.indices.create(index=index_name, body=index_settings)
print(f"Index {index_name} created.")

# MeCabの初期化  
print("Initializing MeCab for keyword extraction...")  
try:  
    # `dicdir` を `mecabrc` に設定済みのため、`-d` オプションを削除  
    mecab = MeCab.Tagger("-Ochasen")  
      
    # バグ回避のために一度パースを実行  
    mecab.parse("")  
    print("Successfully initialized MeCab.")  
except Exception as e:  
    print(f"Failed to initialize MeCab: {e}")  
    print("Falling back to simple keyword extraction method")  
    mecab = None  

# テキストからキーワードを抽出する関数
def extract_keywords(text, max_keywords=10):
    if not text:
        return []
    
    try:
        # MeCabを使った形態素解析による高度なキーワード抽出
        if mecab:
            # 形態素解析を実行
            parsed = mecab.parse(text)
            words = []
            
            # 名詞、動詞の基本形を抽出
            for line in parsed.split('\n'):
                if line == 'EOS' or line == '':
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 4:
                    word = parts[0]
                    pos = parts[3].split('-')[0]  # 品詞
                    
                    # 名詞、動詞、形容詞を抽出（一般的なキーワードは名詞が多い）
                    if pos in ['名詞', '動詞', '形容詞'] and len(word) > 1:
                        words.append(word)
            
            # 頻度でカウント
            word_counts = Counter(words)
            
            # 最も頻度の高いキーワードを返す
            return [word for word, count in word_counts.most_common(max_keywords)]
        else:
            # MeCabが使えない場合のフォールバック: 単純な分割と頻度カウント
            # 日本語と英語の混在テキストに対応
            words = []
            
            # 英数字を含む「単語」を抽出（正規表現で単語の区切りを検出）
            english_words = re.findall(r'[a-zA-Z0-9_]+', text)
            words.extend([w for w in english_words if len(w) > 1])
            
            # 日本語文字の塊を抽出
            japanese_chars = re.sub(r'[a-zA-Z0-9_\s.,!?()[\]{}:;"\'<>\/\\|@#$%^&*~`+=_-]', ' ', text)
            
            # 空白で分割して短すぎる単語を除外
            japanese_words = [w for w in japanese_chars.split() if len(w) > 1]
            words.extend(japanese_words)
            
            # 頻度でカウント
            word_counts = Counter(words)
            
            # 最も頻度の高いキーワードを返す
            return [word for word, count in word_counts.most_common(max_keywords)]
            
    except Exception as e:
        print(f"Error in keyword extraction: {e}")
        return []

# 文字列からハッシュタグを抽出する関数
def extract_hashtags(text):
    if not text:
        return []
    
    try:
        # #で始まる単語をハッシュタグとして抽出
        hashtags = re.findall(r'#(\w+)', text)
        return hashtags
    except Exception as e:
        print(f"Error in hashtag extraction: {e}")
        return []

# データ取得およびインポート
cursor = conn.cursor()
print("Executing SQL query...")
# 必要に応じて、KeywordsカラムがSQL側で正しく取得できるか確認するためのクエリを修正
cursor.execute("SELECT * FROM Mspr.PostCommentView")
columns = [column[0] for column in cursor.description]
rows = cursor.fetchall()

print("Building actions for bulk import...")
actions = []
for row in rows:
    # 行データを辞書に変換
    row_dict = dict(zip(columns, row))
    
    # データの前処理を行う
    
    # *** テキストからキーワードとハッシュタグを抽出 ***
    if 'Text' in row_dict and row_dict['Text']:
        text = row_dict['Text']
        
        # キーワードの抽出
        extracted_keywords = extract_keywords(text)
        
        # 既存のKeywordsフィールドがなければ作成、あれば上書き
        row_dict['Keywords'] = extracted_keywords
        
        # ハッシュタグの抽出
        extracted_hashtags = extract_hashtags(text)
        
        # 既存のHashTagsフィールドがなければ作成、あれば上書き
        if extracted_hashtags:
            row_dict['HashTags'] = extracted_hashtags
    
    # 既存のKeywordsフィールドが文字列であれば、適切に処理
    elif 'Keywords' in row_dict and row_dict['Keywords'] is not None:
        try:
            # カンマ区切りの場合、リストに変換
            if isinstance(row_dict['Keywords'], str):
                if ',' in row_dict['Keywords']:
                    row_dict['Keywords'] = [k.strip() for k in row_dict['Keywords'].split(',')]
                # JSON文字列の可能性があればパース
                elif row_dict['Keywords'].startswith('[') and row_dict['Keywords'].endswith(']'):
                    row_dict['Keywords'] = json.loads(row_dict['Keywords'])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse Keywords for PostId: {row_dict.get('PostId')}")
            # 問題がある場合でも、テキストとして保持
    
    # 既存のHashTagsフィールドが文字列であれば、適切に処理
    if 'HashTags' in row_dict and row_dict['HashTags'] is not None and not extracted_hashtags:
        try:
            # カンマ区切りの場合、リストに変換
            if isinstance(row_dict['HashTags'], str):
                if ',' in row_dict['HashTags']:
                    row_dict['HashTags'] = [h.strip() for h in row_dict['HashTags'].split(',')]
                # JSON文字列の可能性があればパース
                elif row_dict['HashTags'].startswith('[') and row_dict['HashTags'].endswith(']'):
                    row_dict['HashTags'] = json.loads(row_dict['HashTags'])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse HashTags for PostId: {row_dict.get('PostId')}")
            # 問題がある場合でも、テキストとして保持
    
    # Commentsフィールドが文字列であれば、JSONオブジェクトに変換
    if 'Comments' in row_dict and row_dict['Comments'] is not None:
        try:
            if isinstance(row_dict['Comments'], str):
                row_dict['Comments'] = json.loads(row_dict['Comments'])
            # JSON文字列でもオブジェクトでもない場合は空のリストに設定
            elif not isinstance(row_dict['Comments'], (list, dict)):
                row_dict['Comments'] = []
        except json.JSONDecodeError:
            print(f"Warning: Could not parse Comments JSON for PostId: {row_dict.get('PostId')}")
            # パースできない場合は空のリストに設定
            row_dict['Comments'] = []
    
    # デバッグ出力: Keywordsフィールドの値をサンプルログ
    if 'PostId' in row_dict and 'Keywords' in row_dict:
        # 1つめのデータだけログ出力
        if len(actions) == 0:
            print(f"Sample Keywords for PostId {row_dict['PostId']}: {row_dict.get('Keywords')}")
    
    actions.append({
        "_index": index_name,
        "_source": row_dict
    })

# デバッグ情報: インポートデータの数を表示
print(f"Built {len(actions)} actions for bulk import.")

if len(actions) > 0:
    # バルクインポートを実行
    print("Starting bulk import...")
    try:
        # チャンクサイズを小さくして処理
        success, failed = helpers.bulk(es, actions, chunk_size=100, max_retries=5, raise_on_error=False)
        print(f"Data import completed. Success: {success}, Failed: {len(failed) if failed else 0}")
        
        if failed:
            print(f"First few errors: {failed[:3]}")
    except Exception as e:
        print(f"Error during bulk import: {e}")
else:
    print("No data to import.")

# 接続のクローズ
conn.close()
print("SQL connection closed.")

# インデックス更新のために一時的に閉じる
print(f"Closing index {index_name} for updates...")
es.indices.close(index=index_name)

try:
    # テキスト解析用の日本語設定を更新
    print("Updating analysis settings...")
    analysis_settings = {
        "analysis": {
            "analyzer": {
                "ja_analyzer": {
                    "type": "custom",
                    "tokenizer": "kuromoji_tokenizer",
                    "filter": ["kuromoji_baseform", "kuromoji_part_of_speech", "ja_stop", "kuromoji_stemmer"]
                }
            },
            "filter": {
                "ja_stop": {
                    "type": "stop",
                    "stopwords": "_japanese_"
                }
            }
        }
    }
    
    es.indices.put_settings(body={"settings": analysis_settings}, index=index_name)
    print("Analysis settings updated.")
    
    # サジェスト機能のためのマッピング追加 - Keywordsフィールドも対象に
    print("Adding suggestion fields to mapping...")
    suggest_mapping = {
        "properties": {
            "Text": {
                "type": "text",
                "analyzer": "ja_analyzer",
                "fields": {
                    "suggest": {
                        "type": "completion",
                        "analyzer": "ja_analyzer"
                    }
                }
            },
            "Keywords": {
                "type": "text",
                "analyzer": "ja_analyzer",
                "fields": {
                    "suggest": {
                        "type": "completion",
                        "analyzer": "ja_analyzer"
                    }
                }
            },
            "HashTags": {
                "type": "text",
                "analyzer": "ja_analyzer",
                "fields": {
                    "suggest": {
                        "type": "completion",
                        "analyzer": "ja_analyzer"
                    }
                }
            },
            "Comments": {
                "type": "nested",
                "properties": {
                    "Text": {
                        "type": "text",
                        "analyzer": "ja_analyzer",
                        "fields": {
                            "suggest": {
                                "type": "completion",
                                "analyzer": "ja_analyzer"
                            }
                        }
                    }
                }
            }
        }
    }
    
    es.indices.put_mapping(body=suggest_mapping, index=index_name)
    print("Suggestion mappings added.")
    
    # ベクトル検索フィールドの追加（オプション：モデルが必要な場合）
    # Dense Vectorフィールドを追加する場合はコメントを解除
    """
    vector_mapping = {
        "properties": {
            "text_vector": {
                "type": "dense_vector",
                "dims": 768
            },
            "comments_vector": {
                "type": "dense_vector",
                "dims": 768
            }
        }
    }
    
    es.indices.put_mapping(body=vector_mapping, index=index_name)
    print("Vector fields added.")
    """
    
    # インデックスを再オープン
    print(f"Reopening index {index_name}...")
    es.indices.open(index=index_name)
    
    # インデックスのリフレッシュ
    print("Refreshing index...")
    es.indices.refresh(index=index_name)
    
    print("Index update completed successfully!")
    
except Exception as e:
    # エラーが発生した場合、インデックスを再オープンして終了
    print(f"Error during index update: {e}")
    try:
        es.indices.open(index=index_name)
        print(f"Index {index_name} reopened after error.")
    except Exception as reopen_error:
        print(f"Failed to reopen index: {reopen_error}")
    raise

# サジェストデータの準備
print("Updating documents with suggestion data...")

# バッチサイズ
BATCH_SIZE = 100

# スクロールを使用して全ドキュメントを取得
scroll_response = es.search(
    index=index_name,
    scroll='2m',
    size=BATCH_SIZE,
    body={"query": {"match_all": {}}}
)

# 初期スクロールID
scroll_id = scroll_response['_scroll_id']
documents_processed = 0

try:
    while True:
        # 結果を処理
        batch = []
        hits = scroll_response.get('hits', {}).get('hits', [])
        
        if not hits:
            break
            
        for hit in hits:
            doc = hit['_source']
            doc_id = hit['_id']
            
            # ドキュメントの更新操作を作成
            action = {
                "_op_type": "update",
                "_index": index_name,
                "_id": doc_id,
                "doc": {}
            }
            
            # サジェストデータを追加（必要なフィールドがある場合）
            if 'Text' in doc and doc['Text']:
                action['doc']['Text'] = doc['Text']
            
            # Keywordsフィールドの処理を追加
            if 'Keywords' in doc and doc['Keywords']:
                action['doc']['Keywords'] = doc['Keywords']
                
            # HashTagsフィールドの処理を追加
            if 'HashTags' in doc and doc['HashTags']:
                action['doc']['HashTags'] = doc['HashTags']
            
            batch.append(action)
        
        # バッチ更新を実行
        if batch:
            success, errors = helpers.bulk(es, batch, refresh=True)
            documents_processed += success
            print(f"Processed {documents_processed} documents...")
            
            if errors:
                print(f"Errors during bulk update: {errors}")
        
        # 次のバッチを取得
        scroll_response = es.scroll(scroll_id=scroll_id, scroll='2m')
        scroll_id = scroll_response['_scroll_id']
        
finally:
    # スクロールを解放
    es.clear_scroll(scroll_id=scroll_id)

print(f"Completed updating {documents_processed} documents.")
print("Done! Elasticsearch index is now ready for suggestions and vector search.")

# 実際にKeywordsフィールドが正しく格納されているか確認するためのクエリを実行
print("Checking if Keywords field is properly indexed...")
try:
    # サンプルクエリを実行
    sample_query = {
        "size": 5,
        "_source": ["PostId", "Keywords"],
        "query": {
            "exists": {
                "field": "Keywords"
            }
        }
    }
    
    result = es.search(index=index_name, body=sample_query)
    hit_count = result['hits']['total']['value'] if 'hits' in result and 'total' in result['hits'] else 0
    
    print(f"Found {hit_count} documents with Keywords field")
    
    # サンプルのドキュメントを表示
    if hit_count > 0:
        print("Sample documents with Keywords:")
        for hit in result['hits']['hits']:
            print(f"PostId: {hit['_source'].get('PostId')}, Keywords: {hit['_source'].get('Keywords')}")
except Exception as e:
    print(f"Error checking Keywords field: {e}")