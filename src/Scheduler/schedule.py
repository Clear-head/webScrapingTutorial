import datetime
import asyncio
from rq import Queue, Worker
from rq_scheduler import Scheduler


class SchedulerService:
    def __init__(self, conn):
        self.worker = None
        self.worker_task = None
        self.is_running = False
        self.conn = conn.get_cursor()
        self.queue = Queue(connection=self.conn)
        self.scheduler = Scheduler(connection=self.conn)


    def schedule_task(self, func):
        # next_time = datetime.datetime.now() + datetime.timedelta(days=1)
        # next_time = next_time.replace(hour=0, minute=1, second=0, microsecond=0)

        next_time = datetime.datetime.now() + datetime.timedelta(minutes=1)

        return self.scheduler.schedule(
            scheduled_time=next_time,
            func=func,
            interval=86400
        )

    async def start_worker(self):
        if self.is_running:
            print("[schedule] Already running")
            return

        self.is_running = True

        def run_worker():
            try:
                self.worker = Worker(["default"], connection=self.conn)
                self.worker.work(with_scheduler=True)

            except Exception as e:
                print(f"[schedule] Worker Exception: {e}")

            finally:
                self.is_running = False
                
        self.worker_task = asyncio.create_task(
            asyncio.create_task(run_worker())
        )


    def stop_worker(self):
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
        self.is_running = False


    def check_last_schedule(self):
        print(f"[schedule] recent schedule check")
        last_task = self.conn.get('last_scheduled')

        if not last_task:
            print(f"[schedule] no last_scheduled task, scrap now!")
            return True

        now = datetime.datetime.now()
        recent_task = datetime.datetime.strptime(last_task.decode("utf-8"), '%Y-%m-%d')
        if now > recent_task + datetime.timedelta(days=1):
            print(f"[schedule] recent task {recent_task}, scrap now!")
            return True
        else:
            print(f"[schedule] recent task {recent_task}, scrap later~!")
            return False
