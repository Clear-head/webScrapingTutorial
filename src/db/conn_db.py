import redis
import pickle
from ..classes import ItemList, item_info



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
                print("[debug] Redis Connected!")
                return r
            else:
                raise redis.ConnectionError("Fail to Ping")
            
        except redis.ConnectionError as e:
            print(f"[debug] Redis connect failed, Connection Error: {e}")
            return None
        
        except Exception as e:
            print(f"[debug] Redis connect failed, error code: {e}")
            return None
        
    def insert_contents(self, item):
        print(f"================== Insert contents key: {item.key} ==================")
        if self._cursor is None:
            print("[debug] Redis cursor is None. 데이터 삽입 불가.")
            return False

        # 중복 체크
        if not self._check_duplicate_key(item.key):
            print(f"[debug] insert to redis")

            try:
                self._cursor.sadd("keys", item.key)
                print(f"[debug] insert key sucess")
            except Exception as e:
                print(f"[debug] insert key error : {e}")
            self._cursor.hset(item.key, mapping=item.to_dict())
            print("[debug] 적재 완료")

            return True
        else:
            print(f"[debug] 키가 이미 존재합니다.")
            return False

    def get_contents(self):
        print("================== Get contents ==================")
        if self._cursor is None:
            print("[debug] Redis cursor is None. 데이터 조회 불가.")
            return ItemList()

        keys = self._cursor.smembers("keys")
        items = ItemList()

        if len(keys) <= 0:
            print("[debug] can't find key")
            return items
        
        print(f"[debug] find key : count = {len(keys)}")
        
        pipe = self._cursor.pipeline()
        for k in keys:
            pipe.hgetall(k)

        results = pipe.execute()

        print(f"[debug] find contents : count = {len(results), type(results[0])}")

        for result in results:
            if result:
                item = {}
                for k, v in result.items():
                    k = k.decode("UTF-8")
                    v = v.decode("UTF-8")
                    item[k] = v
                
                items.add_item(
                    item_info(
                        img=item["img"],
                        title=item["title"],
                        organize=item['org'],
                        date=item["date"],
                        link=item["link"]
                    )
                )

        print(f"[debug] get contents complite : {len(items)}")
        return items

    def _check_duplicate_key(self, item_key):
        isin = self._cursor.sismember("keys", item_key)
        print(f"[debug] duplicate check : result = {True if isin else False}")
        return isin
    
    def close(self):
        self._cursor.close()