from flask import Flask, request
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
import requests
from bs4 import BeautifulSoup
import json

app = Flask(__name__)

# Function to perform web scraping
def scrape_converse(url):  
    response = requests.get(url)  
    soup = BeautifulSoup(response.text, 'html.parser')  
    products_details = []  
    products = soup.find_all("li", {"class": "item product product-item"})  

    for product in products:  
        name = product.find("strong", class_="product name product-item-name")  
        price = product.find("span", class_="price")  

        # Assume there are no color options being parsed here; simplify for clarity  
        products_details.append({  
            'name': name.text.strip() if name else 'No title found',  
            'price': price.text.strip() if price else 'No price found'  
        })  

    return products_details

# Function to compute response based on the message
def compute_response(msg):  
    url_map = {  
        "men": "https://www.converse.co.th/sport.html?gender=62",  
        "women": "https://www.converse.co.th/sport.html?gender=61",  
        "unisex": "https://www.converse.co.th/sport.html?gender=63"  
    }  
    if msg in url_map:  
        products = scrape_converse(url_map[msg])  
        return '\n'.join([f"{prod['name']} - {prod['price']}" for prod in products])  
    else:  
        return "Please choose from Men, Women, or Unisex."

# Function to send quick reply messages
def send_quick_reply_message(reply_token, line_bot_api, response_msg):
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="Men", text="Men")),
        QuickReplyButton(action=MessageAction(label="Women", text="Women")),
        QuickReplyButton(action=MessageAction(label="Unisex", text="Unisex"))
    ])
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=response_msg, quick_reply=quick_reply)
    )

@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)
    try:
        json_data = json.loads(body)
        line_bot_api = LineBotApi('rvVY90zi7+UL80fU6aQbDj+itnTfPGf+UXv5JyOLAgjxX6xpTzwGNkRAU8b901gGXLop3vOBCfXotyEvhxyYCqAOcuMWOh1x1gCuMDQSHJhiQDpZB1lp4CYIDVN/3hJLuBGMBgkMw7s+qDbONAqySAdB04t89/1O/w1cDnyilFU=')
        msg = json_data['events'][0]['message']['text'].lower()
        reply_token = json_data['events'][0]['replyToken']
        response_msg = compute_response(msg)
        send_quick_reply_message(reply_token, line_bot_api, response_msg)
    except Exception as e:
        print(f"Error processing the LINE event: {e}")
    return 'OK'

if __name__ == '__main__':
    app.run(port=5000, debug=True)
