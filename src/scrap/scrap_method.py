import time
from re import search
from bs4 import BeautifulSoup
from ..Item_class import item_info
from collections import deque
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio


"""

    올포영

"""
async def scrap_allfor(session) -> list[item_info]:
    URL = "https://www.allforyoung.com/posts/contest?tags=20"
    LINK_FRONT = "https://www.allforyoung.com"
    items = []

    page_cnt = 0
    while True:
        page_cnt += 1

        list_content, _ = await fetch_page(session, URL+f"&page={page_cnt}")
        if not list_content:
            break

        soup = BeautifulSoup(list_content, 'html.parser')

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


"""

    위비티

"""
async def scrap_wivity(content, url):
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # 이미지, 공모전 이름, 주관사, 마감일, 상세링크
        item = [False, False, False, False, False]
        
        # 이미지
        img_elem = soup.select_one("div.thumb > img")
        if img_elem and img_elem.get("src"):
            item[0] = "https://www.wevity.com" + img_elem.get("src")
        
        # 제목
        title_elem = soup.select_one("div.tit-area > h6.tit")
        if title_elem:
            item[1] = title_elem.text.strip()
        
        # 카드 정보들
        cards = soup.select("ul.cd-info-list > li")
        if len(cards) >= 8:
            field = cards[0].text.replace(",", "").split()
            if len(set(["영상/UCC/사진", "예체능/미술/음악"]) & set(field)) > 0:
                return None

            # 참가자격 확인 (일반인 포함 여부)
            ap = cards[1].text.replace(",", "").split()
            if ("일반인" not in ap) and ("제한없음" not in ap):
                return None
            
            # 주관사
            org_text = cards[2].text.strip().split("\n")
            if len(org_text) > 1:
                item[2] = org_text[1].replace("\t\t\t\t\t", "").strip()
            
            # 마감일
            date_parts = cards[4].text.strip().split()
            if date_parts:
                item[3] = date_parts[-1]
            
            # 홈페이지
            link_parts = cards[7].text.strip().split()
            if link_parts:
                item[4] = link_parts[-1]
        
        # 모든 정보가 있는지 확인
        if all(item):
            return item_info(
                img=item[0], 
                title=item[1], 
                organize=item[2], 
                date=item[3], 
                link=item[4]
            )
        return None
        
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return None

async def process_wivity_batch(session, page, semaphore):
    FRONT_URL = "https://www.wevity.com/index.php"
    
    async with semaphore:  # 동시 요청 수 제한
        try:
            # 목록 페이지 가져오기
            list_content, _ = await fetch_page(session, page)
            if not list_content:
                return []
            
            soup = BeautifulSoup(list_content, 'html.parser')
            
            # 상세 페이지 URL들 수집
            details = soup.select("ul.list > li > div.tit > a")
            detail_urls = [FRONT_URL + detail.get("href") for detail in details]
            
            # 모든 상세 페이지들을 동시에 요청
            tasks = [fetch_page(session, url) for url in detail_urls]
            detail_responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 파싱 작업들을 동시에 실행
            parse_tasks = []
            for content, url in detail_responses:
                if content and not isinstance(content, Exception):
                    parse_tasks.append(scrap_wivity(content, url))
            
            # 모든 파싱 작업 완료 대기
            parsed_items = await asyncio.gather(*parse_tasks, return_exceptions=True)
            
            # 유효한 아이템 필터링
            valid_items = [
                item for item in parsed_items 
                if item and not isinstance(item, Exception)
            ]
            
            print(f"Successfully parsed {len(valid_items)} items")
            return valid_items
            
        except Exception as e:
            print(f"Error processing page: {e}")
            return []
        


"""

    링커리어
    selenium

"""
async def scrap_linkar(session, driver) -> list[item_info]:
    URL = "https://linkareer.com/list/contest?filterBy_categoryIDs=35&filterBy_targetIDs=3&filterBy_targetIDs=4&filterType=TARGET&orderBy_direction=DESC&orderBy_field=CREATED_AT"
    items = []

    for p in range(1, 3):

        list_content, _ = await fetch_page(session, URL+f"&page={p}")
        if not list_content:
            return items

        driver.get(URL + f"&page={p}")
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
                items.append(new)
    driver.close()

    return list(items)


async def scrap_thinkGood(session):
    # todo: 싱크굳 이거 해야함
    items = []
    list_content, _ = await fetch_page(session, URL)
    if not list_content:
        return items


async def scrap_allCon(session):
    URL_FRONT = "https://www.all-con.co.kr/list/contest/1/1"
    URL_OPTION = "?sortname=cl_order&sortorder=asc&stx=&sfl=&t=1&ct=4&sc=23&tg=2"
    items = []
    list_content, _ = await fetch_page(session, URL)
    if not list_content:
        return items


async def scrap_thinkYou(session):
    pass


async def scrap_detizen(session):
    pass



"""

    Utils

"""
async def fetch_page(session, url):
    """
    
        세션 만들어서 링크 유효성 검증, util 로 뺄 가능성 있음
    
    """
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                content = await response.text()
                return content, url
            else:
                print(f"HTTP {response.status} for {url}")
                return None, url
            
    except asyncio.TimeoutError:
        print(f"Timeout for {url}")
        return None, url
    
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None, url