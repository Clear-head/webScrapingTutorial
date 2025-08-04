import time
from re import search
import requests
from bs4 import BeautifulSoup
from ..Item_class import item_info
from collections import deque
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


HEAD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/138.0.7204.169 Safari/537.36"
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




async def scrap_linkar() -> bool | list[item_info]:
    options = Options()
    options.add_argument("--disable-notifications")
    URL = "https://linkareer.com/list/contest?filterBy_categoryIDs=35&filterBy_targetIDs=3&filterBy_targetIDs=4&filterType=TARGET&orderBy_direction=DESC&orderBy_field=CREATED_AT"
    items = []

    for p in range(1, 3):
        res = requests.get(URL + f"&page={p}", headers=HEAD)
        if res.status_code != 200:
            return None
        
        driver = webdriver.Chrome(options=options)
        driver.get(URL + f"&page={p}")
        time.sleep(0.7)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "activity-image")))

        titles = driver.find_elements(By.CLASS_NAME, "activity-title")
        orgs = driver.find_elements(By.CLASS_NAME, "organization-name")
        dates = driver.find_elements(By.CLASS_NAME, "card-content")
        links = driver.find_elements(By.CLASS_NAME, "image-link")
        images = driver.find_elements(By.CLASS_NAME, "activity-image")
        

        #   이미지, 공모전 이름, 주관사, 마감일
        for date, title, org, link, image in zip(dates, titles, orgs, links, images):
            item = [False, False, False, False, False]
            
            try:
                WebDriverWait(driver, 10).until(lambda d: (("data" not in image.get_attribute("src").split(":")) or ("data" not in image.get_attribute("srcset").split(":"))))
            except:
                continue
            item[0] = image.get_attribute("src") if "data" not in image.get_attribute("src").split(":") else image.get_attribute("srcset")
            

            item[1] = title.text
            item[2] = org.text

            card_content = date.get_property("textContent")
            date_result = search(
                r'D-\d{2,3}',card_content.replace(title.text, "").replace(org.text, "")
                )
            item[3] = date_result.group() if date_result else False

            item[4] = link.get_attribute("href")


            if all(item):
                new = item_info(img=item[0], title=item[1], organize=item[2], date=item[3], link=item[4])
                print(new.img, new.title)
                items.append(new)
        driver.close()

    return list(items)
