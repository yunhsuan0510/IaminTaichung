from flask import Flask, request, abort
import os
from pymongo import MongoClient, UpdateOne
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import requests
from bs4 import BeautifulSoup

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
user_category = {}
user_state = {}
user_temp_data = {}
now = ""
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
    
# 從資料庫中獲取前三高評分的項目
def get_top_rated_items_from_db(category, region):
    db = get_database(category)
    collection = db[region]
    top_items = collection.find().sort('Star', -1).limit(3)
    return list(top_items)
                
def create_flex_message(data):
    bubbles = []
    for item in data:
        title = item.get("Title", "無標題")
        phone = item.get("Phone", "無電話")
        address = item.get("Address", "無地址")
        business_hours = item.get("Business Hours", "無營業時間")
        google_maps_link = item.get("Google Maps Link", "https://maps.google.com")
        star = item.get("Star", "0.0")
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
                        TextComponent(text=f"評分：{star}", wrap=True),
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

    return FlexSendMessage(alt_text="想選嗎都給你選", contents=CarouselContainer(contents=bubbles))

def get_weather_info(region):
    url = f"https://weather.yam.com/{region}/臺中"
    response = requests.get(url)
    if response.status_code == 200:
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        weather_info = {}

        img_tag = soup.find('div', class_='Wpic').find('img')
        if img_tag:
            img_url = img_tag['src']
            full_img_url = requests.compat.urljoin(url, img_url)
            weather_info['img'] = full_img_url
        else:
            print('未找到圖片標籤')

        detail_section = soup.find('div', class_='detail')
        if detail_section:
            for p in detail_section.find_all('p'):
                text = p.text.strip()
                if "體感溫度" in text:
                    weather_info['feels_like'] = text.split(":")[1].strip()
                elif "降雨機率" in text:
                    weather_info['rain_probability'] = text.split(":")[1].strip()
                elif "紫外線" in text:
                    weather_info['uv_index'] = text.split(":")[1].strip()
                elif "空氣品質" in text:
                    weather_info['air_quality'] = text.split(":")[1].strip()
        return weather_info
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return None

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text
    global now
    if user_input == "驚喜":
        now = "驚喜"
        reply_message = TextSendMessage(
            text='請選擇您的所在區域',
            quick_reply=create_quick_reply_buttons()
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif user_input == "推薦":
        now = "推薦"
        reply_message = TextSendMessage(
            text='請選擇您的所在區域',
            quick_reply=create_quick_reply_buttons()
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif user_input == "新增":
        user_state[user_id] = "wait_for_title"
        reply_message = TextSendMessage(text="請輸入要新增的 Title")
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif user_state.get(user_id) == "wait_for_title":
        user_temp_data[user_id] = {'title': user_input}
        user_state[user_id] = "wait_for_rating"
        reply_message = TemplateSendMessage(
            alt_text='請選擇評分',
            template=ButtonsTemplate(
                title='請選擇評分',
                text=f'請為 "{user_input}" 評分',
                actions=[
                    PostbackAction(label='1', data='rating=1&title=' + user_input),
                    PostbackAction(label='2', data='rating=2&title=' + user_input),
                    PostbackAction(label='3', data='rating=3&title=' + user_input),
                    PostbackAction(label='4', data='rating=4&title=' + user_input),
                    PostbackAction(label='5', data='rating=5&title=' + user_input)
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif user_input in ["美食", "點心", "景點"]:
        region = user_region.get(user_id)
        user_category[user_id] = user_input
        if region:
            if user_input == "景點":
                # 獲取天氣資訊
                weather_info = get_weather_info(region)
                if weather_info:
                    flex_message = FlexSendMessage(
                        alt_text="天氣資訊",
                        contents={
                            "type": "bubble",
                            "hero": {
                                "type": "image",
                                "url": weather_info.get("img"),
                                "size": "full",
                                "aspect_ratio": "16:9",
                                "aspect_mode": "cover"
                            },
                            "body": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {"type": "text", "text": f"地區: {region}", "weight": "bold", "size": "lg"},
                                    {"type": "text", "text": f"體感溫度: {weather_info.get('feels_like', 'N/A')}", "wrap": True},
                                    {"type": "text", "text": f"降雨機率: {weather_info.get('rain_probability', 'N/A')}", "wrap": True},
                                    {"type": "text", "text": f"紫外線: {weather_info.get('uv_index', 'N/A')}", "wrap": True},
                                    {"type": "text", "text": f"空氣品質: {weather_info.get('air_quality', 'N/A')}", "wrap": True}
                                ]
                            }
                        }
                    )
                    line_bot_api.reply_message(event.reply_token, flex_message)
                    # 景點推薦的 Flex Message
                    if now == "驚喜":
                        items = get_random_items_from_db(user_input, region)
                    elif now == "推薦":
                        items = get_top_rated_items_from_db(user_input, region)
                    spots_flex_message = create_flex_message(items)
                    line_bot_api.push_message(user_id, spots_flex_message)
                else:
                    reply_message = TextSendMessage(text="無法獲取天氣資訊")
                    line_bot_api.reply_message(event.reply_token, reply_message)
            else:
                # 從資料庫中獲取資料
                if now == "驚喜":
                    items = get_random_items_from_db(user_input, region)
                elif now == "推薦":
                    items = get_top_rated_items_from_db(user_input, region)
                reply_message = create_flex_message(items)
                line_bot_api.reply_message(event.reply_token, reply_message)
        else:
            reply_message = TextSendMessage(text="請先選擇您的所在區域")
            line_bot_api.reply_message(event.reply_token, reply_message)
    else:
        reply_message = TextSendMessage(text="請輸入 '驚喜' 或 '推薦' 來選擇您的所在區域")
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
        
        # 發送給特定用戶
        specific_user_id = "Ueb0d6dea2a95c12fdf716b078d624834"  # 替換為特定用戶的 ID
        user_temp_data[user_id]['rating'] = rating
        temp_data = user_temp_data[user_id]
        reply_message = TextSendMessage(text=f"用戶 {user_id} 新增了一個項目: {temp_data['title']}，評分為 {temp_data['rating']}。")
        line_bot_api.push_message(specific_user_id, reply_message)

        # 清除暫存資料
        user_temp_data.pop(user_id, None)
        user_state[user_id] = None
        
        # 回覆用戶
        reply_message = TextSendMessage(text=f"感謝您的評分！您給了 {title} {rating} 分。")
        line_bot_api.reply_message(event.reply_token, reply_message)
        
def handle_rating(user_id, title, rating):

    # 獲取用戶選擇的分類和區域
    category = user_category.get(user_id)
    region = user_region.get(user_id)

    # 連接到數據庫
    db = get_database(category)
    # 查找符合條件的文檔
    collection = db[region]
    
    if category and region:

        item = collection.find_one({"Title": title})

        if item:
            # 確保 Count 是整數
            count = item.get('Count', 1)
            if isinstance(count, str):
                count = int(float(count))  # 轉換字符串為浮點數，再轉為整數

            # 確保 Star 是浮點數
            current_star = item.get('Star', 0.0)
            if isinstance(current_star, str):
                current_star = float(current_star)  # 轉換字符串為浮點數

            # 計算新的評分
            new_count = count + 1
            new_star = (current_star * count + float(rating)) / new_count
            new_star = round(new_star, 1)
            
            # 更新數據庫中的評分和計數
            collection.update_one(
                {"Title": title},
                {"$set": {"Star": new_star, "Count": new_count}}
            )


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
