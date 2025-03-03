import pyodbc
import elasticsearch
from elasticsearch import helpers
import os
import urllib3
import warnings
import re
import json

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

# インデックス設定
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
            "HashTags": {"type": "text", "analyzer": "ja_analyzer"},
            "Keywords": {"type": "text", "analyzer": "ja_analyzer"},
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

# デバッグ情報: インデックスが存在するか確認
print("Checking if index exists...")
try:
    if not es.indices.exists(index='msprdb-index'):
        print("Index does not exist. Creating index...")
        es.indices.create(index='msprdb-index', body=index_settings)
        print("Index created.")
    else:
        print("Index already exists.")
except Exception as e:
    print(f"Error checking/creating index: {e}")
    raise

# データ取得およびインポート
cursor = conn.cursor()
print("Executing SQL query...")
cursor.execute("SELECT * FROM Mspr.PostCommentView")
columns = [column[0] for column in cursor.description]
rows = cursor.fetchall()

print("Building actions for bulk import...")
actions = []
for row in rows:
    # 行データを辞書に変換
    row_dict = dict(zip(columns, row))
    
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
    
    actions.append({
        "_index": "msprdb-index",
        "_source": row_dict
    })

# デバッグ情報: アクションの構築が成功したか確認
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