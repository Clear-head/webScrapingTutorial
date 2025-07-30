import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
from .Item_class import item_info
from collections import deque


URL = "https://www.allforyoung.com/posts/contest?tags=20"

HEAD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/114.0.0.0 Safari/537.36"
}

def scrap_html()->bool | list[item_info]:
    res = requests.get(URL, headers=HEAD)
    if res.status_code != 200:
        return False

    items = []

    soup = BeautifulSoup(res.content, 'html.parser')
    objs = soup.select("body > div > div:nth-child(2) > main > section > div.main-responsive > div > div.space-y-20 > ul > a > div > div")

    item = [None, None, None, None]       # img, title, ori, date

    for obj in objs:

        img = obj.select_one("figure > img")
        txt = obj.select_one("div > p")
        dt = obj.select_one("div")

        if img != None:
            # item[0] = extract_img(img.get("src"))
            item[0] = img.get("src")

        if txt != None:
            if item[1] == None:
                item[1] = txt.text
            else:
                item[2] = txt.text

        if dt != None:
            item[3] = dt.text

        if None not in item:
            new = item_info(*item)
            items.append(new)
            item = [None, None, None, None]

    return list(items)

    
def extract_img(src)->Image:
    img_res = requests.get(src)
    img = Image.open(BytesIO(img_res.content))
    return img