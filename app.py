from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from pymongo import MongoClient
import logging

app = Flask(__name__)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 设置日志
logging.basicConfig(level=logging.INFO)

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

# 全局變數來保存用戶的區域和類別選擇
user_region = {}
user_category = {}

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

def get_database(dbname):
    # 提供 mongodb atlas url 以使用 pymongo 將 python 連接到 mongodb
    CONNECTION_STRING = "mongodb+srv://r0980040:nuToa9PunCm65tgH@cluster0.wpk1rjx.mongodb.net/traveling"
    # 使用 MongoClient 創建連接
    client = MongoClient(CONNECTION_STRING)
    # 返回數據庫實例
    return client[dbname]

def create_flex_message(data):
    bubbles = []
    for item in data:
        bubble = BubbleContainer(
            direction='ltr',
            body=BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(text=item["title"], weight='bold', size='lg'),
                    BoxComponent(layout='vertical', margin='lg', spacing='sm', contents=[
                        TextComponent(text=f"電話：{item['phone']}"),
                        TextComponent(text=f"地址：{item['address']}"),
                        TextComponent(text=f"營業時間：{item['business_hours']}"),
                        ButtonComponent(
                            style='link',
                            height='sm',
                            action=URIAction(label='查看地圖', uri=item['google_maps_link'])
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
        logging.info(f"User {user_id} selected region: {region}")

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
    
    elif data in ['美食', '點心', '景點']:
        user_category[user_id] = data
        logging.info(f"User {user_id} selected category: {data}")

        # 获取用户选择的区域和类别
        selected_region = user_region.get(user_id)
        selected_category = user_category.get(user_id)
        logging.info(f"Selected region: {selected_region}, selected category: {selected_category}")

        if selected_region and selected_category:
            # 根据用户的选择进行下一步处理，例如查询数据库或者调用API
            db = get_database(selected_category)
            collection = db[selected_region]
            random_items = list(collection.aggregate([{'$sample': {'size': 3}}]))
            logging.info(f"Random items: {random_items}")
            
            # 将随机获取的项目格式化为符合 create_flex_message 函数预期的格式
            items = [
                {
                    "title": item.get("title", "無標題"),
                    "phone": item.get("phone", "無電話"),
                    "address": item.get("address", "無地址"),
                    "business_hours": item.get("business_hours", "無營業時間"),
                    "google_maps_link": item.get("google_maps_link", "https://www.google.com/maps")
                }
                for item in random_items
            ]
            
            if items:
                # 创建并发送 Flex 消息
                flex_message = create_flex_message(items)
                line_bot_api.reply_message(event.reply_token, flex_message)
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="很抱歉，當前沒有找到符合條件的資料。"))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
