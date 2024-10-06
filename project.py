from neo4j import GraphDatabase
from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from sentence_transformers import SentenceTransformer, util
import numpy as np
import faiss  # Import FAISS for efficient similarity search
import json
import requests
import datetime  # เพื่อใช้ในการบันทึก timestamp

# Load the sentence transformer model
model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2')

# Neo4j connection details
URI = "neo4j://localhost"
AUTH = ("neo4j", "password")

def run_query(query, parameters=None):
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

cypher_query = '''
MATCH (n:Greeting) RETURN n.name as name, n.msg_reply as reply;
'''

# Retrieve greetings from the Neo4j database
greeting_corpus = []
results = run_query(cypher_query)
for record in results:
    greeting_corpus.append(record['name'])

# Ensure corpus is unique
greeting_corpus = list(set(greeting_corpus))
print(greeting_corpus)

# Encode the greeting corpus into vectors using the sentence transformer model
greeting_vecs = model.encode(greeting_corpus, convert_to_numpy=True, normalize_embeddings=True)

# Initialize FAISS index
d = greeting_vecs.shape[1]  # Dimension of vectors
index = faiss.IndexFlatL2(d)  # L2 distance index (cosine similarity can be used with normalization)
index.add(greeting_vecs)  # Add vectors to FAISS index

def compute_similar_faiss(sentence):
    # Encode the query sentence
    ask_vec = model.encode([sentence], convert_to_numpy=True, normalize_embeddings=True)
    # Search FAISS index for nearest neighbor
    D, I = index.search(ask_vec, 1)  # Return top 1 result
    return D[0][0], I[0][0]

def neo4j_search(neo_query):
    # ดึงข้อมูลการตอบกลับจาก Neo4j
    results = run_query(neo_query)
    for record in results:
        response_msg = record['reply']
    return response_msg

def compute_response(sentence):
    score, index = compute_similar_faiss(sentence)
    if score > 0.5:  # กำหนด threshold ให้ค่าความคล้ายมากกว่า 0.5
        Match_greeting = greeting_corpus[index] # คำทักทายที่คล้ายกับข้อความที่รับเข้ามา
        My_cypher = f"MATCH (n:Greeting) WHERE n.name = '{Match_greeting}' RETURN n.msg_reply as reply" # สร้างคำสั่ง Cypher สำหรับค้นหาข้อความตอบกลับ
        my_msg = neo4j_search(My_cypher) # ค้นหาข้อความตอบกลับจาก Neo4j
    else:
        my_msg = "ฉันไม่เข้าใจคำถาม" # ถ้าค่าความคล้ายต่ำกว่า threshold จะตอบว่าไม่เข้าใจคำถาม
    print(my_msg) # แสดงข้อความตอบกลับ
    return my_msg # ส่งข้อความตอบกลับ

def save_chat_history(user_id, user_message, bot_message):
    # บันทึกประวัติการคุย และบันทึกการตอบกลับใน Neo4j พร้อม relationship
    timestamp = datetime.datetime.now().isoformat()  # ได้ timestamp ในรูปแบบ ISO
    query = '''
    MERGE (u:User {user_id: $user_id})
    CREATE (c:Chat {message: $user_message, timestamp: $timestamp})
    CREATE (r:Response {reply: $bot_message, timestamp: $timestamp})
    MERGE (u)-[:SENT]->(c)
    MERGE (c)-[:GENERATED]->(r)
    '''
    parameters = {
        'user_id': user_id,
        'user_message': user_message,
        'bot_message': bot_message,
        'timestamp': timestamp
    }
    run_query(query, parameters)

app = Flask(__name__)

@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)
    try:
        json_data = json.loads(body)
        access_token = 'rvVY90zi7+UL80fU6aQbDj+itnTfPGf+UXv5JyOLAgjxX6xpTzwGNkRAU8b901gGXLop3vOBCfXotyEvhxyYCqAOcuMWOh1x1gCuMDQSHJhiQDpZB1lp4CYIDVN/3hJLuBGMBgkMw7s+qDbONAqySAdB04t89/1O/w1cDnyilFU='
        secret = '0d1f927f756f8c9e7aafb7715d8b18c8'
        line_bot_api = LineBotApi(access_token)
        handler = WebhookHandler(secret)
        signature = request.headers['X-Line-Signature']
        handler.handle(body, signature)
        msg = json_data['events'][0]['message']['text']
        tk = json_data['events'][0]['replyToken']
        user_id = json_data['events'][0]['source']['userId']  # ดึง user_id จาก event
        response_msg = compute_response(msg)
        
        # บันทึกประวัติการคุยและการตอบกลับใน Neo4j
        save_chat_history(user_id, msg, response_msg)

        # ส่งข้อความตอบกลับผู้ใช้
        line_bot_api.reply_message(tk, TextSendMessage(text=response_msg))
        print(msg, tk)
    except InvalidSignatureError:
        return jsonify({'status': 'Invalid signature'}), 400
    except Exception as e:
        print(body)
        print(f"Error: {e}")
        return jsonify({'status': 'Error', 'message': str(e)}), 500
    return 'OK'

if __name__ == '__main__':
    app.run(port=5000)