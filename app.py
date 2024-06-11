from flask import Flask, request, abort
import os
from pymongo import MongoClient
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

app = Flask(__name__)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 全局變數來保存用戶的區域選擇
user_region = {}

# 定義台中市區域列表
taichung_regions = [
    '南區', '北區', '中區', '西區', '東區', '北屯區', '大里區', '烏日區',
    '南屯區', '西屯區', '大雅區', '豐原區', '潭子區'
]

def create_quick_reply_buttons():
    items = [
        QuickReplyButton(action=PostbackAction(label=region, data=f'region={region}'))
        for region in taichung_regions
    ]
    return QuickReply(items=items)

# 連接到 MongoDB Atlas
def get_database(dbname):
    CONNECTION_STRING = "mongodb+srv://r0980040:nuToa9PunCm65tgH@cluster0.wpk1rjx.mongodb.net/traveling"
    client = MongoClient(CONNECTION_STRING)
    return client[dbname]

# 從資料庫中獲取隨機的項目
def get_random_items_from_db(category, region):
    db = get_database(category)
    collection = db[region]
    random_items = collection.aggregate([{'$sample': {'size': 3}}])
    return list(random_items)

def create_flex_message(data):
    bubbles = []
    for item in data:
        title = item.get("Title", "無標題")
        phone = item.get("Phone", "無電話")
        address = item.get("Address", "無地址")
        business_hours = item.get("Business Hours", "無營業時間")
        google_maps_link = item.get("Google Maps Link", "https://maps.google.com")
        image_link = item.get("Image Link", "")

        # 確認電話號碼格式是否有效
        phone_text = TextComponent(text=f"電話：{phone}", wrap=True)
        if phone != "無電話" and phone != "no phone":
            phone_text = TextComponent(
                text=f"電話：{phone}",
                wrap=True,
                action=URIAction(uri=f"tel:{phone}")
            )

        # 確認 Google Maps Link 是否有效
        if not google_maps_link.startswith("http"):
            google_maps_link = "https://maps.google.com"

        bubble = BubbleContainer(
            direction='ltr',
            hero=ImageComponent(
                url=image_link,
                size='full',
                aspect_ratio='16:9',
                aspect_mode='cover'
            ),
            body=BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(text=title, weight='bold', size='lg'),
                    BoxComponent(layout='vertical', margin='lg', spacing='sm', contents=[
                        phone_text,
                        TextComponent(text=f"地址：{address}", wrap=True),
                        TextComponent(text=f"營業時間：{business_hours}", wrap=True),
                        ButtonComponent(
                            style='link',
                            height='sm',
                            action=URIAction(label='查看地圖', uri=google_maps_link)
                        ),
                        BoxComponent(
                            layout='horizontal',
                            spacing='sm',
                            contents=[
                                ButtonComponent(
                                    style='primary',
                                    color='#FF0000',
                                    height='sm',
                                    action=PostbackAction(label='1', data=f'rating=1&title={title}')
                                ),
                                ButtonComponent(
                                    style='primary',
                                    color='#FF7F00',
                                    height='sm',
                                    action=PostbackAction(label='2', data=f'rating=2&title={title}')
                                ),
                                ButtonComponent(
                                    style='primary',
                                    color='#FFFF00',
                                    height='sm',
                                    action=PostbackAction(label='3', data=f'rating=3&title={title}')
                                ),
                                ButtonComponent(
                                    style='primary',
                                    color='#7FFF00',
                                    height='sm',
                                    action=PostbackAction(label='4', data=f'rating=4&title={title}')
                                ),
                                ButtonComponent(
                                    style='primary',
                                    color='#00FF00',
                                    height='sm',
                                    action=PostbackAction(label='5', data=f'rating=5&title={title}')
                                )
                            ]
                        )
                    ])
                ]
            )
        )
        bubbles.append(bubble)

    return FlexSendMessage(alt_text="資料庫查詢結果", contents=CarouselContainer(contents=bubbles))



@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text

    if user_input == "開始":
        reply_message = TextSendMessage(
            text='請選擇您的所在區域',
            quick_reply=create_quick_reply_buttons()
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif user_input in ["美食", "點心", "景點"]:
        region = user_region.get(user_id)
        if region:
            # 從資料庫中獲取資料
            items = get_random_items_from_db(user_input, region)
            reply_message = create_flex_message(items)
            line_bot_api.reply_message(event.reply_token, reply_message)
        else:
            reply_message = TextSendMessage(text="請先選擇您的所在區域")
            line_bot_api.reply_message(event.reply_token, reply_message)
    else:
        reply_message = TextSendMessage(text="請輸入 '開始' 來選擇您的所在區域")
        line_bot_api.reply_message(event.reply_token, reply_message)

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    user_id = event.source.user_id

    if data.startswith('region='):
        region = data.split('=')[1]
        user_region[user_id] = region

        reply_message = TemplateSendMessage(
            alt_text='請選擇類別',
            template=ButtonsTemplate(
                title='請選擇服務項目',
                text='請選擇您要找的是美食、點心還是景點',
                actions=[
                    MessageAction(label='美食', text='美食'),
                    MessageAction(label='點心', text='點心'),
                    MessageAction(label='景點', text='景點')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)

    elif data.startswith('rating='):
        rating = data.split('&')[0].split('=')[1]
        title = data.split('&')[1].split('=')[1]
        # 處理評分邏輯，例如更新數據庫中的評分
        handle_rating(user_id, title, rating)
        reply_message = TextSendMessage(text=f"感謝您的評分！您給了 {title} {rating} 分。")
        line_bot_api.reply_message(event.reply_token, reply_message)
        
def handle_rating(user_id, title, rating):
    # 在此處理評分的邏輯，例如更新數據庫
    pass

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
