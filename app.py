from flask import Flask, request, abort
import os
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

# 模擬資料庫中的資料
sample_data = [
    {
        "title": "北澤壽喜燒-大里店",
        "phone": "04-24821129",
        "address": "臺中市大里區德芳南路470號",
        "business_hours": "週一至週五 / 11:30-22:00 最後收客時間21:00，週六日、例假日 / 11:00-22:30 最後收客時間21:30",
        "google_maps_link": "https://maps.google.com/maps?daddr=24.10463,120.68314&hl=zh-TW"
    },
    {
        "title": "林記水餃館",
        "phone": "04-25889186",
        "address": "臺中市東勢區中山路50號",
        "business_hours": "No Business Hours",
        "google_maps_link": "https://maps.google.com/maps?daddr=24.25732,120.83006&hl=zh-TW"
    },
    {
        "title": "麗寶樂園",
        "phone": "04-25582459",
        "address": "臺中市后里區福容路8號(臺中后里外埔交流道下)",
        "business_hours": "平日營業時間: 09:30~17:00 / 假日為 夜間營運 營業時間: 09:30~20:00",
        "google_maps_link": "https://maps.google.com/maps?daddr=24.32377,120.69876&hl=zh-TW"
    }
]

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
    elif user_input in ["美食", "點心", "景點"]:
        region = user_region.get(user_id)
        if region:
            # 模擬從資料庫中抓取資料
            reply_message = create_flex_message(sample_data)
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

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
