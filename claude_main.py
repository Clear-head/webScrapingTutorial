import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.scrap import scrap_batch
from src.db import conn_db
from src.scedule import SchedulerService
import redis
import uvicorn
from contextlib import asynccontextmanager

templates = Jinja2Templates(directory="src/resource/pages")
app = FastAPI()

# Redis 연결 (스케줄러용)
redis_conn = redis.Redis(host='localhost', port=6379, decode_responses=True)
scheduler_service = SchedulerService(redis_conn)


def daily_scraping_job():
    """RQ Worker에서 실행될 스크래핑 작업"""
    try:
        # 작업 상태 업데이트
        redis_conn.hset("scraping_status", mapping={
            "is_running": "true",
            "progress": "0",
            "current_site": "스크래핑 시작",
            "start_time": datetime.now().isoformat()
        })

        print("============= Daily Scraping Job Start =============")

        # 데이터베이스 연결
        cursor = conn_db.Conn()

        # 스크래핑 실행
        redis_conn.hset("scraping_status", mapping={
            "progress": "30",
            "current_site": "위비티 사이트 수집 중..."
        })

        items = asyncio.run(scrap_batch())

        redis_conn.hset("scraping_status", mapping={
            "progress": "80",
            "current_site": "데이터 저장 중..."
        })

        # 데이터 저장
        saved_count = 0
        for item in items:
            if cursor.insert_contents(item):
                saved_count += 1

        redis_conn.hset("scraping_status", mapping={
            "progress": "90",
            "current_site": "기존 데이터 정리 중..."
        })
        cursor.del_over_day()

        # 완료 상태 업데이트
        redis_conn.hset("scraping_status", mapping={
            "is_running": "false",
            "progress": "100",
            "current_site": f"완료 - {saved_count}개 항목 저장",
            "last_update": datetime.now().isoformat(),
            "saved_count": str(saved_count)
        })

        # 마지막 스케줄 시간 저장
        cursor.set_schedule(datetime.now().strftime('%Y-%m-%d'))
        cursor.close()

        print("============= Daily Scraping Job Complete =============")

    except Exception as e:
        redis_conn.hset("scraping_status", mapping={
            "is_running": "false",
            "error": str(e),
            "current_site": "오류 발생"
        })
        print(f"[debug] Daily scraping error: {e}")


@asynccontextmanager
async def setup_daily_schedule():
    """서버 시작 시 일일 스케줄 설정"""
    try:
        # 매일 새벽 3시에 실행
        scheduler_service.schedule_task(daily_scraping_job)
        print("[debug] Daily scraping schedule setup complete")

        # 초기 상태 설정
        if not redis_conn.exists("scraping_status"):
            redis_conn.hset("scraping_status", mapping={
                "is_running": "false",
                "progress": "0",
                "current_site": "대기 중",
                "last_update": ""
            })

    except Exception as e:
        print(f"[debug] Schedule setup failed: {e}")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    cursor = conn_db.Conn()
    items = cursor.get_contents()

    if not items:
        # 스크래핑 상태 확인
        status = redis_conn.hgetall("scraping_status")
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
    status_raw = redis_conn.hgetall("scraping_status")

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
    """AJAX용 상태 API"""
    status_raw = redis_conn.hgetall("scraping_status")
    return {
        "is_running": status_raw.get("is_running", "false") == "true",
        "progress": int(status_raw.get("progress", 0)),
        "current_site": status_raw.get("current_site", "대기 중"),
        "last_update": status_raw.get("last_update", ""),
        "error": status_raw.get("error", ""),
        "saved_count": status_raw.get("saved_count", "0")
    }


if __name__ == "__main__":
    # 서버 시작 시 Redis 정보만 확인
    a = conn_db.Conn()
    a.using_redis_info()

    uvicorn.run(app, host="127.0.0.1", port=1234)