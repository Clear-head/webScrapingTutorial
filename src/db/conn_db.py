import redis
import pickle
from ..classes import ItemList



class conn:
    _instance = None
    _cursor = None
    HOST = "192.168.40.131"
    PORT = 6379

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            instance = super().__new__(cls)
            cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._cursor is None:
            self._cursor = self.__connect_redis()

    def __connect_redis(self):
        try:
            r = redis.Redis(host=self.HOST, port=self.PORT)

            if r.ping():
                print("Redis Connected!")
                return r
            else:
                raise redis.ConnectionError("Fail to Ping")
            
        except redis.ConnectionError as e:
            print(f"Redis connect failed, Connection Error: {e}")
            return None
        
        except Exception as e:
            print(f"Redis connect failed, error code: {e}")
            return None
        
    def insert_contents(self, item):
        if self._cursor is None:
            print("Redis cursor is None. 데이터 삽입 불가.")
            return False

        # 중복 체크
        if not self._check_duplicate_key(item.key):
            self._cursor.sadd("keys", item.key)
            obj = pickle.dumps(item.to_dict())
            self._cursor.hset(item.key, obj)

            return True
        else:
            print(f"키 '{item.key}'는 이미 존재합니다.")
            return False

    def get_contents(self):
        if self._cursor is None:
            print("Redis cursor is None. 데이터 조회 불가.")
            return ItemList()

        keys = self._cursor.smembers("keys")
        items = ItemList()

        if len(keys) <= 0:
            return items
        
        pipe = self._cursor.pipeline()
        for key in keys:
            pipe.get(key)

        results = pipe.execute()

        for result in results:
            if result:
                try:
                    items.add_item(pickle.loads(result))
                except (pickle.UnpicklingError, EOFError) as e:
                    print(f"데이터 역직렬화 실패: {e}")
                    continue
        return items

    def _check_duplicate_key(self, item_key):
        return self._cursor.sismember("keys", item_key)
    
    def close(self):
        self._cursor.close()