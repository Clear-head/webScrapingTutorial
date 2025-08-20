import asyncio
from datetime import datetime

import aiohttp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from ..classes.item_list_class import ItemList
from src.scrap.scrap_method import scrap_allfor, scrap_linkar, process_wivity_batch, scrap_thinkGood

HEAD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/138.0.7204.169 Safari/537.36"
}

def get_driver():

    options = Options()
    options.add_argument("--disable-notifications")
    # options.add_argument("headless")
    options.add_argument('--log-level=3')

    driver = webdriver.Chrome(options=options)

    return driver

async def scrap_service():

    print("============= Scrap Start =============")

    URL1 = "https://www.wevity.com/index.php?c=find&s=1&gub=1&cidx=21"
    URL2 = "https://www.wevity.com/index.php?c=find&s=1&gub=1&cidx=20"
    URL3 = "https://www.wevity.com/index.php?c=find&s=1&gub=1&cidx=22"
    url_list = [URL1, URL2, URL3]
    
    for j in [URL1, URL2, URL3]:
        url_list.append(j + f"&gp=2")

    # 동시 연결 수 제한 (서버 부하 방지)
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=30)
    semaphore = asyncio.Semaphore(10)
    
    
    async with aiohttp.ClientSession(
        headers=HEAD, 
        connector=connector, 
        timeout=timeout
    ) as session:

        page_task1 = [
            process_wivity_batch(session, url, semaphore) for url in url_list
        ]
        page_task2 = [scrap_linkar(session, get_driver()), scrap_allfor(session)]

        page_task3 = [scrap_thinkGood(session, get_driver())]
        
        print("========= task 1 start =========")
        page_results = await asyncio.gather(*page_task1, return_exceptions=True)

        print("========= task 2 start =========")
        page_results.extend(await asyncio.gather(*page_task2, return_exceptions=True))

        print("========= task 3 start =========")
        page_results.extend(await asyncio.gather(*page_task3, return_exceptions=True))
        
        # 결과 통합
        all_items = ItemList()
        for result in page_results:
            if result and not isinstance(result, Exception):
                all_items.extends(result)

    
    print(f"[debug] Total items scraped: {len(all_items)}")
    return all_items if all_items else []


def daily_scraping_job(conn):
    """RQ Worker에서 실행될 스크래핑 작업"""
    try:


        print("============= Daily Scraping Job Start =============")

        update_scrap_state(
            conn,
            {
                "is_running": "true",
                "progress": "0",
                "current_site": "스크래핑 시작",
                "start_time": datetime.now().isoformat()
            }
        )

        update_scrap_state(
            conn,
            {
                "progress": "30",
                "current_site": "사이트 수집 중..."
            }
        )


        items = asyncio.run(scrap_service())

        update_scrap_state(
            conn,
            {
                "progress": "80",
                "current_site": "데이터 저장 중..."
            }
        )

        # 데이터 저장
        saved_count = 0
        for item in items:
            if conn.insert_contents(item):
                saved_count += 1

        update_scrap_state(
            conn,
            {
                "progress": "90",
                "current_site": "기존 데이터 정리 중..."
            }
        )

        conn.del_over_day()

        # 완료 상태 업데이트

        update_scrap_state(
            conn,
            {
                "is_running": "false",
                "progress": "100",
                "current_site": f"완료 - {saved_count}개 항목 저장",
                "last_update": datetime.now().isoformat(),
                "saved_count": str(saved_count)
            }
        )

        conn.close()

        print("============= Daily Scraping Job Complete =============")

    except Exception as e:
        update_scrap_state(
            conn,
            {
                "is_running": "false",
                "error": str(e),
                "current_site": "오류 발생"
            }
        )
        print(f"[debug] Daily scraping error: {e}")

def update_scrap_state(conn, dic):
    cursor = conn.get_cursor()
    try:
        cursor.hset("scraping_status", mapping={
            **dic
        })
    except Exception as e:
        return False
    return True