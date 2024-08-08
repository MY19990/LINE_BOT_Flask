import requests
from datetime import datetime
import os
from geopy.geocoders import GoogleV3
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv() # .envファイルに記述された環境変数をos.getenvするために必要.

Nasa_APIkey = os.getenv('Nasa_APIkey')
Google_Map_APIkey = GoogleV3(api_key=os.getenv('Google_Map_APIkey'))
Deepl_APIkey = os.getenv('Deepl_APIkey')

###-----------------------------------------------------------------------

### 今宇宙にいる人の数・名前と船体名・緯度経度 ⇄ 真下の住所を返す
def iss_info():
    rocket = [f'\n{" "*25}/\{" "*13}\n{" "*24}/  \{" "*12}\n{" "*23}/    \{" "*11}\n{" "*22}/      \{" "*10}\n{" "*21}/-----\{" "*9}\n'
          f'{" "*19}/ \        / \{" "*7}\n{" "*18}/   \      /   \{" "*6}\n{" "*17}/     \    /     \{" "*5}\n'
          f'{" "*16}/----\  /----\{" "*4}\n{" "*18}|   |      |   |{" "*6}\n{" "*17}|---|    |---|{" "*7}\n'
          f'{" "*17}|---|    |---|{" "*7}\n{" "*17}|---|    |---|{" "*7}\n{" "*17}|---|    |---|{" "*7}\n'
          f'{" "*17}|---|    |---|{" "*7}\n{" "*17}|---|    |---|{" "*7}\n{" "*15}|---|-- --|---|{" "*5}\n'
          f'{" "*15}|---|-- --|---|{" "*5}\n{" "*15}|---|-- --|---|{" "*5}\n{" "*15}|---|        |---|{" "*5}\n'
          f'{" "*13}|----|-----|----|{" "*3}\n{" "*13}|----|-----|----|{" "*3}\n{" "*13}|----|-----|----|{" "*3}\n{" "*11}/🔥🔥🔥🔥🔥\{" "*1}\n']
    people_response = requests.get('http://api.open-notify.org/astros.json')
    people_json = people_response.json()
    iss_response = requests.get('http://api.open-notify.org/iss-now.json')
    iss_json = iss_response.json()
    box = []
    explain = [f"{'='*23}\n|+|  今宇宙にいる人の数\n|+|  名前と船体名\n|+|  緯度経度 ⇄ 真下の住所\n{'='*23}\n"]
    # 今宇宙にいる人の数 + その名前と船体名
    people_in_space = ['-'*31, f'|+| {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}','-'*31, f"|+| 👨‍🚀🛰 in space now : {people_json['number']}", '-'*31]
    people_info = [f"【{person['name']}】\n Place : {person['craft']}\n{'-'*31}" for person in people_json['people']]
    ##ISSの緯度経度 + 緯度経度を住所に変換
    latitude,longitude = iss_json['iss_position']['latitude'], iss_json['iss_position']['longitude']
    location = Google_Map_APIkey.reverse(f"{latitude}, {longitude}", language="en")
    current_iss_position = [f"\n|+| Current iss position :\n[ {latitude}, {longitude} ]\n\n|+| flying over :\n[{location}] 🛰\n\n{'='*23}"]

    box.extend([rocket ,explain, people_in_space, people_info, current_iss_position])

    box_flatten = [item for sublist in box for item in sublist]

    text = '\n'.join(info for info in box_flatten)
    return text

###-----------------------------------------------------------------------

### APODのimageURL、説明を返す
def get_apod_info():
    apod_response = requests.get(f"https://api.nasa.gov/planetary/apod?api_key={Nasa_APIkey}&hd=TRue")
    apod_response.raise_for_status() # statusが200番台（成功）以外ならHTTPErrorを起こしてexceptが作動
    apod_json = apod_response.json()
    # imageURL取得
    imageURL = apod_json['url']
    # 説明を取得
    get_date = (f"Date : {apod_json['date']}")
    ex_data = (f"Explanation : {apod_json['explanation']}")
    comment = (f"Writer : {apod_json.get('copyright', 'Unknown')}")
    # deeplでcommentを翻訳
    params = {'auth_key' : Deepl_APIkey,'text' : ex_data, 'source_lang' : 'EN', "target_lang": 'JA'}
    deepl_response = requests.post("https://api-free.deepl.com/v2/translate", data=params)
    deepl_response.raise_for_status()
    deepl_json = deepl_response.json()
    translated_text = deepl_json['translations'][0]['text']
    translated_text = translated_text.replace("。", "。\n" + os.linesep) # 自動改行機
    translated_text = translated_text.rstrip(os.linesep)  # 最後の改行を削除
    apod_explain = (f"{get_date}\n\n{comment}\n\n{translated_text}") 
    return imageURL, apod_explain
      
###-----------------------------------------------------------------------
### 今日の天文イベント情報を返す
def astronomy_event():
    now = datetime.now()
    # 日にちが二桁の場合は(日)がない場合があるから日を外す
    if (len(str(now.day))) == 1: day = f"{now.month}月{now.day}日"
    else: day = f"{now.month}月{now.day}"
    starwalk_response = requests.get(f"https://starwalk.space/ja/news/astronomy-calendar-{now.year}")
    html_content = starwalk_response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    data = []
    for h3 in soup.find_all('h3'):
        title = h3.text
        description = []
        # 現在のtitle(h3(x月x日：xxx))に今日の日付が含まれている場合、それ以降に存在するテキストをdescriptionに追加し続けて、
        # もし途中でh3,h2が見つかったら、ループを抜けて、dataリストに現在のtitleとdescを追加
        if day in title: 
            for sibling in h3.find_next_siblings():
                if sibling.name in ['h3','h2'] :
                    break
                description.append(sibling.text) # h3の兄弟タグのテキスト（題名に対する説明）を追加
            data.append((title, ' '.join(description)))
    post_text = '\n\n'.join(f"{title}\n{desc}" for title, desc in data)
    if bool(post_text) == False:
        return "天体イベントなし"
    else:
        return post_text

###-----------------------------------------------------------------------

if __name__ == "__main__": 
    # print(iss_info())

    # print(get_apod_info())
    imageURL, apod_explain = get_apod_info()
    print(imageURL, apod_explain)

    # print(astronomy_event())

    pass