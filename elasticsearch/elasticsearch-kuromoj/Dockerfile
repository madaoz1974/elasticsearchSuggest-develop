FROM docker.elastic.co/elasticsearch/elasticsearch:7.10.0

# kuromojiプラグインをインストール
RUN elasticsearch-plugin install analysis-kuromoji

# 設定をコピー
COPY elasticsearch.yml /usr/share/elasticsearch/config/

# 権限を設定
USER root
RUN chown -R elasticsearch:elasticsearch /usr/share/elasticsearch/config/
USER elasticsearch