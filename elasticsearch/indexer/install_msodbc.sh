#!/bin/bash  
  
# 必要なライブラリをインストール  
apt-get update && \  
    apt-get install -y apt-utils apt-transport-https gnupg curl  
  
# Microsoftのキーとリポジトリを追加  
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -  
curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list  
  
# パッケージリストの更新とインストール  
apt-get update  
ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools unixodbc-dev  