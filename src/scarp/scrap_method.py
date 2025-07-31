import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
from ..Item_class import item_info
from collections import deque
import json


HEAD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/114.0.0.0 Safari/537.36"
}


def scrap_allfor() -> bool | list[item_info]:
    URL = "https://www.allforyoung.com/posts/contest?tags=20"
    LINK_FRONT = "https://www.allforyoung.com"
    items = []

    page_cnt = 0
    while True:
        page_cnt += 1
        res = requests.get(URL+f"&page={page_cnt}", headers=HEAD)
        if res.status_code != 200:
            break

        soup = BeautifulSoup(res.content, 'html.parser')

        #   상세 페이지 링크
        links_selet = soup.select("body > div > div:nth-child(2) > main > section > div.main-responsive > div > div.space-y-20 > ul > a")
        links = deque()
        for i in links_selet:
            links.append(LINK_FRONT + i.get("href"))

        item = [None, None, None, None]       # img, title, ori, date, link

        #   이미지, 공모전 이름, 주관사, 마감일
        objs = soup.select("body > div > div:nth-child(2) > main > section > div.main-responsive > div > div.space-y-20 > ul > a > div > div")

        for obj in objs:

            img = obj.select_one("figure > img")
            txt = obj.select("div:nth-child(2) > p")
            dt = obj.select_one("div")

            if img != None:
                item[0] = img.get("src")

            if txt != None:
                for t in txt:
                    if item[1] == None:
                        item[1] = t.text

                    else:
                        item[2] = t.text

            if dt != None:
                item[3] = dt.text

            if None not in item:
                if not item[3] == "D-day":
                    new = item_info(img=item[0], title=item[1], organize=item[2], date=item[3], link=links.popleft())
                    
                    items.append(new)
                item = [None, None, None, None]

    return list(items)




def scrap_linkar() -> bool | list[item_info]:
    URL = "https://api.linkareer.com/graphql?operationName=gqlActivityListFromAdsByPlacementCode&variables=%7B%22isActivityCard%22%3Afalse%2C%22isActivityListItem%22%3Afalse%2C%22isEducation%22%3Afalse%2C%22isRecruit%22%3Afalse%2C%22isActivity%22%3Atrue%2C%22adPlacementCode%22%3A%22activity-contest-notice-banner%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%2269701fd2a1169a3e4a6255a73ee8863ff8d450ea80751b42be8ea97a0c9cce0e%22%7D%7D"
    LINK_FORNT = "https://linkareer.com"
    items = []
    res = requests.get(URL, headers=HEAD)
    if res.status_code != 200:
        return None

    contents = json.loads(res.content.decode("UTF-8"))['data']['activityListFromAdsByPlacementCode']

    return list(items)
