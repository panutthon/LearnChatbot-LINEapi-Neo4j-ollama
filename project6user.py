from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import FlexSendMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
import requests
from bs4 import BeautifulSoup
import json
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import faiss
import datetime

app = Flask(__name__)

# Initialize LineBotApi with your channel access token
line_bot_api = LineBotApi('rvVY90zi7+UL80fU6aQbDj+itnTfPGf+UXv5JyOLAgjxX6xpTzwGNkRAU8b901gGXLop3vOBCfXotyEvhxyYCqAOcuMWOh1x1gCuMDQSHJhiQDpZB1lp4CYIDVN/3hJLuBGMBgkMw7s+qDbONAqySAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('0d1f927f756f8c9e7aafb7715d8b18c8')

# Neo4j connection details
URI = "neo4j://localhost"
AUTH = ("neo4j", "password")

# Load sentence transformer model
model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2')

# Function to run Neo4j query
def run_query(query, parameters=None):
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

# Function to store chat history in Neo4j
def save_chat_history(user_id, user_message, bot_message):
    timestamp = datetime.datetime.now().isoformat()
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

# Function to scrape products from Converse website
def scrape_converse(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    products_details = []
    products = soup.find_all("li", {"class": "item product product-item"})
    for product in products:
        name = product.find("strong", class_="product name product-item-name")
        price = product.find("span", class_="price")
        image_tag = product.find("img", class_="product-image-photo")
        image_url = image_tag['src'] if image_tag else 'No image found'
        link_tag = product.find("a", class_="product-item-link")
        product_url = link_tag['href'] if link_tag else 'No link found'

        products_details.append({
            'name': name.text.strip() if name else 'No title found',
            'price': price.text.strip() if price else 'No price found',
            'image_url': image_url,
            'product_url': product_url
        })
    return products_details

# Function to send Flex Message with product details
def send_flex_message(reply_token, products):
    if not products:
        text_message = TextSendMessage(text="No products found.")
        line_bot_api.reply_message(reply_token, text_message)
        return

    bubbles = [{
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": prod['image_url'],
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover",
            "action": {
                "type": "uri",
                "uri": prod['product_url']
            }
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": prod['name'], "weight": "bold", "size": "md", "wrap": True},
                {"type": "text", "text": f"Price: {prod['price']}", "size": "sm", "color": "#999999"}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#00C853",
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": "View Product",
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

    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="Men", text="Men")),
        QuickReplyButton(action=MessageAction(label="Women", text="Women")),
        QuickReplyButton(action=MessageAction(label="Unisex", text="Unisex"))
    ])

    line_bot_api.reply_message(
        reply_token,
        messages=[flex_message, TextSendMessage(text="Choose an option:", quick_reply=quick_reply)]
    )

# Function to handle incoming LINE messages
@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)
    try:
        json_data = json.loads(body)
        reply_token = json_data['events'][0]['replyToken']
        msg = json_data['events'][0]['message']['text'].lower()
        user_id = json_data['events'][0]['source']['userId']  # Extract user_id from the event

        # Mapping URLs to user input
        url_map = {
            "men": "https://www.converse.co.th/sport.html?gender=62",
            "women": "https://www.converse.co.th/sport.html?gender=61",
            "unisex": "https://www.converse.co.th/sport.html?gender=63"
            
        }

        # Scrape products based on user input
        products = scrape_converse(url_map.get(msg, ""))
        
        # Send flex message with the products
        send_flex_message(reply_token, products)
        
        # Save chat history in Neo4j
        bot_message = f"Showing products for {msg}."
        save_chat_history(user_id, msg, bot_message)

    except Exception as e:
        print(f"Error processing the LINE event: {e}")

    return 'OK'

if __name__ == '__main__':
    app.run(port=5000, debug=True)
