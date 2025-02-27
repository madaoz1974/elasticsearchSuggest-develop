import pyodbc
import elasticsearch
from elasticsearch import helpers
import os

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
es = elasticsearch.Elasticsearch([os.environ['ELASTICSEARCH_HOST']])

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
if not es.indices.exists(index='msprdb-index'):
    print("Index does not exist. Creating index...")
    es.indices.create(index='msprdb-index', body=index_settings)
    print("Index created.")
else:
    print("Index already exists.")

# データ取得およびインポート
cursor = conn.cursor()
cursor.execute("SELECT * FROM Mspr.PostCommentView")
columns = [column[0] for column in cursor.description]

actions = [
    {
        "_index": "msprdb-index",
        "_source": dict(zip(columns, row))
    }
    for row in cursor.fetchall()
]

# デバッグ情報: アクションの構築が成功したか確認
print(f"Built {len(actions)} actions for bulk import.")

# バルクインポートを実行
helpers.bulk(es, actions)
print("Data import completed.")
