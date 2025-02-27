import pyodbc
import elasticsearch
from elasticsearch import helpers
import os
import urllib3
import warnings

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
# 接続タイムアウトの増加と、verify_certs=Falseの追加
es_host = os.environ['ELASTICSEARCH_HOST']
print(f"Connecting to Elasticsearch at {es_host}...")

# HTTPかHTTPSかの確認
is_https = es_host.startswith('https://')

try:
    # タイムアウト設定を増やし、HTTPSの場合は証明書検証を無効化
    if is_https:
        es = elasticsearch.Elasticsearch(
            [es_host], 
            timeout=30, 
            max_retries=5, 
            retry_on_timeout=True,
            verify_certs=False,  # 自己署名証明書や証明書検証の問題を回避
        )
    else:
        es = elasticsearch.Elasticsearch(
            [es_host], 
            timeout=30, 
            max_retries=5, 
            retry_on_timeout=True
        )
    
    # 接続テスト
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

print("Building actions for bulk import...")
actions = [
    {
        "_index": "msprdb-index",
        "_source": dict(zip(columns, row))
    }
    for row in cursor.fetchall()
]

# デバッグ情報: アクションの構築が成功したか確認
print(f"Built {len(actions)} actions for bulk import.")

if len(actions) > 0:
    # バルクインポートを実行
    print("Starting bulk import...")
    helpers.bulk(es, actions)
    print("Data import completed.")
else:
    print("No data to import.")

# 接続のクローズ
conn.close()
print("SQL connection closed.")