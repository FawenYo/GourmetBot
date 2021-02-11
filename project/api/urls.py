import sys
from datetime import datetime

import config
import pandas as pd
import requests
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from weather.main import Weather

sys.path.append(".")
from food.main import RestaurantInfo
from line.templates import Template

api = APIRouter()


@api.get("/api/export/history")
async def export_history():
    data = pd.DataFrame()
    results = config.db.history.find({})
    for each in results:
        each["latitude"], each["longitude"] = each["location"]
        del each["location"]
        data = data.append(each, ignore_index=True)
    data.to_csv("history.csv", encoding="utf_8_sig")
    return FileResponse("history.csv")


# API - 當地天氣
@api.get("/api/weather/")
async def weather(loc: str):
    try:
        lat, lng = loc.split(",")
        weather_data = Weather()
        weather_data.fetch_data(latitude=lat, longitude=lng)
        config.console.log(weather_data.__dict__)
        return weather_data.__dict__
    except KeyError:
        error_message = {"status": "error", "error_message": "Parameters value error."}
        return error_message


# API - 地點附近餐廳
@api.get("/api/restaurant/")
async def restaurant(keyword: str, loc: str):
    start = datetime.now()
    try:
        latitude, longitude = loc.split(",")
        restaurant_data = RestaurantInfo(
            latitude=latitude, longitude=longitude, keyword=keyword
        )
        restaurant_data.nearby()
        config.console.log(restaurant_data.__dict__)
        end = datetime.now()
        return f"Total Process Time: {end - start}."
    except KeyError:
        error_message = {"status": "error", "error_message": "Parameters value error."}
        return error_message


# API - LIFF share Flex template
@api.get("/api/liffshare")
async def liff_share(pull_id: str):
    message = Template().liff_share(pull_id=pull_id)
    return {"status": "success", "data": message}


# API - Vote page restaurant data
@api.get("/api/vote/{pull_id}", response_class=JSONResponse)
async def get_pull_data(pull_id):
    pull_data = config.db.vote_pull.find_one({"_id": pull_id})
    if pull_data:
        message = {"status": "success", "restaurants": pull_data["restaurants"]}
    else:
        message = {"status": "error", "error_message": "Vote pull not found."}
    return message


# API - deploy done
@api.get("/api/deploy", response_class=JSONResponse)
async def deploy():
    commit_info = requests.get(config.GITHUB_REPO_URL).json()
    commit_committer = commit_info["commit"]["commit"]["committer"]["name"]
    commit_date = commit_info["commit"]["commit"]["committer"]["date"]
    commit_message = commit_info["commit"]["commit"]["message"]
    commit_url = commit_info["commit"]["html_url"]
    for token in config.AUTHORS_NOTIFY_TOKEN:
        message = f"New Commit\n提交者：{commit_committer}\n提交日期：{commit_date}\n提交訊息：{commit_message}\n詳細資訊：{commit_url}"
        config.lotify_client.send_message(access_token=token, message=message)
    return {"status": "success"}