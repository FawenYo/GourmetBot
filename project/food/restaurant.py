import re

import requests
from bs4 import BeautifulSoup


class Restaurant:
    def __init__(
        self,
        place_id: str,
        name: str,
        photo_url: str,
        open_now: bool,
        operating_time: dict,
        location: dict,
        address: str,
        rating: float,
        website: str,
        google_url: str,
        price: int = 0,
        phone_number: str = "無",
        reviews: list = [""],
        ifoodie_url: str = "https://ifoodie.tw/",
    ):
        self.place_id = place_id
        self.name = name
        self.photo_url = photo_url
        self.open_now = open_now
        self.operating_time = operating_time
        self.next_open_time = ""
        self.location = location
        self.address = address
        self.rating = rating
        self.website = website
        self.google_url = google_url
        self.price = price
        self.phone_number = phone_number
        self.reviews = reviews
        self.keywords = self.find_keywords(cid=google_url)
        self.ifoodie_url = ifoodie_url

    def find_keywords(self, cid: str) -> list:
        """Restaurant review keyword

        Args:
            cid (str): Google Maps CID
            reviews (list): Reviews list

        Returns:
            (list): Most frequent keywords (3 items)
        """
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36"
        }

        response = requests.get(f"{cid}&hl=zh-TW", headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        try:
            result = re.findall(r"規劃行程(.*)查看附近的餐廳", str(soup))
            if not result:
                result = re.findall(
                    r"規劃行程(.*),null,null,null,\[\[2\]\\n\]\\n\]\\n\]\\n\]\\n,",
                    str(soup),
                )

            result = result[0].replace("\\", " ")
            chinese_filter = re.compile(r"[^\u4e00-\u9fa5]+\s")
            result = re.sub(chinese_filter, "", result)
            result = result.strip('"').split(sep='"')
        except:
            print("error")
            result = []

        return result[:3]
