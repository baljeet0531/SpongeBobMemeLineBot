
from __future__ import print_function
import configparser
from hashlib import new
import re
from linebot.models import *
from linebot.exceptions import InvalidSignatureError
from linebot import LineBotApi, WebhookHandler
from flask import Flask, request, abort

import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import re
import csv
import json

app = Flask(__name__)  # 建立 Flask 物件
# app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # disable cache

config = configparser.ConfigParser()
config.read('config.ini')

line_bot_api = LineBotApi(config.get('line_bot', 'channel_access_token'))
handler = WebhookHandler(config.get('line_bot', 'channel_secret'))

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']


def searchImage(text):
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)

    results_length = 0
    results_message = []
    nextPageToken = "first"
    flex_dict = {
        "type": "carousel",
        "contents": []
    }

    with open("episode_info.json", 'r', encoding="utf-8") as f:
        episode_info = json.load(f)

    # imageFolder: https://drive.google.com/drive/u/0/folders/1CH7i08P4NK0WkhASe4_qs92fsL2Mz0tM

    while nextPageToken != []:
        if nextPageToken == "first":
            results = service.files().list(q="'1CH7i08P4NK0WkhASe4_qs92fsL2Mz0tM' in parents and fullText contains '{}'".format(text), pageSize=1000,
                                           fields="nextPageToken, files(id, name)").execute()
        else:
            results = service.files().list(q="'1CH7i08P4NK0WkhASe4_qs92fsL2Mz0tM' in parents and fullText contains '{}'".format(text), pageSize=1000, pageToken=nextPageToken,
                                           fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        nextPageToken = results.get('nextPageToken', [])
        print(len(items))
        for item in items:
            img_url = "https://lh3.googleusercontent.com/d/{}=w1080".format(
                item['id'])
            # print(u'{0} ({1})'.format(item['name'], img_url))

            positino_left_brackets = item['name'].find("【")
            position_right_brackets = item['name'].find("】")
            position_dot = item['name'].find(".jpg")
            img_episode = item['name'][positino_left_brackets +
                                       1:position_right_brackets]
            img_title = item['name'][position_right_brackets+1:position_dot]
            if img_title.find(text) != -1:
                results_length += 1
                if len(flex_dict["contents"]) < 12:
                    try:
                        esfio = episode_info[img_episode]["Every Spongebob Frame In Order"]
                        chn_episode_title = episode_info[img_episode]["中文集數名稱"]
                        eng_episode_title = episode_info[img_episode]["英文集數名稱"]
                    except:
                        pass

                    new_bubble_flex_message = {}

                    with open("bubble_flex_message.json", "r", encoding='utf-8') as f:
                        new_bubble_flex_message = json.load(f)

                    new_bubble_flex_message["hero"]["url"] = img_url
                    new_bubble_flex_message["body"]["contents"][0]["contents"][0]["text"] = img_title
                    new_bubble_flex_message["body"]["contents"][1]["contents"][0]["contents"][1]["text"] = img_episode
                    new_bubble_flex_message["body"]["contents"][1]["contents"][1]["contents"][1]["text"] = esfio
                    new_bubble_flex_message["body"]["contents"][1]["contents"][2]["contents"][1]["text"] = chn_episode_title
                    new_bubble_flex_message["body"]["contents"][1]["contents"][3]["contents"][1]["text"] = eng_episode_title
                    new_bubble_flex_message["footer"]["contents"][0]["action"]["data"] = "傳" + img_url
                    new_bubble_flex_message["footer"]["contents"][1]["action"]["uri"] = img_url

                    flex_dict["contents"].append(new_bubble_flex_message)
                if len(flex_dict["contents"]) == 12:
                    if len(results_message) < 5:
                        results_message.append(FlexSendMessage(
                            alt_text="搜尋結果",
                            contents=flex_dict)
                        )
                    if len(results_message) == 5:
                        print("len(results_message)1: ", len(results_message))
                        return {"length": results_length, "top5_url_list": results_message}
                    flex_dict["contents"] = []
        if nextPageToken == []:
            if len(flex_dict["contents"]) != 0:
                if len(results_message) < 5:
                    results_message.append(FlexSendMessage(
                        alt_text="搜尋結果",
                        contents=flex_dict)
                    )
                    print("len(results_message)2: ", len(results_message))
                    return {"length": results_length, "top5_url_list": results_message}

    print("len(results_message)3: ", len(results_message))
    return {"length": results_length, "top5_url_list": results_message}


@app.route("/callback", methods=['POST'])  # 路由
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
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print(event)
    text = event.message.text
    # ipath = u"{}".format(text)
    # print(re.findall(r'[\u4e00-\u9fff0-9]+', ipath))
    # if(re.findall(r'[\u4e00-\u9fff0-9]+', ipath)) == []:
    #     line_bot_api.reply_message(
    #         event.reply_token, TextSendMessage(text="無結果")
    #     )
    #     return

    results = searchImage(text)
    if results["length"] == 0:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="無結果")
        )
    else:
        line_bot_api.reply_message(
            event.reply_token, results["top5_url_list"]
        )
    return


@handler.add(PostbackEvent)
def handle_postback(event):
    print(event)
    data = event.postback.data
    if data[0] == "傳":
        img_url = data[1:]
        print(img_url)
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=img_url,
                preview_image_url=img_url
            )
        )
    return


if __name__ == "__main__":
    app.run(debug=True)
