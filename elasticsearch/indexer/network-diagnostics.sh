#!/bin/bash

echo "============ ネットワーク診断 ============"
echo "現在の時刻: $(date)"

# 必要なツールのインストール
apt-get update && apt-get install -y curl net-tools dnsutils iputils-ping traceroute

# 環境変数の取得
ES_HOST=$(echo $ELASTICSEARCH_HOST | sed 's|^.*://||' | sed 's|:[0-9]*$||')
ES_PORT=$(echo $ELASTICSEARCH_HOST | grep -o ':[0-9]*$' | sed 's|:||')
if [ -z "$ES_PORT" ]; then
  if [[ $ELASTICSEARCH_HOST == https://* ]]; then
    ES_PORT=443
  else
    ES_PORT=80
  fi
fi

echo "ホスト名: $ES_HOST"
echo "ポート: $ES_PORT"

# DNSルックアップ
echo -e "\n===== DNSルックアップ ====="
nslookup $ES_HOST

# pingテスト
echo -e "\n===== Pingテスト ====="
ping -c 4 $ES_HOST

# トレースルート
echo -e "\n===== トレースルート ====="
traceroute $ES_HOST

# ポート接続テスト
echo -e "\n===== ポート接続テスト (nc) ====="
apt-get install -y netcat
timeout 5 nc -zv $ES_HOST $ES_PORT

# curlでの接続テスト
echo -e "\n===== HTTP接続テスト ====="
curl -v -k -m 10 http://$ES_HOST:$ES_PORT || echo "HTTP接続失敗"

echo -e "\n===== HTTPS接続テスト ====="
curl -v -k -m 10 https://$ES_HOST:$ES_PORT || echo "HTTPS接続失敗"

echo -e "\n===== ネットワーク情報 ====="
ip addr show
route -n

echo "========== 診断完了 =========="