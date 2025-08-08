from ..Item_class import item_info
import asyncio
import aiohttp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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

async def scrap_batch():

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
    semaphore = asyncio.Semaphore(5)  # 동시 페이지 처리 수 제한
    
    
    async with aiohttp.ClientSession(
        headers=HEAD, 
        connector=connector, 
        timeout=timeout
    ) as session:
        
        # 모든 페이지를 동시에 처리
        page_task1 = [
            process_wivity_batch(session, url, semaphore) for url in url_list
        ]
        page_task2 = [scrap_linkar(session, get_driver()), scrap_allfor(session)]

        page_task3 = [scrap_thinkGood(session, get_driver())]
        
        # 모든 페이지 처리 완료 대기
        print("========= task 1 start =========")
        page_results = await asyncio.gather(*page_task1, return_exceptions=True)

        print("========= task 2 start =========")
        page_results.extend(await asyncio.gather(*page_task2, return_exceptions=True))
        
        print("========= task 3 start =========")
        page_results.extend(await asyncio.gather(*page_task3, return_exceptions=True))
        
        # 결과 통합
        all_items = []
        for result in page_results:
            if result and not isinstance(result, Exception):
                all_items.extend(result)
    
    print(f"Total items scraped: {len(all_items)}")
    return all_items if all_items else []