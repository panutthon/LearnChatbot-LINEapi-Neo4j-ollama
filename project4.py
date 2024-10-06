from flask import Flask, request
from linebot import LineBotApi
from linebot.models import FlexSendMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
import requests
from bs4 import BeautifulSoup
import json

app = Flask(__name__)

# Initialize LineBotApi with your channel access token
line_bot_api = LineBotApi('rvVY90zi7+UL80fU6aQbDj+itnTfPGf+UXv5JyOLAgjxX6xpTzwGNkRAU8b901gGXLop3vOBCfXotyEvhxyYCqAOcuMWOh1x1gCuMDQSHJhiQDpZB1lp4CYIDVN/3hJLuBGMBgkMw7s+qDbONAqySAdB04t89/1O/w1cDnyilFU=')

# Function to perform web scraping
def scrape_converse(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    products_details = []
    products = soup.find_all("li", {"class": "item product product-item"})
    for product in products:
        name = product.find("strong", class_="product name product-item-name")
        price = product.find("span", class_="price")
        products_details.append({
            'name': name.text.strip() if name else 'No title found',
            'price': price.text.strip() if price else 'No price found'
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
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": prod['name'], "weight": "bold", "size": "md", "wrap": True},
                {"type": "text", "text": f"Price: {prod['price']}", "size": "sm", "color": "#999999"}
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

@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)
    try:
        json_data = json.loads(body)
        reply_token = json_data['events'][0]['replyToken']
        msg = json_data['events'][0]['message']['text'].lower()
        
        # Mapping URLs to user input
        url_map = {
            "men": "https://www.converse.co.th/sport.html?gender=62",
            "women": "https://www.converse.co.th/sport.html?gender=61",
            "unisex": "https://www.converse.co.th/sport.html?gender=63"
        }
        
        products = scrape_converse(url_map.get(msg, ""))  # Scrape products based on user input
        send_flex_message(reply_token, products)  # Send flex message with the products

    except Exception as e:
        print(f"Error processing the LINE event: {e}")

    return 'OK'

if __name__ == '__main__':
    app.run(port=5000, debug=True)
