#!/bin/bash  
  
set -e  
set -x  

echo "### APT キャッシュとロックのクリア ###"  
rm -rf /var/lib/apt/lists/*  
rm -f /var/cache/apt/*.bin  
rm -f /var/lib/apt/lists/lock  
rm -f /var/cache/apt/archives/lock  
rm -rf /var/lib/dpkg/lock*  
dpkg --configure -a  

echo "### 更新と基本パッケージのインストール ###"
apt-get update -o Debug::pkgAcquire=true -o Debug::pkgAcquire::Worker=true
apt-get install -y --no-install-recommends apt-transport-https -o Debug::pkgAcquire=true -o Debug::pkgAcquire::Worker=true
apt-get install -y --no-install-recommends curl -o Debug::pkgAcquire=true -o Debug::pkgAcquire::Worker=true
apt-get install -y --no-install-recommends ca-certificates -o Debug::pkgAcquire=true -o Debug::pkgAcquire::Worker=true
apt-get install -y --no-install-recommends gnupg -o Debug::pkgAcquire=true -o Debug::pkgAcquire::Worker=true
apt-get install -y --no-install-recommends dirmngr -o Debug::pkgAcquire=true -o Debug::pkgAcquire::Worker=true
apt-get install -y --no-install-recommends pinentry-curses -o Debug::pkgAcquire=true -o Debug::pkgAcquire::Worker=true
apt-get install -y --no-install-recommends lsb-release -o Debug::pkgAcquire=true -o Debug::pkgAcquire::Worker=true
  
echo "### MicrosoftのGPGキーをインポート ###"  
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-archive-keyring.gpg  
  
echo "### Microsoftリポジトリを追加 ###"  
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list  
  
echo "### パッケージリストを更新 ###"  
apt-get update  
  
echo "### msodbcsql18 と mssql-tools のインストール ###"  
ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 mssql-tools unixodbc-dev  
  
echo "### クリーンアップ ###"  
apt-get clean  
rm -rf /var/lib/apt/lists/*  