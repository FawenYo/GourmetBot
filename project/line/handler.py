import random
import re
import string
import sys
import threading
import traceback
from datetime import datetime

import sentry_sdk
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import *

sys.path.append(".")
from typing import Optional

import config
import cron
import MongoDB.operation as database
from food.main import Restaurant_Info
from line.templates import Template
from vote.main import create_event
from weather.main import Weather

line_bot_api = LineBotApi(config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(config.LINE_CHANNEL_SECRET)

line_app = APIRouter()

# LINE Notify Redirect
@line_app.get("/notify/", response_class=RedirectResponse)
async def line_notify_redirect(uid: Optional[str] = ""):
    link = config.lotify_client.get_auth_link(state=uid)
    return RedirectResponse(link)


# Line Notify Callback
@line_app.get("/notify/callback", response_class=RedirectResponse)
async def line_notify_callback(code: str = "", state: str = ""):
    line_notify_key = config.lotify_client.get_access_token(code=code)
    result = config.db.user.find_one({"user_id": state})
    result["notify"]["status"] = True
    result["notify"]["token"] = line_notify_key
    config.db.user.update_one({"user_id": state}, {"$set": result})
    return RedirectResponse(config.SITE_NAME)


# LINE Server Webhook callback
@line_app.post("/callback")
async def callback(request: Request):
    """LINE Server Webhook Callback

    Raises:
        HTML status code 400: InvalidSignatureError
    Returns:
        str: "OK"
    """
    signature = request.headers["X-Line-Signature"]
    body = await request.body()
    # handle webhook body
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Missing Parameter")
    return "OK"


@handler.add(FollowEvent)
def handle_follow(event):
    """事件 - 新使用者加入Bot

    Args:
        event (LINE Event Object): Refer to https://developers.line.biz/en/reference/messaging-api/#follow-event
    """
    reply_token = event.reply_token
    message = Template().welcome()
    line_bot_api.reply_message(reply_token, message)
    profile = line_bot_api.get_profile(event.source.user_id)
    display_name = profile.display_name
    database.new_user(user_id=event.source.user_id, display_name=display_name)


@handler.add(UnfollowEvent)
def handle_unfollow(event):
    """事件 - 新使用者封鎖Bot

    Args:
        event (LINE Event Object): Refer to https://developers.line.biz/en/reference/messaging-api/#unfollow-event
    """
    database.delete_user(user_id=event.source.user_id)


@handler.add(MessageEvent, message=(TextMessage, LocationMessage))
def handle_message(event):
    """事件 - 訊息

    Args:
        event (LINE Event Object): Refer to https://developers.line.biz/en/reference/messaging-api/#message-event
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    # 文字訊息
    if isinstance(event.message, TextMessage):
        user_message = event.message.text
        try:
            pending = config.db.pending.find_one({"user_id": user_id})
            # QA問答
            if pending:
                # 取消操作
                if user_message == "取消":
                    config.db.pending.delete_one({"user_id": user_id})
                    message = TextSendMessage(text=f"已取消操作！")
                else:
                    # 餐廳關鍵字
                    if pending["action"] == "search":
                        config.db.pending.delete_one({"user_id": user_id})
                        latitude = pending["latitude"]
                        longitude = pending["longitude"]
                        message = find_nearby(
                            user_id=user_id,
                            latitude=latitude,
                            longitude=longitude,
                            keyword=user_message,
                        )
                    # 創建投票
                    else:
                        (
                            status,
                            event_name,
                            available_dates,
                            no_earlier,
                            no_later,
                        ) = parse_string(message=user_message)

                        if status:
                            config.db.pending.delete_one({"user_id": user_id})
                            user = config.db.user.find_one({"user_id": user_id})
                            user["vote"] = []
                            config.db.user.update_one(
                                {"user_id": user_id}, {"$set": user}
                            )

                            link = create_event(
                                event_name=event_name,
                                dates=available_dates,
                                early_time=no_earlier,
                                later_time=no_later,
                            )

                            vote_id = "".join(
                                random.choice(string.ascii_letters + string.digits)
                                for x in range(10)
                            )
                            database.create_vote(
                                creator=user_id,
                                vote_id=vote_id,
                                vote_link=link,
                                restaurants=pending["pools"],
                                end_date=pending["end_date"],
                            )
                            threading.Thread(
                                target=cron.vote_cronjob,
                                args=(vote_id, user_id, pending["end_date"], link),
                            ).start()
                            message = Template().share_vote(pull_id=vote_id)
                        else:
                            message = TextSendMessage(
                                text="抱歉，格式有誤，請重新輸入！\n如要取消操作請輸入 '取消' "
                            )
            else:
                # 教學
                if user_message == "教學":
                    message = Template().tutorial()
                    line_bot_api.reply_message(reply_token, message)
                # 我的最愛
                if user_message == "我的最愛":
                    user_data = config.db.user.find_one({"user_id": user_id})
                    if len(user_data["favorite"]) > 0:
                        message = Template().show_favorite(
                            restaurants=user_data["favorite"][:10]
                        )
                    else:
                        message = TextSendMessage(text="您的最愛列表內還沒有餐廳喔！")
                # 投票池
                elif user_message == "投票":
                    user_data = config.db.user.find_one({"user_id": user_id})
                    # 已綁定 LINE Notify
                    if user_data["notify"]["status"]:
                        if len(user_data["vote"]) > 0:
                            message = [
                                Template().show_vote_pull(
                                    restaurants=user_data["vote"][:10]
                                ),
                                TextSendMessage(
                                    text="請確認投票名單是否正確",
                                    quick_reply=QuickReply(
                                        items=[
                                            QuickReplyButton(
                                                action=PostbackAction(
                                                    label="創建",
                                                    data=f"create",
                                                )
                                            )
                                        ]
                                    ),
                                ),
                            ]
                        else:
                            message = TextSendMessage(text="您的投票池內還沒有餐廳喔！")
                    else:
                        message = TextSendMessage(
                            text=f"尚未綁定 LINE Notify!\n請先前往 {config.SITE_NAME}notify/?uid={user_id} 進行綁定~"
                        )
                elif user_message == "客服":
                    message = TextSendMessage(text="客服連結\nhttps://lin.ee/DsogwtP")
                elif "@找" in user_message:
                    target = user_message.split("@找")[1]
                    message = search_info(user_id=user_id, query=target)
                    line_bot_api.reply_message(reply_token, message)
                else:
                    if event.source.type == "user":
                        message = TextSendMessage(
                            text="不好意思，我聽不懂你在說什麼呢QwQ\n如需要幫助，請輸入「客服」尋求幫忙"
                        )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            config.console.print_exception()
            message = Template().error()
        line_bot_api.reply_message(reply_token, message)
    # 地點訊息
    elif isinstance(event.message, LocationMessage):
        try:
            lat = event.message.latitude
            lng = event.message.longitude

            # 預設類別
            restaurant_category = ["隨便", "日式", "中式", "西式"]
            quick_reply_items = [
                QuickReplyButton(
                    action=PostbackAction(
                        label=category,
                        display_text=category,
                        data=f"search_||_{lat},{lng}_||_{category}",
                    )
                )
                for category in restaurant_category
            ]

            # 動態類別
            dynamic_update_category = Weather().customized_category(lat=lat, lng=lng)
            temp_quick_reply_items = [
                QuickReplyButton(
                    action=PostbackAction(
                        label=category,
                        display_text=dynamic_update_category[category],
                        data=f"search_||_{lat},{lng}_||_{dynamic_update_category[category]}",
                    )
                )
                for category in list(dynamic_update_category.keys())
            ]

            quick_reply_items += temp_quick_reply_items
            quick_reply_items.append(
                QuickReplyButton(
                    action=PostbackAction(
                        label="其他",
                        display_text="其他",
                        data=f"search_||_{lat},{lng}_||_其他",
                    )
                )
            )
            message = TextSendMessage(
                text="請選擇餐廳類別",
                quick_reply=QuickReply(items=quick_reply_items),
            )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            config.console.print_exception()
            message = Template().error()
        line_bot_api.reply_message(reply_token, message)


@handler.add(PostbackEvent)
def handle_postback(event):
    """事件 - Postback

    Args:
        event (LINE Event Object): Refer to https://developers.line.biz/en/reference/messaging-api/#postback-event
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    postback_data = event.postback.data
    try:
        if "_||_" in postback_data:
            postback_args = postback_data.split("_||_")
            action = postback_args[0]
            # 加入收藏名單
            if action == "favorite":
                restaurant_id = postback_args[1]
                restaurant_data = config.db.restaurant.find_one(
                    {"place_id": restaurant_id}
                )
                if not restaurant_data:
                    restaurant_data = config.restaurants[restaurant_id]
                user = config.db.user.find_one({"user_id": user_id})
                # 尚未收藏餐廳
                if restaurant_data not in user["favorite"]:
                    # 更新收藏列表
                    user["favorite"].append(restaurant_data)
                    config.db.user.update_one({"user_id": user_id}, {"$set": user})

                    message = TextSendMessage(text=f"已將{restaurant_data['name']}加入最愛！")
                else:
                    message = TextSendMessage(text=f"已經有like過相同的餐廳囉！")
                line_bot_api.reply_message(reply_token, message)
            # 搜尋餐廳
            elif action == "search":
                latitude, longitude = [float(i) for i in postback_args[1].split(",")]
                keyword = postback_args[2]
                if keyword == "其他":
                    data = {
                        "action": "search",
                        "user_id": user_id,
                        "latitude": latitude,
                        "longitude": longitude,
                    }
                    config.db.pending.insert_one(data)
                    message = TextSendMessage(text=f"請輸入餐廳類別或名稱")
                else:
                    message = find_nearby(
                        user_id=user_id,
                        latitude=latitude,
                        longitude=longitude,
                        keyword=keyword,
                    )
                try:
                    line_bot_api.reply_message(reply_token, message)
                # 搜尋超時
                except LineBotApiError as e:
                    sentry_sdk.capture_exception(e)
                    config.console.print_exception()
                    line_bot_api.push_message(user_id, message)
            # 搜尋更多
            elif action == "more":
                latitude, longitude = [float(i) for i in postback_args[1].split(",")]
                keyword = postback_args[2]
                token = postback_args[3]
                token_table = config.db.page_token.find_one({})
                page_token = token_table["data"][token]
                message = find_nearby(
                    user_id=user_id,
                    latitude=latitude,
                    longitude=longitude,
                    keyword=keyword,
                    page_token=page_token,
                )
                try:
                    line_bot_api.reply_message(reply_token, message)
                # 搜尋超時
                except LineBotApiError as e:
                    sentry_sdk.capture_exception(e)
                    config.console.print_exception()
                    # 使用push回應內容
                    line_bot_api.push_message(user_id, message)
            # 加入投票池
            elif action == "vote":
                restaurant_id = postback_args[1]
                user = config.db.user.find_one({"user_id": user_id})
                restaurant_data = config.db.restaurant.find_one(
                    {"place_id": restaurant_id}
                )
                if not restaurant_data:
                    restaurant_data = config.restaurants[restaurant_id]
                if restaurant_data not in user["vote"]:
                    user["vote"].append(restaurant_data)
                    config.db.user.update_one({"user_id": user_id}, {"$set": user})
                    message = TextSendMessage(text=f"已將{restaurant_data['name']}加入投票池！")
                else:
                    message = TextSendMessage(text=f"餐廳已經在投票池內囉！")
                line_bot_api.reply_message(reply_token, message)
            # 移除投票
            elif action == "remove":
                place_id = postback_args[1]
                user = config.db.user.find_one({"user_id": user_id})
                restaurant_data = config.db.restaurant.find_one({"place_id": place_id})
                if restaurant_data in user["vote"]:
                    user["vote"].remove(restaurant_data)
                    config.db.user.update_one({"user_id": user_id}, {"$set": user})
                    message = TextSendMessage(text=f"已將{restaurant_data['name']}移除投票池！")
                else:
                    message = TextSendMessage(text=f"餐廳不在投票池內！")
                try:
                    line_bot_api.reply_message(reply_token, message)
                # 搜尋超時
                except LineBotApiError as e:
                    sentry_sdk.capture_exception(e)
                    config.console.print_exception()
                    line_bot_api.push_message(user_id, message)
        else:
            # 創建投票
            if postback_data == "create":
                message = TextSendMessage(
                    text=f"請設定投票截止日期",
                    quick_reply=QuickReply(
                        items=[
                            QuickReplyButton(
                                action=DatetimePickerAction(
                                    label="截止日期",
                                    data="endDate",
                                    mode="datetime",
                                )
                            ),
                        ]
                    ),
                )
            # 投票截止日期
            elif postback_data == "endDate":
                vote_pull = config.db.user.find_one({"user_id": user_id})["vote"]
                end_date = datetime.strptime(
                    event.postback.params["datetime"], "%Y-%m-%dT%H:%M"
                )
                data = {
                    "action": "create_event",
                    "user_id": user_id,
                    "end_date": end_date,
                    "pools": vote_pull,
                }
                config.db.pending.insert_one(data)
                message = TextSendMessage(
                    text=f"請依據以下格式輸入投票資訊：\n'投票名稱/投票聚餐日期(西元年-月-日, 多個日期之間以 '|' 連結)/聚餐最早開始時間(小時, 24小時制)/聚餐最晚開始時間(小時, 24小時制)'\n(例如：聖誕聚餐/2020-12-24/18/20)"
                )
            else:
                message = TextSendMessage(text=f"我不知道你在幹嘛QwQ")
            line_bot_api.reply_message(reply_token, message)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        config.console.print_exception()
        message = Template().error()
        line_bot_api.reply_message(reply_token, message)


def search_info(user_id: str, query: str, page_token: str = ""):
    restaurants = Restaurant_Info(page_token=page_token)
    restaurants.search(query=query)
    if len(restaurants.restaurants) == 0:
        message = TextSendMessage(text=f"很抱歉，我們找不到相關的餐廳😭")
    else:
        # Show first five restaurant
        message = Template().search_result(
            restaurants=restaurants.restaurants[:5],
        )
    # 記錄使用者位置
    """thread = threading.Thread(
        target=database.record_user_search, args=(user_id, latitude, longitude, keyword)
    )
    thread.start()"""
    return message


def find_nearby(
    user_id: str, latitude: float, longitude: float, keyword: str, page_token: str = ""
):
    """搜尋附近餐廳

    Args:
        latitude (float): Location latitude
        longitude (float): Location longitude
        keyword (str): Restaurant name / category
        page_token (str, optional): Google Maps API page token. Defaults to "".
    """
    if keyword == "隨便":
        keyword = ""
    restaurants = Restaurant_Info(
        latitude=latitude, longitude=longitude, keyword=keyword, page_token=page_token
    )
    restaurants.nearby()
    if len(restaurants.restaurants) == 0:
        message = TextSendMessage(text=f"很抱歉，我們找不到相關的餐廳😭")
    else:
        # Show first five restaurant
        message = Template(user_lat=latitude, user_lng=longitude).show_restaurant(
            restaurants=restaurants.restaurants[:5],
            keyword=keyword,
            next_page=restaurants.next_page,
        )
    # 記錄使用者位置
    thread = threading.Thread(
        target=database.record_user_search, args=(user_id, latitude, longitude, keyword)
    )
    thread.start()
    return message


def parse_string(message: str):
    """投票資訊

    Args:
        message (str): 投票資訊內容
    """
    # default
    status = True
    event_name = ""
    available_dates = ""
    no_earlier = 0
    no_later = 24

    if not message:
        # input是空字串，回傳預設值
        status = False
        return status, event_name, available_dates, no_earlier, no_later

    try:
        date_candidates = re.findall(r"\d{4}-\d{1,2}-\d{1,2}", message)
        if len(date_candidates) == 1:
            date_candidates = date_candidates[0]
        elif len(date_candidates) > 1:
            date_candidates = "|".join(date_candidates)
        message = message.replace(date_candidates, "")

        event_name = message.replace(re.findall(r"//\d{1,2}/\d{1,2}", message)[0], "")
        daytime_constraint = re.findall(r"//(\d{1,2})/(\d{1,2})", message)[0]
        daytime_constraint = list(map(int, daytime_constraint))

        correct_date = None
        dates = date_candidates.split("|")
        for date in dates:
            try:
                new_date = datetime.strptime(date, "%Y-%m-%d")
                correct_date = True
            except ValueError:
                correct_date = False

        if correct_date:
            available_dates = date_candidates
        else:
            # 日期輸入格式錯誤
            status = False
            pass

        no_earlier = min(daytime_constraint)
        no_later = max(daytime_constraint)
        if no_earlier < 0 or no_later > 24 or no_earlier == no_later:
            # 時間限制格式錯誤
            status = False
    except:
        status = False
        return status, event_name, available_dates, no_earlier, no_later

    return status, event_name, available_dates, no_earlier, no_later
