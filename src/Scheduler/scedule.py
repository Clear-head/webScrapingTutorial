import datetime

from rq import Queue
from rq_scheduler import Scheduler


class SchedulerService:
    def __init__(self, conn):
        self.conn = conn
        self.queue = Queue(connection=self.conn)
        self.scheduler = Scheduler(connection=self.conn)


    def schedule_task(self, func):
        next_time = datetime.datetime.now() + datetime.timedelta(days=1)
        next_time = next_time.replace(hour=0, minute=1, second=0, microsecond=0)

        job = self.scheduler.schedule(
            scheduled_time=next_time,
            func=func,
            interval=86400
        )

        if self.check_last_schedule():
            next_time2 = datetime.datetime.now() + datetime.timedelta(minutes=5)

            job2 = self.scheduler.schedule(
                scheduled_time=next_time2,
                func=func,
                repeat=1
            )

    def start_task(self):
        pass

    def stop_task(self):
        pass


    def check_last_schedule(self):
        last_task = self.conn.get('schedule')
        datetime.datetime.strptime(last_task, '%Y-%m-%d')
        now = datetime.datetime.now()

        if now > datetime.datetime.strptime(last_task, '%Y-%m-%d') + datetime.timedelta(days=1):
            return True
        else:
            return False
