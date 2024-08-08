from flask import Flask, request
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import InvalidSignatureError
from linebot.models import (MessageEvent, PostbackAction, LocationMessage, TextMessage, TextSendMessage, 
                            ImageSendMessage, PostbackEvent,QuickReply, QuickReplyButton)
from argparse import ArgumentParser
import os
import logging
import requests
from trello import TrelloClient, Unauthorized
# .envを読み込む
from dotenv import load_dotenv
load_dotenv()
#import RPi.GPIO as GPIO
from get_weather_img import get_weather, get_img_url, del_up_img
from current_space_info import iss_info, get_apod_info, astronomy_event

##### API #####
Trello_client = TrelloClient(api_key=os.getenv('Trello_api_key'), 
                             api_secret=os.getenv('Trello_api_secret'), 
                             token=os.getenv('Trello_token'))
Board_ID = 'Mktum5nZ'
List_ID = '65a8c59b76dc90b306d06acb'

# OpenAI
# openai_api_key = os.getenv('openai_api_key')

###-----------------------------------------------------------------------

app = Flask(__name__)
handler = WebhookHandler(os.getenv('LINE_secret')) 
line_api = LineBotApi(os.getenv('LINE_access_token')) 
app.logger.setLevel(logging.WARNING)

### 署名 & Webhookイベントを適切なハンドラ関数にルーティング
@app.route("/callback", methods=['POST'])
def callback() -> str:
    # リクエストヘッダーから署名検証のための値を取得
    signature = request.headers["X-Line-Signature"]
    # リクエストボディの取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        # 署名を検証し、問題なければhandleに定義している関数を呼び出す
        """
        LINEからのWebhookイベント（ユーザーからのメッセージなど）を処理して、
        そのイベントの種類（MessageEventやPostbackEvent）とメッセージの種類（TextMessageなど）に基づいて、
        適切なハンドラ関数（PostbackEventイベントならon_postback(event)関数）にルーティングする。
        """
        handler.handle(body, signature)
        return "OK"
    except InvalidSignatureError:
        app.logger.warn("Invalid Signature.")
        
###-----------------------------------------------------------------------

@handler.add(PostbackEvent)
def on_postback(event):
    ### on_postback関数でユーザーに天気情報のImageを送信するための関数
    def send_weather_img(info_type, event):            
        # 天気グラフを作成 - /media/weather.pngに保存
        get_weather(loc=app.config['skcs'], info_type=info_type)
        # weather.pngをgyazoにアップロードしてユーザーに送信してアップした内容を削除
        upload_url, image_id = get_img_url(info_type=info_type)
        line_api.reply_message(event.reply_token, 
                               [ImageSendMessage(original_content_url=upload_url, preview_image_url=upload_url),
                               TextSendMessage(text=astronomy_event())])
        del_up_img(image_id=image_id)
    #------------------------------------------------
    user_id = event.source.user_id
    postback_msg = event.postback.data
    if postback_msg == "現在の天気・今日の天文イベント":
        send_weather_img(info_type="current", event=event)
    elif postback_msg == "48時間の天気":
        send_weather_img(info_type="hourly", event=event)
    elif postback_msg == "1週間の天気":
        send_weather_img(info_type="daily", event=event)

###-----------------------------------------------------------------------

@handler.add(MessageEvent, message=(TextMessage, LocationMessage))
def message_text(event):
    # ユーザーから「TextMessage」を受け取った場合の処理
    if isinstance(event.message, TextMessage):
        user_message = event.message.text
        user_id = event.source.user_id
        ### 鍵の開閉時
        if user_message == '🔑🔓':
            degree = 90
            duty_cycle = 2.5 + (12.0 - 2.5) / 180 * (degree + 90)
            duty_cycle = round(duty_cycle, 2)
            servo.ChangeDutyCycle(duty_cycle)
          
            line_api.reply_message(event.reply_token,TextSendMessage(text='OPEN 🔑'))
        elif user_message == '🔒':
            line_api.reply_message(event.reply_token,TextSendMessage(text='LOCK 🔒'))
        #-----------------------------------------------------------------------
        ### 天気情報の種類のボタンを送信
        elif user_message == 'Weather':
            line_api.reply_message(event.reply_token,TextSendMessage(text="地域名か位置情報を送信してください🌍"))
            app.config['wating_location'] = True
        ## (A).ユーザーから地域名（TextMessage）を受け取った場合の処理
        elif isinstance(event.message, TextMessage) and app.config.get('wating_location'):
            app.config['skcs'], app.config['wating_location'] = user_message, False
            # print(f"event.message = {user_message}, {app.config['skcs']}")
            data = ['現在の天気・今日の天文イベント', '48時間の天気', '1週間の天気']
            items = [QuickReplyButton(action=PostbackAction(label=d, data=d)) for d in data]
            messages = TextSendMessage(text="種類を選んでください🌍", quick_reply=QuickReply(items=items))
            line_api.reply_message(event.reply_token, messages=messages)
        #-----------------------------------------------------------------------
        ### 今宇宙にいる人の数・名前と船体名・緯度経度 ⇄ 真下の住所を送信｜APOD画像と説明を送信
        elif user_message == 'Space': 
            line_api.reply_message(event.reply_token,TextSendMessage(text=iss_info()))
        elif user_message == 'APOD':
            imageURL, apod_explain = get_apod_info()              
            line_api.reply_message(event.reply_token, [TextSendMessage(text=apod_explain),
                            ImageSendMessage(original_content_url=imageURL, preview_image_url=imageURL)])
        #-----------------------------------------------------------------------
        ### Trello新規カード追加
        elif user_message == "依頼":
            line_api.reply_message(event.reply_token,TextSendMessage(text="タイトルを入力してください📝"))
            # 次のメッセージを待つためのフラグを設定
            app.config['waiting_name'], app.config['waiting_desc'] = True,  False
        elif app.config.get('waiting_name'):
            app.config['name'] = user_message
            line_api.reply_message(event.reply_token,TextSendMessage(text="詳細を入力してください📝"))
            app.config['waiting_name'], app.config['waiting_desc'] = False, True
        elif app.config.get('waiting_desc'):
            app.config['desc'] = user_message
            card_name, card_desc = app.config.get('name'), app.config.get('desc')
            board = Trello_client.get_board(Board_ID)
            trello_list = board.get_list(List_ID)
            trello_list.add_card(name=card_name, desc=card_desc)
            line_api.reply_message(event.reply_token,TextSendMessage(text="カードを追加しました✨"))
            app.config['waiting_desc'] = False
        #-----------------------------------------------------------------------
    #-----------------------------------------------------------------------        
    ### (A).ユーザーから位置情報（LocationMessage）を受け取った時の処理
    elif isinstance(event.message, LocationMessage) and app.config.get('wating_location'):
        app.config['skcs'], app.config['wating_location'] = event.message.address, False
        data = ['現在の天気・今日の天文イベント', '48時間の天気', '1週間の天気']
        items = [QuickReplyButton(action=PostbackAction(label=d, data=d)) for d in data]
        messages = TextSendMessage(text="種類を選んでください🌍", quick_reply=QuickReply(items=items))
        line_api.reply_message(event.reply_token, messages=messages)
    ###-----------------------------------------------------------------------

if __name__ == "__main__":
    arg_parser = ArgumentParser(usage='Usage: python ' + __file__ + ' [--port ] [--help]')
    # portが指定されなかった場合はdefaultの5000が選択される.
    arg_parser.add_argument('-p', '--port', default=5000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()
    app.run(debug=options.debug, port=options.port)


##### 開閉プログラム #####
# # サーボモータを回す関数の登録
# SERVO_PIN = 18
# SERVO_OPEN_STATE = YYY（開錠状態）
# SERVO_CLOSE_STATE = ZZZ（z施錠状態）

# def KeyOpener():
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setup(SERVO_PIN, GPIO.OUT)
#     servo = GPIO.PWM(SERVO_PIN, 50)
#     servo.start(0.0)
#     servo.ChangeDutyCycle(SERVO_OPEN_STATE)
#     time.sleep(1.0)
#     GPIO.cleanup()

# def KeyCloser():
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setup(SERVO_PIN, GPIO.OUT)
#     servo = GPIO.PWM(SERVO_PIN, 50)
#     servo.start(0.0)
#     servo.ChangeDutyCycle(SERVO_CLOSE_STATE)
#     time.sleep(1.0)
#     GPIO.cleanup()
