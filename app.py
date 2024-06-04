def create_flex_message(data):
    bubbles = []
    for item in data:
        title = item.get("Title", "無標題")
        phone = item.get("Phone", "無電話")
        address = item.get("Address", "無地址")
        business_hours = item.get("Business Hours", "無營業時間")
        google_maps_link = item.get("Google Maps Link", "https://maps.google.com")
        image_link = item.get("Image Link", "")

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
                        TextComponent(text=f"電話：{phone}"),
                        TextComponent(text=f"地址：{address}"),
                        TextComponent(text=f"營業時間：{business_hours}"),
                        ButtonComponent(
                            style='link',
                            height='sm',
                            action=URIAction(label='查看地圖', uri=google_maps_link)
                        )
                    ])
                ]
            )
        )
        bubbles.append(bubble)

    return FlexSendMessage(alt_text="資料庫查詢結果", contents=CarouselContainer(contents=bubbles))
