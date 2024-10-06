from neo4j import GraphDatabase
from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from sentence_transformers import SentenceTransformer, util,InputExample
from sentence_transformers import models, losses
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from torch.utils.data import DataLoader
import numpy as np


#model = SentenceTransformer('bert-base-nli-mean-tokens')
model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2')
import json
# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = "neo4j://localhost"
AUTH = ("neo4j", "password")




def run_query(query, parameters=None):
   with GraphDatabase.driver(URI, auth=AUTH) as driver:
       driver.verify_connectivity()
       with driver.session() as session:
           result = session.run(query, parameters)
           return [record for record in result]
   driver.close()


cypher_query = '''
MATCH (n:Greeting) RETURN n.name as name, n.msg_reply as reply;
'''
greeting_corpus = []
greeting_vec = None
results = run_query(cypher_query)
for record in results:
   greeting_corpus.append(record['name'])
   #greeting_corpus = ["สวัสดีครับ","ดีจ้า"]
greeting_corpus = list(set(greeting_corpus))
print(greeting_corpus)  




def compute_similar(corpus, sentence):
   a_vec = model.encode([corpus],convert_to_tensor=True,normalize_embeddings=True)
   b_vec = model.encode([sentence],convert_to_tensor=True,normalize_embeddings=True)
   similarities = util.cos_sim(a_vec, b_vec)
   return similarities


def neo4j_search(neo_query):
   results = run_query(neo_query)
   # Print results
   for record in results:
       response_msg = record['reply']
   return response_msg     


def compute_response(sentence):
    greeting_vec = model.encode(greeting_corpus, convert_to_tensor=True, normalize_embeddings=True)
    ask_vec = model.encode(sentence, convert_to_tensor=True, normalize_embeddings=True)
    
    # Compute cosine similarities
    greeting_scores = util.cos_sim(greeting_vec, ask_vec)
    
    # Convert tensor to list if NumPy is not available
    greeting_scores_list = greeting_scores.tolist()
    
    # Convert list to NumPy array-like for argmax operation
    greeting_np = np.array(greeting_scores_list)
    
    # Extract the maximum similarity score as a scalar
    max_greeting_score = np.argmax(greeting_np)
    Match_greeting = greeting_corpus[max_greeting_score]
    
    if greeting_np[np.argmax(greeting_np)] > 0.5:
        My_cypher = f"MATCH (n:Greeting) WHERE n.name ='{Match_greeting}' RETURN n.msg_reply AS reply"
        my_msg = neo4j_search(My_cypher)
        print(my_msg)
        return my_msg

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
       line_bot_api.reply_message( tk, TextSendMessage(text=response_msg) )
       print(msg, tk)                                     
   except:
       print(body)                                         
   return 'OK'               
if __name__ == '__main__':
   #For Debug
   compute_response("นอนหลับฝันดี")
   app.run(port=5000)