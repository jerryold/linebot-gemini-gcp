from linebot.models import FlexSendMessage
from linebot.models import (
    FollowEvent, MessageEvent, TextSendMessage
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot import (
    AsyncLineBotApi, WebhookParser
)

from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from fastapi import Request, FastAPI, HTTPException
import google.generativeai as genai
import os
import sys
from io import BytesIO
# import aioschedule as schedule

from datetime import datetime
import pytz

import aiohttp
import PIL.Image
from firebase import firebase
import json
from pydantic import BaseModel


# # get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('ChannelSecret', None)
channel_access_token = os.getenv('ChannelAccessToken', None)
gemini_key = os.getenv('GEMINI_API_KEY')
firebase_url = os.getenv('FIREBASE_URL')






imgage_prompt = '''
Describe this image with scientific detail, reply in zh-TW:
'''



if channel_secret is None:
    print('Specify ChannelSecret as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify ChannelAccessToken as environment variable.')
    sys.exit(1)
if gemini_key is None:
    print('Specify GEMINI_API_KEY as environment variable.')
    sys.exit(1)
if firebase_url is None:
    print('Specify FIREBASE_URL as environment variable.')
    sys.exit(1)

# Initialize the FastAPI app for LINEBot
app = FastAPI()
session = aiohttp.ClientSession()
async_http_client = AiohttpAsyncHttpClient(session)
line_bot_api = AsyncLineBotApi(channel_access_token, async_http_client)
parser = WebhookParser(channel_secret)

# Initialize the Gemini Pro API
genai.configure(api_key=gemini_key)

line_bot_api = LineBotApi('<channel access token>')

class UserIdRequest(BaseModel):
    user_id: str

@app.post("/get_userid")
async def get_userid(request: UserIdRequest):
    try:
        profile = line_bot_api.get_profile(request.user_id)
        return {"user_id": profile.user_id, "display_name": profile.display_name}
    except LineBotApiError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/")
async def handle_callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    for event in events:
        # Check if the event is a FollowEvent and save the user_id

        if not isinstance(event, MessageEvent):
            continue

        if event.message.type == "text":
            # Assume generate_gemini_text_complete is defined elsewhere
            msg = event.message.text
            ret = generate_gemini_text_complete(f'{msg}, reply in zh-TW:')
            reply_msg = TextSendMessage(text=ret.text)
            await line_bot_api.reply_message(event.reply_token, reply_msg)
        elif event.message.type == "image":
            message_content = await line_bot_api.get_message_content(event.message.id)
            image_content = b''
            async for s in message_content.iter_content():
                image_content += s
            img = PIL.Image.open(BytesIO(image_content))
            # Assume generate_result_from_image is defined elsewhere
            result = generate_result_from_image(img, "image_prompt")
            reply_msg = TextSendMessage(text=result.text)
            await line_bot_api.reply_message(event.reply_token, reply_msg)
            return 'OK'
        else:
            continue

    return 'OK'


# @app.post("/")
# async def handle_callback(request: Request):
#     signature = request.headers['X-Line-Signature']

#     # get request body as text
#     body = await request.body()
#     body = body.decode()

#     try:
#         events = parser.parse(body, signature)
#     except InvalidSignatureError:
#         raise HTTPException(status_code=400, detail="Invalid signature")
    
#     for event in events:
#         if not isinstance(event, MessageEvent):
#             continue        

#         if (event.message.type == "text"):
#             # Provide a default value for reply_msg
#             msg = event.message.text
#             ret = generate_gemini_text_complete(f'{msg}, reply in zh-TW:')
#             reply_msg = TextSendMessage(text=ret.text)
#             await line_bot_api.reply_message(
#                 event.reply_token,
#                 reply_msg
#             )
#         elif (event.message.type == "image"):
#             message_content = await line_bot_api.get_message_content(
#                 event.message.id)
#             image_content = b''
#             async for s in message_content.iter_content():
#                 image_content += s
#             img = PIL.Image.open(BytesIO(image_content))

#             result = generate_result_from_image(img, imgage_prompt)
#             reply_msg = TextSendMessage(text=result.text)
#             await line_bot_api.reply_message(
#                 event.reply_token,
#                 reply_msg
#             )
#             return 'OK'
#         else:
#             continue

#     return 'OK'


def generate_gemini_text_complete(prompt):
    """
    Generate a text completion using the generative model.
    """
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response


def generate_result_from_image(img, prompt):
    """
    Generate a image vision result using the generative model.
    """

    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content([prompt, img], stream=True)
    response.resolve()
    return response


# asyncio.run(run_scheduler())