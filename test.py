import pandas as pd
import faiss
import numpy as np
from neo4j import GraphDatabase
from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from sentence_transformers import SentenceTransformer, util
import json

# ตั้งค่าโมเดล SentenceTransformer
model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2')

# เชื่อมต่อ Neo4j
URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "password")

def run_query(query, parameters=None):
   with GraphDatabase.driver(URI, auth=AUTH) as driver:
       driver.verify_connectivity()
       with driver.session() as session:
           result = session.run(query, parameters)
           return [record for record in result]
   driver.close()

# ดึงข้อมูลข้อความจากฐานข้อมูล Neo4j
cypher_query = '''
MATCH (n:Greeting) RETURN n.name as name, n.msg_reply as reply;
'''
greeting_corpus = []
greeting_vec = None
results = run_query(cypher_query)
for record in results:
   greeting_corpus.append(record['name'])

greeting_corpus = list(set(greeting_corpus))  # เอาข้อความมาใส่ใน corpus
print(greeting_corpus)

# ฟังก์ชันคำนวณความคล้ายของข้อความ
def compute_similar(corpus, sentence):
   a_vec = model.encode([corpus], convert_to_tensor=True, normalize_embeddings=True)
   b_vec = model.encode([sentence], convert_to_tensor=True, normalize_embeddings=True)
   similarities = util.cos_sim(a_vec, b_vec)
   return similarities

# ค้นหาข้อความตอบกลับใน Neo4j
def neo4j_search(neo_query):
   results = run_query(neo_query)
   for record in results:
       response_msg = record['reply']
   return response_msg

# ฟังก์ชันคำนวณและหาข้อความตอบกลับ
def compute_response(sentence):
    greeting_vec = model.encode(greeting_corpus, convert_to_tensor=True, normalize_embeddings=True)
    ask_vec = model.encode(sentence, convert_to_tensor=True, normalize_embeddings=True)
    
    # Compute cosine similarities
    greeting_scores = util.cos_sim(greeting_vec, ask_vec)
    greeting_scores_list = greeting_scores.tolist()
    greeting_np = np.array(greeting_scores_list)
    
    max_greeting_score = np.argmax(greeting_np)
    Match_greeting = greeting_corpus[max_greeting_score]
    
    # ตรวจสอบคะแนนความเหมือน หากสูงกว่า 0.5 ให้ดึงข้อความตอบกลับจาก Neo4j
    if greeting_np[np.argmax(greeting_np)] > 0.5:
        My_cypher = f"MATCH (n:Greeting) WHERE n.name ='{Match_greeting}' RETURN n.msg_reply AS reply"
        my_msg = neo4j_search(My_cypher)
        return my_msg
    else:
        return "ขอโทษ ฉันไม่เข้าใจคำถามของคุณ"

# สร้าง Flask app
app = Flask(__name__)

@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)  # รับข้อมูลจาก Line API
    try:
        json_data = json.loads(body)  # แปลงข้อมูลที่รับมาเป็น JSON
        access_token = 'rvVY90zi7+UL80fU6aQbDj+itnTfPGf+UXv5JyOLAgjxX6xpTzwGNkRAU8b901gGXLop3vOBCfXotyEvhxyYCqAOcuMWOh1x1gCuMDQSHJhiQDpZB1lp4CYIDVN/3hJLuBGMBgkMw7s+qDbONAqySAdB04t89/1O/w1cDnyilFU='
        secret = '0d1f927f756f8c9e7aafb7715d8b18c8'
        line_bot_api = LineBotApi(access_token)
        handler = WebhookHandler(secret)
        signature = request.headers['X-Line-Signature']
        handler.handle(body, signature)

        # ข้อความที่ได้รับจากผู้ใช้
        msg = json_data['events'][0]['message']['text']
        tk = json_data['events'][0]['replyToken']
        
        # คำนวณและค้นหาข้อความตอบกลับ
        response_msg = compute_response(msg)
        
        # ส่งข้อความตอบกลับไปยัง Line
        line_bot_api.reply_message(tk, TextSendMessage(text=response_msg))
        print(msg, tk)
    except Exception as e:
        print(f"Error: {e}")
        print(body)  # ในกรณีที่เกิดข้อผิดพลาด

    return 'OK'

if __name__ == '__main__':
   # For Debugging
   app.run(port=5000)