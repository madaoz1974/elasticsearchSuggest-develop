#!/usr/bin/env python
"""
Buildラッパースクリプト - 主要コンポーネントのテストと診断を行います
"""

import os
import sys
import subprocess
import platform
import importlib.util

def check_environment():
    """システム環境とPythonバージョンを確認"""
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Architecture: {platform.machine()}")
    
    # 環境変数の確認
    required_vars = ['SQL_SERVER', 'SQL_DATABASE', 'SQL_USER', 'SQL_PASSWORD', 'ELASTICSEARCH_HOST']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"WARNING: Missing required environment variables: {', '.join(missing_vars)}")
    else:
        print("All required environment variables are set.")

def check_odbc():
    """ODBC ドライバのインストール状態を確認"""
    try:
        print("Checking ODBC drivers...")
        result = subprocess.run(['odbcinst', '-q', '-d'], capture_output=True, text=True)
        if result.returncode == 0:
            print("ODBC drivers found:")
            print(result.stdout)
        else:
            print("Error checking ODBC drivers:")
            print(result.stderr)
    except FileNotFoundError:
        print("odbcinst command not found. ODBC utilities may not be installed.")

def check_mecab():
    """MeCabのインストール状態を確認"""
    try:
        import MeCab
        print("MeCab is installed.")
        
        # MeCabのバージョンを取得
        tagger = MeCab.Tagger("-v")
        tagger.parse("")  # バグ回避のために一度パース
        print("MeCab is working correctly.")
        
        # 辞書ディレクトリの確認
        try:
            # mecabrcファイルのパスを確認
            mecabrc_path = "/usr/local/etc/mecabrc"
            if os.path.exists(mecabrc_path):
                with open(mecabrc_path, 'r') as f:
                    content = f.read()
                    print(f"mecabrc content: {content}")
            else:
                print(f"mecabrc file not found at {mecabrc_path}")
        except Exception as e:
            print(f"Error checking mecabrc: {e}")
            
    except ImportError:
        print("MeCab is not installed or not properly configured.")
    except Exception as e:
        print(f"Error with MeCab: {e}")

def check_elasticsearch():
    """Elasticsearchへの接続を確認"""
    try:
        import elasticsearch
        print("Elasticsearch library is installed.")
        
        # ES_HOSTが設定されているか確認
        es_host = os.environ.get('ELASTICSEARCH_HOST')
        if not es_host:
            print("ELASTICSEARCH_HOST is not set.")
            return
            
        print(f"Attempting to connect to Elasticsearch at {es_host}...")
        try:
            es = elasticsearch.Elasticsearch(
                [es_host], 
                timeout=10,
                verify_certs=False
            )
            
            if es.ping():
                print("Successfully connected to Elasticsearch!")
                info = es.info()
                print(f"Elasticsearch version: {info.get('version', {}).get('number')}")
            else:
                print("Could not ping Elasticsearch.")
        except Exception as e:
            print(f"Error connecting to Elasticsearch: {e}")
        
    except ImportError:
        print("Elasticsearch library is not installed.")

def check_python_dependencies():
    """必要なPythonパッケージがインストールされているか確認"""
    required_packages = ["pyodbc", "elasticsearch", "urllib3", "MeCab"]
    
    for package in required_packages:
        if importlib.util.find_spec(package):
            print(f"✓ {package} is installed")
        else:
            print(f"✗ {package} is NOT installed")

def main():
    """メイン実行関数"""
    print("=" * 50)
    print("Docker Container Diagnostics")
    print("=" * 50)
    
    # 各チェックを実行
    check_environment()
    print("\n" + "-" * 50)
    
    check_python_dependencies()
    print("\n" + "-" * 50)
    
    check_odbc()
    print("\n" + "-" * 50)
    
    check_mecab()
    print("\n" + "-" * 50)
    
    check_elasticsearch()
    print("\n" + "-" * 50)
    
    print("Diagnostics completed.")
    
    # インタラクティブシェルの開始
    print("\nStarting interactive Python shell. Press Ctrl+D to exit.")
    import code
    code.interact(local=locals())

if __name__ == "__main__":
    main()