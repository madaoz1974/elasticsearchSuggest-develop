from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT
import re
import logging
import traceback
import os
from elasticsearch import Elasticsearch

# Elasticsearch設定
es = Elasticsearch(['http://localhost:9200'])

app = Flask(__name__)

# キーワード抽出クラス
class KeywordExtractor:
    def __init__(self, model_name='sonoisa/sentence-bert-base-ja-mean-tokens'):
        self.model = SentenceTransformer(model_name)
        self.kw_model = KeyBERT(model=self.model)

    def extract_keywords(self, text, top_n=5):
        keywords = self.kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), top_n=top_n)
        return [kw for kw, _ in keywords]

# ルート設定
@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json()
    results = []

    for record in data['values']:
        text_data = record['data']['Text']
        hashtags = re.findall(r'#\w+', text_data)
        keywords = KeywordExtractor().extract_keywords(text_data)

        results.append({
            'recordId': record['recordId'],
            'data': {
                'HashTags': ' '.join(hashtags),
                'Keywords': ' '.join(keywords)
            }
        })

    return jsonify({'values': results})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
