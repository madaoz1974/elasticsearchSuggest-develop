# ベースイメージをDebian 11（bullseye）に指定  
FROM --platform=linux/amd64 python:3.9-slim-bullseye  
  
# 環境変数の設定  
ENV DEBIAN_FRONTEND=noninteractive  
ENV DEBCONF_NOWARNINGS=yes  
ENV PATH="/opt/mssql-tools/bin:${PATH}"  
ENV PYTHONUNBUFFERED=1  
  
# 作業ディレクトリの設定  
WORKDIR /app  
  
# 必要なファイルをコピー  
COPY requirements.txt .  
COPY install_msodbc.sh .  
  
# install_msodbc.shに実行権限を付与  
RUN chmod +x ./install_msodbc.sh  
  
# msodbcsql17のインストール
RUN ./install_msodbc.sh  
  
# 必要なパッケージのインストール（一部を分離して効率化）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libmecab-dev \
        mecab \
        mecab-ipadic \
        swig \
        pkg-config \
        fontconfig \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのインストール  
RUN pip install --upgrade pip && \  
    pip install --no-cache-dir -r requirements.txt  
  
# アプリケーションファイルをコピー（最後に配置）
COPY index_data.py .
COPY build_wrapper.py .
  
# コンテナ起動時に実行するコマンド  
CMD ["python", "-v", "/app/index_data.py"]