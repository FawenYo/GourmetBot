import sys
from datetime import datetime

import pytz

sys.path.append(".")
from config import db


def record_user_search(user_id: str, lat: float, lng: float, search: str):
    """LINE Bot - Record user

    Args:
        user_id (str): LINE User ID
        lat (float): Location latitude
        lng (float): Location longitude
        search (str): Search Texts
    """
    now = datetime.now(tz=pytz.timezone("Asia/Taipei"))
    if search == "":
        search = "隨便"
    data = {
        "user_id": user_id,
        "location": [lat, lng],
        "search": search,
        "time": now,
    }
    db.history.insert_one(data)


def add_restaurant(restaurant: object, keyword: str):
    """New restaurant

    Args:
        restaurant (object): Restaurant data (food/model.py)
        keyword (str): Restaurant category
    """
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


def create_vote(
    creator: str, vote_id: str, vote_link: str, restaurants: list, end_date: datetime
):
    """Create vote event

    Args:
        creator (str): Creator's LINE User ID
        vote_id (str): Vote's event ID
        vote_link (str): When2meet link
        restaurants (list): Restaurant list
        end_date (datetime): Vote end date
    """
    now = datetime.now(tz=pytz.timezone("Asia/Taipei"))
    if not db.vote_pull.find_one({"_id": vote_id}):
        data = {
            "_id": vote_id,
            "creator": creator,
            "vote_link": vote_link,
            "end_date": end_date,
            "restaurants": restaurants,
            "create_time": now,
            "participants": {},
        }
        db.vote_pull.insert_one(data)
        user_data = db.user.find_one({"user_id": creator})
        user_data["vote"] = []
        db.user.update_one({"user_id": creator}, {"$set": user_data})
