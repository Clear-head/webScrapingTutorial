import redis
from .config import DbConfig

class RedisConnection:

    __config = None
    __HOST = None
    __PORT = None

    def __init__(self):
        self._cursor = None
        self.__config = DbConfig()
        self.__HOST, self.__PORT = self.__config.get_config()

    def _connect_redis(self):
        if self._cursor is None:
            try:
                r = redis.Redis(host=self.__HOST, port=self.__PORT)

                if r.ping():
                    print("[debug] Redis Connected!")
                    self._cursor = r
                else:
                    print(f"[User] Fail to Ping")
                    self._cursor = None

            except redis.ConnectionError as e:
                print(f"[debug] Redis connect failed, Connection Error: {e}")
                self._cursor = None

            except Exception as e:
                print(f"[debug] Redis connect failed, error code: {e}")
                self._cursor = None

    def get_cursor(self):

        if self._cursor is None:
            try:
                self._connect_redis()
            except Exception as e:
                print(f"[debug] Redis connect failed, Connection Error: {e}")
            finally:
                return self._cursor

        return self._cursor

    def close(self):
        if self._cursor:
            self._cursor.memory_purge()
            self._cursor.close()
            self._cursor = None
            print("[debug] Redis 연결 종료")

    def reconnect(self):
        self.close()
        self._connect_redis()
        print("[debug] Redis 재연결 완료")

    def check_scraping_status(self, **kwargs):


        if cursor is None:
            print("[debug] status check failed, no connection")
            return False