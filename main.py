import asyncio
import datetime
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uvicorn

from src.scrap import scrap_service, daily_scraping_job
from src.db import server_connection, user_connection, MonitoringRedis
from src.Scheduler import SchedulerService

templates = Jinja2Templates(directory="src/resource/pages")

import multiprocessing


def run_worker():
    conn = server_connection.ServerConn()
    scheduler_service = SchedulerService(conn)
    scheduler_service.start_worker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[debug] setup daily schedule")
    worker_process = None
    try:
        schedule_conn = server_connection.ServerConn()
        scheduler_service = SchedulerService(schedule_conn)
        scheduler_service.schedule_task(daily_scraping_job)

        worker_process = multiprocessing.Process(target=run_worker, daemon=True)
        worker_process.start()

        print("[debug] Daily scraping schedule setup complete")

    except Exception as e:
        print(f"[debug] Schedule setup failed: {e}")

    yield

    if worker_process and worker_process.is_alive():
        print("[debug] Stopping worker process...")
        worker_process.terminate()  # 프로세스 종료
        worker_process.join()  # 종료될 때까지 대기
app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    cursor = user_connection.UserConn()

    items = cursor.get_contents()

    if not items:
        # 스크래핑 상태 확인
        status = cursor.get_scraping_status()
        if status.get("is_running") == "true":
            return RedirectResponse(url="/scraping")
        else:
            return RedirectResponse(url="/false")

    items = sorted(items, key=lambda x: (x.date, x.title))
    # cursor.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "items": items
    })


@app.get("/scraping")
async def scraping_page(request: Request):
    """
        스크래핑 진행 상황 페이지
    """
    cursor = user_connection.UserConn()
    status = cursor.get_scraping_status()


    if not status["is_running"] and status["progress"] == 100:
        return RedirectResponse("/")

    return templates.TemplateResponse("scraping.html", {
        "request": request,
        "status": status
    })


@app.get("/api/scraping-status")
async def scraping_status():
    cursor = user_connection.UserConn()
    return cursor.get_scraping_status()


@app.get("/false")
def fail_load(request: Request):
    return templates.TemplateResponse("fail_load.html", {"request":request})


if __name__ == "__main__":
    # connection = server_connection.ServerConn()
    # scheduler = SchedulerService(connection)
    #
    # if scheduler.check_last_schedule():
    #     for i in asyncio.run(scrap_service()):
    #         connection.insert_contents(i)
    #     connection.del_over_day()

    monitor = MonitoringRedis()
    monitor.using_redis_info()

    # connection.close()
    update_thread = threading.Thread()
    update_thread.start()

    print(f"{datetime.datetime.now()} : server on")
    uvicorn.run(app, host="127.0.0.1", port=1234)