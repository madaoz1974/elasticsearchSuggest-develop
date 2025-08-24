#!/bin/bash  
  
set -e  
  
# 必要なライブラリをインストール  
apt-get update
apt-get install -y apt-utils apt-transport-https gnupg curl lsb-release ca-certificates
  
# MicrosoftのGPGキーをインポート  
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg  
  
# Microsoftリポジトリを追加（Debian 11用）  
echo "deb [arch=amd64] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list
  
# パッケージリストを更新  
apt-get update  
  
# msodbcsql17 と mssql-tools のインストール  
ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools unixodbc-dev  

# クリーンアップ
apt-get clean && \
rm -rf /var/lib/apt/lists/*