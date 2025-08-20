import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.scrap import scrap_service
from src.db import server_connection, user_connection
from src.Scheduler import SchedulerService
import uvicorn

templates = Jinja2Templates(directory="src/resource/pages")
app = FastAPI()

@asynccontextmanager
async def setup_daily_schedule():
    """서버 시작 시 일일 스케줄 설정"""
    try:
        cursor = server_connection.ServerConn()
        scheduler_service = SchedulerService(cursor)
        # 매일 새벽 3시에 실행
        scheduler_service.schedule_task(daily_scraping_job)
        print("[debug] Daily scraping schedule setup complete")

        # 초기 상태 설정
        if not cursor.exists("scraping_status"):
            cursor.hset("scraping_status", mapping={
                "is_running": "false",
                "progress": "0",
                "current_site": "대기 중",
                "last_update": ""
            })

    except Exception as e:
        print(f"[debug] Schedule setup failed: {e}")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    cursor = user_connection.UserConn()

    items = cursor.get_contents()

    if not items:
        # 스크래핑 상태 확인
        status = cursor.get_cursor().hgetall("scraping_status")
        if status.get("is_running") == "true":
            return RedirectResponse(url="/scraping")
        else:
            return RedirectResponse(url="/false")

    items = sorted(items, key=lambda x: (x.date, x.title))
    cursor.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "items": items
    })


@app.get("/scraping")
async def scraping_page(request: Request):
    """스크래핑 진행 상황 페이지"""
    cursor = user_connection.UserConn()
    status_raw = cursor.get_cursor().hgetall("scraping_status")

    # Redis 데이터를 Python dict로 변환
    status = {
        "is_running": status_raw.get("is_running", "false") == "true",
        "progress": int(status_raw.get("progress", 0)),
        "current_site": status_raw.get("current_site", "대기 중"),
        "last_update": status_raw.get("last_update", ""),
        "error": status_raw.get("error", ""),
        "saved_count": status_raw.get("saved_count", "0")
    }

    # 완료되었으면 홈으로 리다이렉트
    if not status["is_running"] and status["progress"] == 100:
        return RedirectResponse("/")

    return templates.TemplateResponse("scraping.html", {
        "request": request,
        "status": status
    })

@app.get("/api/scraping-status")
async def get_scraping_status():
    cursor = server_connection.ServerConn()
    status_raw = cursor.get_cursor().hgetall("scraping_status")
    return {
        "is_running": status_raw.get("is_running", "false") == "true",
        "progress": int(status_raw.get("progress", 0)),
        "current_site": status_raw.get("current_site", "대기 중"),
        "last_update": status_raw.get("last_update", ""),
        "error": status_raw.get("error", ""),
        "saved_count": status_raw.get("saved_count", "0")
    }

@app.get("/false")
def fail_load(request: Request):
    return templates.TemplateResponse("fail_load.html", {"request":request})

if __name__ == "__main__":
    a = server_connection.ServerConn()
    if
    # for i in asyncio.run(await scrap_service()):
    #     a.insert_contents(i)
    # a.del_over_day()
    #
    a.using_redis_info()
    #
    # uvicorn.run(app, host="127.0.0.1", port = 1234)
