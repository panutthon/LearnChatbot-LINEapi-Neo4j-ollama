from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from sentence_transformers import SentenceTransformer, util,InputExample
from sentence_transformers import models, losses
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from torch.utils.data import DataLoader
import numpy as np
import json

# โหลดโมเดล BERT สำหรับภาษาไทย
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# สร้างคลังข้อความคำถาม-คำตอบ
qa_pairs = [
    ("สวัสดี", "สวัสดีครับ ยินดีต้อนรับสู่ระบบแชทบอท"),
    ("คุณเป็นอย่างไรบ้าง", "ผมสบายดีครับ แล้วคุณล่ะครับ เป็นอย่างไรบ้าง?"),
    ("วันนี้อากาศเป็นยังไง", "วันนี้อากาศดีครับ คุณรู้สึกอย่างไรกับอากาศวันนี้บ้างครับ?"),
    ("คุณทำอะไรอยู่", "ผมกำลังช่วยตอบคำถามและพูดคุยกับคุณอยู่ครับ มีอะไรให้ช่วยไหมครับ?"),
    ("ขอบคุณ", "ด้วยความยินดีครับ หากมีอะไรให้ช่วยเหลือเพิ่มเติม บอกผมได้เลยนะครับ"),
    ("คุณเป็นใคร", "ผมเป็นแชทบอท AI ที่ถูกสร้างขึ้นเพื่อช่วยตอบคำถามและพูดคุยกับคุณครับ"),
    ("คุณทำอะไรได้บ้าง", "ผมสามารถช่วยตอบคำถาม ให้ข้อมูล และพูดคุยในหัวข้อทั่วไปได้ครับ คุณอยากถามอะไรเป็นพิเศษไหมครับ?"),
    ("ช่วยฉันหน่อย", "ยินดีช่วยเหลือครับ คุณต้องการความช่วยเหลือในเรื่องอะไรครับ?"),
]

def compute_response(sentence):
    # เข้ารหัสคำถามของผู้ใช้
    query_embedding = model.encode(sentence, convert_to_tensor=True)
    
    # เข้ารหัสคำถามทั้งหมดในคลัง
    corpus_embeddings = model.encode([pair[0] for pair in qa_pairs], convert_to_tensor=True)
    
    # คำนวณความคล้ายคลึง
    similarities = util.cos_sim(query_embedding, corpus_embeddings)[0]
    
    # หาคำถามที่คล้ายที่สุด
    best_match_idx = similarities.argmax().item()
    best_similarity = similarities[best_match_idx].item()
    
    # ถ้าความคล้ายคลึงสูงพอ ให้ตอบด้วยคำตอบที่กำหนดไว้
    if best_similarity > 0.6:  # ปรับค่านี้ตามความเหมาะสม
        return qa_pairs[best_match_idx][1]
    else:
        return "ขอโทษครับ ผมไม่เข้าใจคำถามของคุณ คุณช่วยถามใหม่หรืออธิบายเพิ่มเติมได้ไหมครับ?"

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
        response_msg = compute_response(msg)
        line_bot_api.reply_message(tk, TextSendMessage(text=response_msg)) 
        print(f"Received: {msg}, Replied: {response_msg}")                                      
    except Exception as e:
        print(f"Error: {str(e)}")                                          
    return 'OK'                 

if __name__ == '__main__':
    app.run(port=5000)