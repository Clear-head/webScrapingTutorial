import datetime
from rq import Queue, Worker
from rq_scheduler import Scheduler


class SchedulerService:
    def __init__(self, conn):
        self.worker = None
        self.is_running = False
        self.conn = conn.get_cursor()
        self.queue = Queue("default", connection=self.conn)
        self.scheduler = Scheduler(queue=self.queue, connection=self.conn)


    def schedule_task(self, func):
        # next_time = datetime.datetime.now() + datetime.timedelta(days=1)
        # next_time = next_time.replace(hour=0, minute=1, second=0, microsecond=0)

        next_time = datetime.datetime.now() + datetime.timedelta(seconds=30)

        print(f"[schedule] next scraping time: {next_time}")

        try:
            scheduled_jobs = self.scheduler.get_jobs()
            for job in scheduled_jobs:
                if hasattr(job, 'func_name') and job.func_name == func.__name__:
                    print(f"[schedule] Cancelling existing job: {job.id}")
                    job.cancel()
        except Exception as e:
            print(f"[schedule] Error checking existing jobs: {e}")


        job = self.scheduler.schedule(
            scheduled_time=next_time,
            func=func
        )

        print(f"[schedule] scheduled job")

        return job

    def start_worker(self):
        self.worker = Worker([self.queue], connection=self.conn)
        self.is_running = True
        self.worker.work()

    def stop_worker(self):
        if self.worker:
            self.worker.stop()
        self.is_running = False


    def check_last_schedule(self):
        print(f"[schedule] recent schedule check")
        try:
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
        except Exception as e:
            print(f"[schedule] Error checking recent task: {e}")
            return True
