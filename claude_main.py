import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.scrap import scrap_service
from src.db import server_connection
from src.Scheduler import SchedulerService
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
            "current_site": "사이트 수집 중..."
        })

        items = asyncio.run(scrap_service())

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

