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
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from linebot import LineBotApi
from linebot.models import FlexSendMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

app = Flask(__name__)

# ตั้งค่าโมเดล SentenceTransformer
model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2')

# เชื่อมต่อ Neo4j
URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "1648900019557")

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

# สร้าง Flask app และรวมโค้ดเดิมเข้ามา
app = Flask(__name__)

# Initialize LineBotApi with your channel access token
line_bot_api = LineBotApi('E5nJxfWbZyk8wH0xGE8+5YODmU+vor1FODX6LSMQCIqFFa1wxtl+7zpOOlVybD8O256OMQKP8VBMGYuttuZdhP5VjJJ61rQC5v2gSDBblzt1ChPla0PuGoVi/FsOEEqyn5WAtnJQzfFzCy3PPuLwRAdB04t89/1O/w1cDnyilFU=')

def ensure_http(url):
    if url.startswith('//'):
        return 'https:' + url
    elif not url.startswith(('http://', 'https://')):
        return 'https://' + url
    return url

def scrape_crocs(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    products_details = []
    products = soup.find_all("div", class_="grid-product__content")
    for product_element in products:
        product_name = product_element.find("div", class_="grid-product__title").text.strip()
        product_price_div = product_element.find("div", class_="grid-product__price")
        product_price_spans = product_price_div.find_all("span")
        if len(product_price_spans) == 5:
            product_normal_price_tag = product_price_div.find("span", class_="d-block fontWeight-7 grid-product__price--original")
            product_sale_price_tag = product_price_div.find("span", class_="color-sale")
            product_normal_price = product_normal_price_tag.text.strip() if product_normal_price_tag else None
            product_sale_price = product_sale_price_tag.text.strip() if product_sale_price_tag else None
        else:
            product_normal_price_tag = product_price_div.find("span", style="font-size: 12px;")
            product_normal_price = product_normal_price_tag.text.strip() if product_normal_price_tag else None
            product_sale_price = None
        img_tag = product_element.find("img")
        product_image_url = ensure_http(img_tag.get("src")) if img_tag else None
        product_link_tag = product_element.find("a", class_="grid-product__link")
        product_url = "https://crocs.co.th/"+(product_link_tag.get("href")) if product_link_tag else None
        products_details.append({
            'product_name': product_name,
            'normal_price': product_normal_price,
            'sale_price': product_sale_price,
            'image_url': product_image_url,
            'product_url': product_url
        })
    return products_details



def send_flex_message(reply_token, products,bot_reply):
    if not products:
        text_message = TextSendMessage(text="Not found.")
        line_bot_api.reply_message(reply_token, text_message)
        return

    # Limit the number of products to a maximum of 12
    products = products[:12]

    bubbles = [{
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": prod['image_url'],  # This now contains a valid URL with http/https
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": prod['product_name'], "weight": "bold", "size": "md", "wrap": True},
                {"type": "text", "text": f"ราคาปกติ: {prod['normal_price']}", "size": "sm", "color": "#999999"},
                {"type": "text", "text": f"ราคาลด: {prod['sale_price']}" if prod['sale_price'] else "ราคาลด: -", "size": "sm", "color": "#FF5551"}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "action": {
                        "type": "uri",
                        "label": "More details",
                        "uri": prod['product_url']  
                    }
                }
            ]
        }
    } for prod in products]

    contents = {"type": "carousel", "contents": bubbles}

    flex_message = FlexSendMessage(
        alt_text="Product List",
        contents=contents
    )

    line_bot_api.reply_message(
        reply_token,
        messages=[TextSendMessage(text=bot_reply),flex_message]
    )


# ฟังก์ชันบันทึกประวัติการสนทนา
def save_chat_history(user_id, user_msg, bot_reply):
    query = '''
    MERGE (u:User {uid: $user_id})
    CREATE (m:Message {text: $user_msg, timestamp: $timestamp})
    CREATE (r:Reply {text: $bot_reply, timestamp: $timestamp})
    MERGE (u)-[:SENT]->(m)
    MERGE (m)-[:HAS_REPLY]->(r)
    '''
    parameters = {
        "user_id": user_id,
        "user_msg": user_msg,
        "bot_reply": bot_reply,
        "timestamp": datetime.now().isoformat()
    }
    run_query(query, parameters)

def ask_style(reply_token):
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="Clogs", text="Clogs")),
        QuickReplyButton(action=MessageAction(label="Flats", text="Flats")),
        QuickReplyButton(action=MessageAction(label="Flip-Flops", text="Flip-Flops")),
        QuickReplyButton(action=MessageAction(label="Sandals", text="Sandals")),
        QuickReplyButton(action=MessageAction(label="Slides", text="Slides")),
        QuickReplyButton(action=MessageAction(label="Sneakers", text="Sneakers")),
        QuickReplyButton(action=MessageAction(label="Wedges and Heights", text="Wedges and Heights")),
        QuickReplyButton(action=MessageAction(label="All Style", text="All Style")),
    ])

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="กรุณาเลือกสไตล์รองเท้า :", quick_reply=quick_reply)
    )

def ask_color(reply_token):
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="Black", text="Black")),
        QuickReplyButton(action=MessageAction(label="White", text="White")),
        QuickReplyButton(action=MessageAction(label="Red", text="Red")),
        QuickReplyButton(action=MessageAction(label="Pink", text="Pink")),
        QuickReplyButton(action=MessageAction(label="Yellow", text="Yellow")),
        QuickReplyButton(action=MessageAction(label="End Filter", text="End filter"))
    ])

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="กรุณาเลือกสีรองเท้า :", quick_reply=quick_reply)
    )
def ask_type(reply_token):
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="Men", text="ชาย")),
        QuickReplyButton(action=MessageAction(label="Women", text="หญิง")),
        QuickReplyButton(action=MessageAction(label="Kids", text="เด็ก")),
        QuickReplyButton(action=MessageAction(label="Charms", text="ของตกแต่ง")),
        QuickReplyButton(action=MessageAction(label="Sale", text="ลดราคา"))
    ])

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="กรุณาเลือกประเภทสินค้า:", quick_reply=quick_reply)
    )
def ask_orderby(reply_token):
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="Best Selling", text="Best Selling")),
        QuickReplyButton(action=MessageAction(label="Newest", text="Newest")),
        QuickReplyButton(action=MessageAction(label="Highest Price", text="Highest Price")),
        QuickReplyButton(action=MessageAction(label="lowest Price", text="Lowest Price")),
    ])

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="คุณอยากจัดเรียงสินค้าแบบไหน : ", quick_reply=quick_reply)
    )

# แก้ไขฟังก์ชัน linebot เพื่อรวมการตอบสนองกับ Neo4j และการแสดงสินค้า
@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)
    try:
        json_data = json.loads(body)
        reply_token = json_data['events'][0]['replyToken']
        user_id = json_data['events'][0]['source']['userId']  # ดึง userId ของผู้ใช้
        msg = json_data['events'][0]['message']['text'].lower()

        global category_url, selected_style , selected_color,selected_order,bot_reply
         # URL mappings
        url_map = {
            "ชาย": "https://crocs.co.th/collections/men",
            "หญิง": "https://crocs.co.th/collections/women",
        }
        url_map_promo = {
            "ของตกแต่ง": "https://crocs.co.th/collections/jibbitz-charms",
            "เด็ก": "https://crocs.co.th/collections/kids",
            "ลดราคา": "https://crocs.co.th/collections/sale"    
        }

        if msg in url_map:
            category_url = url_map[msg]  # Store the category URL
            ask_style(reply_token)  # Ask for style

        elif msg in url_map_promo:
            final_url = url_map_promo[msg]
            products = scrape_crocs(final_url)
            bot_reply = "นี่คือผลการค้นหาครับ"
            send_flex_message(reply_token, products,bot_reply)
            save_chat_history(user_id, msg, bot_reply)

        elif msg in ["all style"]:
            final_url = category_url  # No need to append style or color filters
            products = scrape_crocs(final_url)
            print(products)
            bot_reply = "นี่คือผลการค้นหาครับ"
            send_flex_message(reply_token, products,bot_reply)
            save_chat_history(user_id, msg, bot_reply)

        # Handle style selection and then ask for color
        elif msg in ["clogs", "flats", "flip-flops", "sandals", "slides", "sneakers", "wedges and heights"]:
            style_map = {
                "clogs": "?filter.p.m.filter.style=Clogs",
                "flats": "?filter.p.m.filter.style=Flats",
                "flip-flops": "?filter.p.m.filter.style=Flip-Flops",
                "sandals": "?filter.p.m.filter.style=Sandals",
                "slides": "?filter.p.m.filter.style=Slides",
                "sneakers": "?filter.p.m.filter.style=Sneakers",
                "wedges and heights": "?filter.p.m.filter.style=Wedges+and+Heights"
            }
            selected_style = style_map[msg]  # Store the selected style
            ask_color(reply_token)  # Ask for color next
            

        elif msg in ["end filter"]:
            final_url = f"{category_url}{selected_style}"  # No need to append style or color filters
            products = scrape_crocs(final_url)
            bot_reply = "นี่คือผลการค้นหาครับ"
            send_flex_message(reply_token, products,bot_reply)
            save_chat_history(user_id, msg, bot_reply)
        # Handle color selection and generate the final URL
        elif msg in ["black", "white", "red", "pink", "yellow"]:
            color_map = {
                "black": "&filter.v.option.color=Black",
                "white": "&filter.v.option.color=White",
                "red": "&filter.v.option.color=Red",
                "pink": "&filter.v.option.color=Pink",
                "yellow": "&filter.v.option.color=Yellow"
            }
            selected_color = color_map[msg]  # Store the selected color
            ask_orderby(reply_token)

        elif msg in ["best selling", "newest", "highest price", "lowest price"]:
            orderby_map = {
                "best selling": "&sort_by=best-selling",
                "newest": "&sort_by=created-descending",
                "highest price": "&sort_by=price-descending",
                "lowest price": "&sort_by=price-ascending"
            }
            selected_order = orderby_map[msg]  # Store the selected ordering preference
            bot_reply = "นี่คือผลการค้นหาครับ"
            # Combine category, style, color, and order into the final URL
            final_url = f"{category_url}{selected_style}{selected_color}{selected_order}"
            products = scrape_crocs(final_url)
            print(final_url)
            send_flex_message(reply_token, products,bot_reply)
            save_chat_history(user_id, msg, bot_reply)

        else:
         # กรณีที่เป็นข้อความปกติที่ต้องการค้นหาการตอบกลับใน Neo4j
            bot_reply = compute_response(msg)
            line_bot_api.reply_message(reply_token, TextSendMessage(text=bot_reply))
            # บันทึกข้อความและการตอบกลับลงใน Neo4j
            save_chat_history(user_id, msg, bot_reply)

            print("Calling ask_type function...")
            ask_type(reply_token)
            
    except Exception as e:
        print(f"Error: {e}")
        print(body)
    return 'OK'

if __name__ == '__main__':
    app.run(port=5000, debug=True)
