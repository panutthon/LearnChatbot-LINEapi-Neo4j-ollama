from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
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
        image_tag = product.find("img", class_="product-image-photo")
        image_url = image_tag['src'] if image_tag else 'No image found'

        link_tag = product.find("a", class_="product-item-link")
        product_url = link_tag['href'] if link_tag else 'No link found'

        products_details.append({
            'name': name.text.strip() if name else 'No title found',
            'price': price.text.strip() if price else 'No price found',
            'image_url': image_url,
            'product_url': product_url  # Include the product URL
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

    line_bot_api.reply_message(
        reply_token,
        messages=[flex_message]
    )

# Function to handle first Quick Reply for all styles and categories
def ask_category(reply_token):
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="ALL Style", text="all style")),
        QuickReplyButton(action=MessageAction(label="Best Sellers", text="best sellers")),
        QuickReplyButton(action=MessageAction(label="New Arrival", text="new arrival")),
        QuickReplyButton(action=MessageAction(label="Exclusives", text="exclusives")),
    ])

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="Please choose a category:", quick_reply=quick_reply)
    )

# Function to handle second level Quick Reply for gender selection
def ask_gender(reply_token):
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="Men", text="Men")),
        QuickReplyButton(action=MessageAction(label="Women", text="Women")),
        QuickReplyButton(action=MessageAction(label="Unisex", text="Unisex")),
    ])

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="Please choose gender:", quick_reply=quick_reply)
    )

# Function to handle the second Quick Reply for all style choices
def ask_all_style(reply_token):
    quick_reply = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="Chuck 70", text="chuck 70")),
        QuickReplyButton(action=MessageAction(label="Classic Chuck", text="classic chuck")),
        QuickReplyButton(action=MessageAction(label="Sport", text="sport")),
        QuickReplyButton(action=MessageAction(label="Elevation", text="elevation")),
    ])

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="Please choose a style:", quick_reply=quick_reply)
    )

@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)
    try:
        json_data = json.loads(body)
        reply_token = json_data['events'][0]['replyToken']
        msg = json_data['events'][0]['message']['text'].lower()

        # Mapping URLs to product categories
        url_map = {
            "chuck 70": "https://www.converse.co.th/chuck-70.html",
            "classic chuck": "https://www.converse.co.th/classic-chuck.html",
            "sport": "https://www.converse.co.th/sport.html",
            "elevation": "https://www.converse.co.th/women/shoes/platform.html"
        }

        # Handle first category selection
        if msg == "all style":
            ask_all_style(reply_token)  # Ask user to select style under ALL Style

        # Handle best sellers, new arrival, and exclusives
        elif msg == "best sellers":
            final_url = "https://www.converse.co.th/men/trending.html?cat=13"
            ask_gender(reply_token)  # Ask user to select gender
        elif msg == "new arrival":
            final_url = "https://www.converse.co.th/men/trending.html?cat=14"
            ask_gender(reply_token)  # Ask user to select gender
        elif msg == "exclusives":
            final_url = "https://www.converse.co.th/men/trending.html?cat=15"
            ask_gender(reply_token)  # Ask user to select gender

        # Store the selected category in a variable (or use session if needed)
        elif msg in url_map:
            # Store the category URL temporarily and ask for gender
            global category_url
            category_url = url_map[msg]
            ask_gender(reply_token)  # Ask the user to select gender

        # If user selects gender, use the previously stored category URL to form the final URL
        elif msg in ["men", "women", "unisex"]:
            gender_map = {
                "men": "?gender=62",
                "women": "?gender=61",
                "unisex": "?gender=63"
            }

            # Build the final URL based on the category and selected gender
            final_url = f"{category_url}{gender_map[msg]}"
            products = scrape_converse(final_url)
            send_flex_message(reply_token, products)  # Send the scraped products to the user

    except Exception as e:
        print(f"Error processing the LINE event: {e}")

    return 'OK'

if __name__ == '__main__':
    app.run(port=5000, debug=True)