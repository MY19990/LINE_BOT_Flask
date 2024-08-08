# -*- coding: utf-8 -*-
import os
import requests
import pandas as pd
import plotly.graph_objects as go
import urllib.request
from pytz import timezone
from datetime import datetime
from PIL import Image
import locale
from timezonefinder import TimezoneFinder
from geopy.geocoders import GoogleV3
locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
from PIL import Image

CITY_LATLOC_PATH = "dic/city_latloc.json"
ICON_DIR = "tenki_icon"
IMAGE_H = 1260
IMAGE_W = 800
BG_COLOR = "#100500"
LINE_COLOR = "#5f5050"
FONT_COLOR = "#fff5f3"
WEATHER_IMAGE_PATH = "./media"

Open_Wearther_APIkey = os.getenv("Open_Wearther_APIkey")
geolocator = GoogleV3(api_key=os.getenv('Google_Map_APIkey'))
gyazo_access_token = os.getenv('Gyazo_access_token')

def get_weather(loc=None, info_type=None):
    # 地域名から緯度経度取得
    location = geolocator.geocode(loc)
    lat, lon = location.latitude, location.longitude
    # 天気情報取得
    onecall_endpoint = "http://api.openweathermap.org/data/2.5/onecall"
    payload = { "lat": lat, "lon": lon,
            "lang": "ja", "units": "metric","APPID": Open_Wearther_APIkey}
    response = requests.get(onecall_endpoint, params=payload)
    jsondata = response.json()
    # 緯度と経度からタイムゾーンを取得
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lon)
    tz = timezone(timezone_str)
    # json.dumps(jsondata['current'], indent=4)

    ### 現在の天気情報を取得
    if info_type == 'current':
        tenki_data_list, skcs_name = [],[]
        locations = [loc ,'東京都', '神奈川県', '沖縄県那覇市', 'マチュ・ピチュ', 'ｸﾌ王のﾋﾟﾗﾐｯﾄﾞ', 'プーケット', 'ガラパゴス諸島', 'キューバ共和国', 'バンクーバー']
        for cnt, locs in  enumerate(locations):
            jsondata, tz = get_weather(loc=locs, info_type=None) # locsの天気情報が含まれるjsonとtimezoneを取得
            if cnt == 0: locs = "指定場所の天気"
            info1, info2 = make_weather_image_current(wd=[jsondata['current'], jsondata['hourly']], skcs_name=locs, tz=tz)
            tenki_data_list.append(info1), skcs_name.append(info2)
        return create_graph(tenki_data_list, f'{loc} & 世界')
    elif info_type == None:
        return jsondata, tz
    
    ### 48時間の天気情報を1時間間隔で取得
    elif info_type == 'hourly':
        tenki_data_list, skcs_name = make_weather_image_hourly(wd=jsondata['hourly'], skcs_name=loc, tz=tz)
        return create_graph(tenki_data_list, skcs_name)
    
    ### 1週間の天気を取得
    elif info_type == 'daily':
        tenki_data_list, skcs_name = make_weather_image_daily(wd=jsondata['daily'], skcs_name=loc, tz=tz)
        return create_graph(tenki_data_list, skcs_name)

###-----------------------------------------------------------------------

# 1.作成したグラフをgyazoにアップして、そのURLを返す
def get_img_url(info_type):
    try:
        # hourly以外はトリミングする
        if info_type != "hourly":
            image = Image.open('media/weather_img.png')
            width, height = image.size
            image.crop((0, 0, width, 360)).save('media/weather_img.png')
        headers = {'Authorization': "Bearer {}".format(gyazo_access_token)}
        with open("media/weather_img.png", "rb") as f:  
            files = {'imagedata':f.read()}  
            response = requests.post("https://upload.gyazo.com/api/upload", headers=headers, files=files)  
            gyazo_json = response.json()
            upload_url, image_id = gyazo_json['url'], gyazo_json['image_id']
        return upload_url, image_id
    except Exception as e:
            return (f"Error in get_img_url: {e}")
# 2.1でアップした画像をユーザーに送信後削除するための関数
def del_up_img(image_id):
    headers = {'Authorization': "Bearer {}".format(gyazo_access_token)} 
    return requests.delete(url=f"https://api.gyazo.com/api/images/{image_id}", headers=headers)

# 16方位名
'''
360/16方位=22.5 - 北は0、北北東は22.25、、、
deg(風向きの角度)=11.25, deg/22.5で0~15方位の中の0.5(北と北北東の中間)に位置することが分かる。round(0.5)=0で方位0の北が対応。
deg(風向きの角度)=11.26, 方位0.5004に位置, round(0.5004)=1で北北東が対応。
roundで、中間に位置する場合でも判定できるようにする - 例 : 北北東(22.25)と北東(45)の中間33.75の場合、方位1.5に位置、北東になる。
'''
def get_wind_deg_name(deg):
    # 16方位
    directions = ['北', '北北東', '北東', '東北東', '東', '東南東', '南東', '南南東', '南', '南南西', '南西', '西南西', '西', '西北西', '北西', '北北西']
    # 角度を方位インデックスに変換
    index = round(deg / 22.5) % 16
    return directions[index]

# 天気アイコン取得
def get_weather_icon(icon_name):
    # 天気アイコンの画像が保存されているディレクトリへのパス、取得したい天気アイコンの名前.png
    icon_image_path = os.path.join(
        WEATHER_IMAGE_PATH, ICON_DIR, icon_name + ".png")
    # 指定したパスに画像ファイルがあればpass
    if os.path.exists(icon_image_path):
        pass
    else:
        # 画像をダウンロードして、画像ファイルをopenして画像データを返す
        url = f"http://openweathermap.org/img/wn/{icon_name}@4x.png"
        with urllib.request.urlopen(url) as web_file:
            data = web_file.read()
            with open(icon_image_path, mode='wb') as local_file:
                local_file.write(data)
    return Image.open(icon_image_path)

###-----------------------------------------------------------------------

#現在の天気 - ['日時', '☀☁', '地域', 'icon', '天気', '気温℃', '湿度％', '体感気温℃', '降水確率％', '日の出', '日の入']
def make_weather_image_current(wd, skcs_name, tz):
    # tenki_data_list = []
    tmp_dict = {}
    # wd=[jsondata['current'],jsondata['hourly']]
    tmp_dict['日時'] = datetime.fromtimestamp(wd[0]['dt'], tz=tz).strftime("%m/%d %H時")
    tmp_dict['☀☁'] = ""  # お天気アイコン表示用
    tmp_dict['地域'] = skcs_name
    tmp_dict['icon'] = wd[0]['weather'][0]['icon']
    tmp_dict['天気'] = wd[0]['weather'][0]['description']
    tmp_dict['気温℃'] = f"{float(wd[0]['temp']):.1f}"
    tmp_dict['湿度％'] = wd[0]['humidity']
    tmp_dict['体感気温℃'] = f"{float(wd[0]['feels_like']):.1f}"
    # tmp_dict['気圧hPa'] = wd[0]['pressure']
    tmp_dict['降水確率％'] = int(float((list(wd[1]))[0]['pop'])*100)
    tmp_dict['日の出'] = datetime.fromtimestamp(
        wd[0]['sunrise'], tz=tz).strftime("%H:%M")
    tmp_dict['日の入'] = datetime.fromtimestamp(
        wd[0]['sunset'], tz=tz).strftime("%H:%M")
    # tenki_data_list.append(tmp_dict)
    return tmp_dict, skcs_name

# ４８時間天気 - ['日時', '☀☁', 'icon', '天気', '気温℃', '湿度％', '体感気温℃', '降水確率％', '風向', '風速m/s', '気圧hPa']
def make_weather_image_hourly(wd, skcs_name, tz):
    tenki_data_list = []
    for l1 in wd:
        tmp_dict = {}
        tmp_dict['日時'] = datetime.fromtimestamp(l1['dt'], tz=tz).strftime("%m/%d %H時")
        tmp_dict['☀☁'] = ""  # お天気アイコン表示用
        tmp_dict['icon'] = l1['weather'][0]['icon']
        tmp_dict['天気'] = l1['weather'][0]['description']
        tmp_dict['気温℃'] = f"{float(l1['temp']): .1f}" # tmp_dict['気温'] = f'{jsondata["main"]["temp"]}°'
        tmp_dict['湿度％'] = l1['humidity']
        tmp_dict['体感気温℃'] = f"{float(l1['feels_like']):.1f}"
        tmp_dict['降水確率％'] = int(float(l1['pop'])*100)
        tmp_dict['風向'] = get_wind_deg_name(l1['wind_deg'])
        tmp_dict['風速m/s'] = f"{float(l1['wind_speed']):.1f}"
        tmp_dict['気圧hPa'] = f"{int(l1['pressure']):,}"
        tenki_data_list.append(tmp_dict)
    return tenki_data_list, skcs_name

# 1週間天気 - ['日付', '☀☁', 'icon', '天気', '最高気温℃', '最低気温℃', '降水確率％', '湿度％', '風速m/s', '風向', '気圧hPa']
def make_weather_image_daily(wd, skcs_name, tz):
    tenki_data_list = []

    for l1 in wd:
        tmp_dict = {}
        tmp_dict['日付'] = datetime.fromtimestamp(
            l1['dt'], tz=tz).strftime("%m/%d(%a)")
        tmp_dict['☀☁'] = ""  # お天気アイコン表示用
        tmp_dict['icon'] = l1['weather'][0]['icon']
        tmp_dict['天気'] = l1['weather'][0]['description']
        tmp_dict['最高気温℃'] = f"{float(l1['temp']['max']):.1f}"
        tmp_dict['最低気温℃'] = f"{float(l1['temp']['min']):.1f}"
        tmp_dict['降水確率％'] = int(float(l1['pop'])*100)
        tmp_dict['湿度％'] = l1['humidity']
        tmp_dict['風速m/s'] = f"{float(l1['wind_speed']):.1f}"
        tmp_dict['風向'] = get_wind_deg_name(l1['wind_deg'])
        tmp_dict['気圧hPa'] = f"{int(l1['pressure']):,}"
        tenki_data_list.append(tmp_dict)
    return tenki_data_list, skcs_name

###-----------------------------------------------------------------------

# グラフ作成
def create_graph(tenki_data_list, skcs_name):
    tenki_data_key = (list(tenki_data_list[0].keys())) 
    tenki_data_key.remove('icon')
    df_temp = pd.json_normalize(tenki_data_list)
    df = df_temp[tenki_data_key]  # テーブルの作成

    fig = go.Figure(data=[go.Table(
        # columnorder=[10, 20, 30, 40, 50, 25, 70],
        columnwidth=[25, 10, 25, 20, 20, 20, 20, 20, 20, 20],  # カラム幅の変更
        header=dict(values=df.columns, align='center', font=dict(color=FONT_COLOR, size=18), height=30,
                    line_color=LINE_COLOR, fill_color=BG_COLOR),
        cells=dict(values=df.values.T, align='center', font=dict(color=FONT_COLOR, size=18), height=30,
                   line_color=LINE_COLOR, fill_color=BG_COLOR),)],
        layout=dict(margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor=BG_COLOR,
                    title=dict(text=skcs_name+"の天気", x=0.5, y=1.0, font=dict(color=FONT_COLOR, size=24), xanchor='center', yanchor='top', pad=dict(l=0, r=0, t=5, b=0))),)

    # 天気アイコン貼り付け
    for i in range(1, len(df)+1, 1):
        # 天気アイコン取得
        icon_name = df_temp['icon'][i-1]
        icon_image = get_weather_icon(icon_name)
        fig.add_layout_image(dict(source=icon_image, x=0.127, y=(1.0-1.0/49.0*(i+0.5))))
    fig.update_layout_images(dict(xref="paper", yref="paper", sizex=0.045, sizey=0.045, xanchor="left", yanchor="middle"))

    imagepath = os.path.join(WEATHER_IMAGE_PATH, "weather_img.png")
    fig.write_image(imagepath, height=30*(48+2), width=1100, scale=1)

    return imagepath

###-----------------------------------------------------------------------

### app.pyとのやり取り想定 ###
# app.pyでのユーザー入力 # 'current', 'daily', 'hourly'
# user = {'loc':'町田市', 'info_type':'daily'}
# print(get_weather(loc=user['loc'], info_type=user['info_type']))

if __name__ == '__main__':
    # get_weather(loc="町田市", info_type="hourly")
    # get_weather(loc="町田市", info_type="daily")
    # upload_url, image_id = get_img_url(info_type="hourly")
    pass