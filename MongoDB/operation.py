import sys
from datetime import datetime

import pytz
from pymongo import results

sys.path.append(".")
from config import db


def new_user(user_id: str):
    now = datetime.now(tz=pytz.timezone("Asia/Taipei"))
    data = {"user_id": user_id, "add_time": now, "favorite": [], "vote": []}
    db.user.insert_one(data)


def delete_user(user_id: str):
    db.user.delete_one({"user_id": user_id})


def record_user_location(user_id: str, lat: float, lng: float):
    now = datetime.now(tz=pytz.timezone("Asia/Taipei"))
    data = {
        "user_id": user_id,
        "location": [lat, lng],
        "time": now,
    }
    db.history.insert_one(data)


def add_restaurant(restaurant, keyword):
    now = datetime.now(tz=pytz.timezone("Asia/Taipei"))
    result = db.restaurant.find_one({"name": restaurant.name})
    if not result:
        data = {
            "place_id": restaurant.place_id,
            "name": restaurant.name,
            "photo_url": restaurant.photo_url,
            "operating_time": restaurant.operating_time,
            "location": restaurant.location,
            "loc": [restaurant.location["lng"], restaurant.location["lat"]],
            "address": restaurant.address,
            "rating": restaurant.rating,
            "website": restaurant.website,
            "google_url": restaurant.google_url,
            "price": restaurant.price,
            "phone_number": restaurant.phone_number,
            "reviews": restaurant.reviews,
            "keywords": restaurant.keywords,
            "ifoodie_url": restaurant.ifoodie_url,
            "category": [],
            "time": now,
        }
        if keyword:
            data["category"].append(keyword)
        db.restaurant.insert_one(data)
    else:
        if keyword not in result["category"]:
            result["category"].append(keyword)
            db.restaurant.update_one({"name": restaurant.name}, {"$set": result})


def create_vote(vote_id, restaurants):
    now = datetime.now(tz=pytz.timezone("Asia/Taipei"))
    if not db.vote_pull.find_one({"_id": vote_id}):
        data = {
            "_id": vote_id,
            "restaurants": restaurants,
            "create_time": now,
        }
        db.vote_pull.insert_one(data)
