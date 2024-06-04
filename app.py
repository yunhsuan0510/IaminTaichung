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
    '中區', '東區', '西區', '南區', '北區', '西屯區', '南屯區', '北屯區', '豐原區', '大里區', '太平區', '清水區', '沙鹿區',
    '大甲區', '東勢區', '梧棲區', '烏日區', '神岡區', '大肚區', '大雅區', '后里區', '霧峰區', '潭子區', '龍井區', '外埔區',
    '和平區', '石岡區', '大安區', '新社區'
]

def create_quick_reply_buttons():
    items = [
        QuickReplyButton(action=PostbackAction(label=region, data=f'region={region}'))
        for region in taichung_regions
    ]
    return QuickReply(items=items)

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

        reply_message = TextSendMessage(
            text='請選擇服務項目',
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
