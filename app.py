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

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text

    if user_input == "開始":
        # 問使用者所在的區域
        reply_message = TemplateSendMessage(
            alt_text='請選擇區域',
            template=ButtonsTemplate(
                title='請選擇您的所在區域',
                text='請選擇您所在的台中市區域',
                actions=[
                    PostbackAction(label='中區', data='region=中區'),
                    PostbackAction(label='東區', data='region=東區'),
                    PostbackAction(label='西區', data='region=西區'),
                    PostbackAction(label='南區', data='region=南區'),
                    PostbackAction(label='北區', data='region=北區'),
                    PostbackAction(label='西屯區', data='region=西屯區'),
                    PostbackAction(label='南屯區', data='region=南屯區'),
                    PostbackAction(label='北屯區', data='region=北屯區'),
                    PostbackAction(label='豐原區', data='region=豐原區'),
                    PostbackAction(label='大里區', data='region=大里區'),
                    PostbackAction(label='太平區', data='region=太平區'),
                    PostbackAction(label='清水區', data='region=清水區'),
                    PostbackAction(label='沙鹿區', data='region=沙鹿區'),
                    PostbackAction(label='大甲區', data='region=大甲區'),
                    PostbackAction(label='東勢區', data='region=東勢區'),
                    PostbackAction(label='梧棲區', data='region=梧棲區'),
                    PostbackAction(label='烏日區', data='region=烏日區'),
                    PostbackAction(label='神岡區', data='region=神岡區'),
                    PostbackAction(label='大肚區', data='region=大肚區'),
                    PostbackAction(label='大雅區', data='region=大雅區'),
                    PostbackAction(label='后里區', data='region=后里區'),
                    PostbackAction(label='霧峰區', data='region=霧峰區'),
                    PostbackAction(label='潭子區', data='region=潭子區'),
                    PostbackAction(label='龍井區', data='region=龍井區'),
                    PostbackAction(label='外埔區', data='region=外埔區'),
                    PostbackAction(label='和平區', data='region=和平區'),
                    PostbackAction(label='石岡區', data='region=石岡區'),
                    PostbackAction(label='大安區', data='region=大安區'),
                    PostbackAction(label='新社區', data='region=新社區')
                ]
            )
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

        reply_message = TemplateSendMessage(
            alt_text='請選擇服務項目',
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
    elif data in ["美食", "點心", "景點"]:
        region = user_region.get(user_id)
        reply_message = TextSendMessage(text="請先選擇您的所在區域")
        line_bot_api.reply_message(event.reply_token, reply_message)
            

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
