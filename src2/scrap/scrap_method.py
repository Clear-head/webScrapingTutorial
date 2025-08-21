import time
from re import search
from bs4 import BeautifulSoup
from ..classes.Item_class import ItemInfo
from ..classes.item_list_class import ItemList
from collections import deque
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import asyncio


"""

    올포영

"""
async def scrap_allfor(session):
    URL = "https://www.allforyoung.com/posts/contest?tags=20"
    LINK_FRONT = "https://www.allforyoung.com"
    items = ItemList()

    for page_cnt in range(1, 4):

        list_content, _ = await fetch_page(session, URL+f"&page={page_cnt}")
        if not list_content:
            print(f"[debug] all for young page {page_cnt} is None")
            continue

        print(f"[debug] all for young page {page_cnt} scrap started.")

        soup = BeautifulSoup(list_content, 'html.parser')

        #   상세 페이지 링크
        links_select = soup.select("body > div > div:nth-child(2) > main > section > div.main-responsive > div > div.space-y-20 > ul > a")
        links = deque()
        for i in links_select:
            links.append(LINK_FRONT + i.get("href"))

        item = [None, None, None, None]       # img, title, ori, date, link

        #   이미지, 공모전 이름, 주관사, 마감일
        objs = soup.select("body > div > div:nth-child(2) > main > section > div.main-responsive > div > div.space-y-20 > ul > a > div > div")

        for obj in objs:

            img = obj.select_one("figure > img")
            txt = obj.select("div:nth-child(2) > p")
            dt = obj.select_one("div")

            if img is not None:
                item[0] = img.get("src2")

            if txt is not None:
                for t in txt:
                    if item[1] is None:
                        item[1] = t.text

                    else:
                        item[2] = t.text

            if dt is not None:
                item[3] = dt.text

            if None not in item:
                if not item[3] == "D-day":
                    new = ItemInfo(img=item[0], title=item[1], organize=item[2], date=item[3], link=links.popleft())
                    
                    items.add_item(new)
                item = [None, None, None, None]
    print(f"[debug] Successfully allforyoung parsed {len(items)} items")
    return items


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
        if img_elem and img_elem.get("src2"):
            item[0] = "https://www.wevity.com" + img_elem.get("src2")
        
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
                item[3] = item[3][:2] + item[3][2:]
            
            # 홈페이지
            link_parts = cards[7].text.strip().split()
            if link_parts:
                item[4] = link_parts[-1]
        
        # 모든 정보가 있는지 확인
        if all(item):
            return ItemInfo(
                img=item[0], 
                title=item[1], 
                organize=item[2], 
                date=item[3], 
                link=item[4]
            )
        return None
        
    except Exception as e:
        print(f"[debug] Error parsing {url}: {e}")
        return None

async def process_wivity_batch(session, page, semaphore):
    FRONT_URL = "https://www.wevity.com/index.php"
    
    async with semaphore:  # 동시 요청 수 제한
        try:
            # 목록 페이지 가져오기
            list_content, _ = await fetch_page(session, page)
            if not list_content:
                print(f"[debug] wivity page {page} is None")
                return ItemList()
            
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

            valid_items = ItemList()
            for item in parsed_items:
                if item and not isinstance(item, Exception):
                    valid_items.add_item(item)
            
            print(f"[debug] Successfully wivity parsed {len(valid_items)} items")
            return valid_items
            
        except Exception as e:
            print(f"[debug] Error processing page: {e}")
            return []
        


"""

    링커리어
    selenium

"""
async def scrap_linkar(session, driver):
    URL = "https://linkareer.com/list/contest?filterBy_categoryIDs=35&filterBy_targetIDs=3&filterBy_targetIDs=4&filterType=TARGET&orderBy_direction=DESC&orderBy_field=CREATED_AT"
    items = ItemList()

    for p in [URL+"&page=1", URL+"&page=2"]:

        list_content, _ = await fetch_page(session, p)

        if not list_content:
            print(f"[debug] linkereer page {p[-1]} is None")
            continue
        try:
            driver.get(p)
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
                    WebDriverWait(driver, 10).until(lambda d: (("data" not in image.get_attribute("src2").split(":")) or ("data" not in image.get_attribute("srcset").split(":"))))
                except:
                    continue

                item[0] = image.get_attribute("src2") if "data" not in image.get_attribute("src2").split(":") else image.get_attribute("srcset")
                item[1] = title.text
                item[2] = org.text

                card_content = date.get_property("textContent")
                date_result = search(
                    r'D-\d{2,3}',card_content.replace(title.text, "").replace(org.text, "")
                    )
                
                item[3] = date_result.group() if date_result else False
                item[4] = link.get_attribute("href")

                if all(item):
                    new = ItemInfo(img=item[0], title=item[1], organize=item[2], date=item[3], link=item[4])
                    items.add_item(new)

        except Exception as e:
            print(f"[debug] error linkareer : {e}")
            continue
        
    driver.quit()
    print(f"[debug] Successfully Linkerear parsed {len(items)} items")
    return items


"""

    씽굿  상세 페이지 url 수집 불가.

"""
async def scrap_thinkGood(session, driver):
    possible_selectors = [
        ".button-list",
        "button[onclick*='back']",
        "button[onclick*='close']",
        ".btn-back",
        ".btn-close",
        "a[href*='back']"
    ]
    URL = "https://www.thinkcontest.com/thinkgood/user/contest/index.do#PxyyoRLHIcgvNg6HiHNz_mp_cuclMrohRDGEjn6hvDsggetrTQxNWBBQR1mPnaRxjI93xVlR_kFjCl9g5hFBO1N6UGMkDhLA2ecFAf6UhFU"
    items = ItemList()
    list_content, _ = await fetch_page(session, URL)
    if not list_content:
        return items
    
    driver.get(URL)
    time.sleep(1.5)
    wait = WebDriverWait(driver, 10)

    a = driver.find_elements(By.CLASS_NAME, "gotoLeftLink")     # ㄹㅇ a 태그임 ㅋㅋ
    for i in a:
        if i.get_attribute("data-search_type") == "contest_field" and i.get_attribute("data-value") in ["CCFD002", "CCFD017", "CCFD003"]:
            i.click()
        elif i.get_attribute("data-search_type") == "enter_qualified" and i.get_attribute("data-value") in ["PCQF008", "PCQF010"]:
            i.click()

    initial_details = get_tk_details(wait, driver)
    total_details = len(initial_details)

    for i in range(total_details):
        #   이미지, 공모전 이름, 주관사, 마감일
        item = [False, False, False, False, False]

        #   d-day and click
        date = click_safely(i, driver, wait)
        if not date:
            continue
        else:
            item[3] = date

        try:

            #   제목
            title = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "contest-view__title"))).text
            item[1] = title

            #   이미지
            img = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "contestimg"))).get_attribute("src2")
            item[0] = img

            #   주최, 링크
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.txt")))
            tits = driver.find_elements(By.CSS_SELECTOR, "div.tit")
            txts = driver.find_elements(By.CSS_SELECTOR, "div.txt")

            for tit, txt in zip(tits, txts):

                if tit.text == "주최":
                    item[2] = txt.text

                elif tit.text == "주관" and tit.text != txt.text:
                    item[2] += " / " + txt.text

                elif tit.text == "홈페이지":
                    item[4] = txt.find_element(By.TAG_NAME, "a").get_attribute("href")

            try:
                button_clicked = False
                for selector in possible_selectors:
                    try:
                        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                        next_btn = driver.find_element(By.CSS_SELECTOR, selector)
                        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                        driver.execute_script("arguments[0].click();", next_btn)
                        button_clicked = True
                        break
                    except:
                        continue
                
                if not button_clicked:
                    driver.back()

            except Exception as e:
                driver.back()
            finally:
                if all(item):
                    new = ItemInfo(img=item[0], title=item[1], organize=item[2], date=item[3], link=item[4])
                    items.add_item(new)

        except Exception as e:
            try:
                driver.back()
                time.sleep(1)
            except:
                pass

    driver.quit()

    print(f"[debug] Successfully thinkGood parsed {len(items)} items")
    return items


def get_tk_details(wait, driver):
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#dataList > tr")))
    return driver.find_elements(By.CSS_SELECTOR, "#dataList > tr")

def click_safely(index, driver, wait):     #   D-day 가져오고 클릭해서 상세페이지 들감
    max_retries = 3
    for attempt in range(max_retries):
        try:
            details = get_tk_details(wait, driver)
            
            if index < len(details):
                detail = details[index]
                driver.execute_script("arguments[0].scrollIntoView(true);", detail)
                time.sleep(1)
                date = driver.find_element(By.CSS_SELECTOR, "#dataList > tr:nth-child(1) > td:nth-child(4)").text
                driver.execute_script("arguments[0].click();", detail)
                return date
            else:
                print(f"[debug] 인덱스 {index}가 범위를 벗어났습니다.")
                return False
                
        except StaleElementReferenceException:
            print(f"[debug] StaleElement 오류 발생, 재시도 {attempt + 1}/{max_retries}")
            time.sleep(1)
        except Exception as e:
            print(f"[debug] 클릭 오류: {e}")
            time.sleep(1)
    
    return False

"""

    Utils

"""
async def fetch_page(session, url):
    """
    
        세션 만들어서 링크 유효성 검증, util 로 뺄 가능성 있음
    
    """
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                content = await response.text()
                return content, url
            else:
                print(f"[debug] HTTP {response.status} for {url}")
                return False, url
            
    except asyncio.TimeoutError:
        print(f"[debug] Timeout for {url}")
        return None, url
    
    except Exception as e:
        print(f"[debug] Error fetching {url}: {e}")
        return None, url