ローカルでのデバッグコマンド
```bash
#!/bin/bash

# 1. デバッグモードでコンテナを起動
docker-compose -f docker-compose.yml up --build

# 2. 別のターミナルからコンテナに接続する場合
docker-compose -f docker-compose.yml exec indexer bash

# 3. コンテナ内でpdbを使ったデバッグ実行
# コンテナ内で実行:
python -m pdb /app/index_data.py

# 4. ログを確認する場合
docker-compose logs -f

# 5. 本番実行モード（バックグラウンド実行）
docker-compose up -d

# 6. 単一コマンドとして実行（デバッグ時に便利）
docker-compose run --rm indexer python /app/index_data.py

# 7. ビルドのみ実行
docker-compose build

# 8. コンテナ停止・削除
docker-compose down
```