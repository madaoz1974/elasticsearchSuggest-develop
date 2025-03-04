#!/usr/bin/env python3
"""
Azure SQL DatabaseよりKeywordとhasutaguを抽出してElasticSearchのindex生成するスクリプト
"""
import sys
import traceback
import time
import os

print("="*80)
print("Azure SQL DatabaseよりKeywordとhasutaguを抽出してElasticSearchのindex生成するスクリプト開始")
print("Python バージョン:", sys.version)
print("現在の作業ディレクトリ:", os.getcwd())
print("環境変数:")
for key, value in os.environ.items():
    if key.startswith(("SQL_", "ELASTICSEARCH_")):
        # パスワードは表示しない
        if "PASSWORD" in key:
            print(f"  {key}: ********")
        else:
            print(f"  {key}: {value}")
print("="*80)

try:
    print("index_data.pyを実行します...")
    # オリジナルのスクリプトをインポート
    import index_data
    print("index_data.pyの実行が完了しました")
except Exception as e:
    print("エラーが発生しました:")
    print(f"エラータイプ: {type(e).__name__}")
    print(f"エラーメッセージ: {e}")
    print("\n詳細なスタックトレース:")
    traceback.print_exc()
    
print("="*80)
print("デバッグラッパースクリプト終了")
print("コンテナは実行を継続します...")
print("(Ctrl+Cで強制終了できます)")

# コンテナがすぐに終了しないようにする
while True:
    time.sleep(60)