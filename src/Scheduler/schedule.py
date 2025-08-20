import datetime

from rq import Queue
from rq_scheduler import Scheduler
from rq import Worker


class SchedulerService:
    def __init__(self, conn):
        self.worker = None
        self.worker_thread = None
        self.is_running = False
        self.conn = conn.get_cursor()
        self.queue = Queue(connection=self.conn)
        self.scheduler = Scheduler(connection=self.conn)


    def schedule_task(self, func):
        # next_time = datetime.datetime.now() + datetime.timedelta(days=1)
        # next_time = next_time.replace(hour=0, minute=1, second=0, microsecond=0)

        next_time = datetime.datetime.now() + datetime.timedelta(minutes=1)

        # self.worker.work(with_scheduler=True)
        job = self.scheduler.schedule(
            scheduled_time=next_time,
            func=func,
            interval=86400
        )

    def start_worker(self):
        """백그라운드에서 워커 시작"""
        if self.is_running:
            print("Worker가 이미 실행 중입니다.")
            return

        self.is_running = True
        self.worker = Worker(['default'], connection=self.conn)

        # 별도 스레드에서 워커 실행
        def run_worker():
            try:
                self.worker.work(with_scheduler=True)
            except KeyboardInterrupt:
                print("Worker 중단됨")
            finally:
                self.is_running = False

        self.worker_thread = threading.Thread(target=run_worker, daemon=True)
        self.worker_thread.start()
        print("RQ Worker 시작됨")

    def start_task(self):
        pass

    def stop_task(self):
        pass


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
