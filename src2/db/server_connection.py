from datetime import datetime
from .redis_connection import RedisConnection


class ServerConn(RedisConnection):
    _instance = None
    _cursor = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            super().__init__()
            self._cursor = self._connect_redis()
            self._initialized = True

    def insert_contents(self, item):
        print(f"================== Insert contents key: {item.key} ==================")
        cursor = self.get_cursor()

        try:
            # 중복 체크
            if not self._check_duplicate_key(item.key):
                print(f"[Server] insert to redis")

                try:
                    cursor.sadd("keys", item.key)
                    print(f"[Server] insert key success")
                except Exception as e:
                    print(f"[Server] insert key error : {e}")

                cursor.hset(item.key, mapping=item.to_dict())
                print("[Server] 적재 완료")
            else:
                print(f"[Server] 키가 이미 존재합니다.")
                return False
        except RedisConnection as e:
            print(f"[Server] connect error: {e}")
            return False

        cursor.set("last_scheduled", datetime.now().strftime("%Y-%m-%d"))
        return True

    def _check_duplicate_key(self, item_key):
        cursor = self.get_cursor()
        isin = cursor.sismember("keys", item_key[9:])
        print(f"[Server] duplicate check : result = {True if isin else False}")
        return isin




    def del_over_day(self):
        """

            마감 지난 공모전 삭제

        """
        print("="*100)
        print(f"[Server] delete start")
        cursor = self.get_cursor()

        if cursor is None:
            print("No cursor")
            return None

        cnt = 0

        for key in cursor.scan_iter(match="2000*"):

            try:
                cursor.delete(key)
                cursor.srem('keys', key)
                print(f"deleted: {key.decode('utf-8')}")
                cnt+=1
            except Exception as e:
                print(f"[Server] delete 2000 year failed : {e}")
                continue

        print(f"[Server] delete complete 2000 year, {cnt} records")

        keys = cursor.smembers("keys")

        if len(keys) == 0:
            print("[Server] no keys")
            return None

        cnt = 0
        for key in keys:
            try:
                key_decord = key
                if isinstance(key, bytes):
                    key_decord = key.decode('utf-8')
                key_pre = key_decord[:10]
                if datetime(int(key_pre[:4]), int(key_pre[5:7]), int(key_pre[8:10])) < datetime.now():
                    cursor.delete(key)
                    cursor.srem('keys', key)
                    print(f"deleted: {key.decode('utf-8')}")
                    cnt+=1
            except Exception as e:
                print(f"[Server] delete failed : {e}, key: {key}")
                continue
        print(f"[Server] delete complete , {cnt} records")
        try:
            cursor.memory_purge()
            print(f"[Server] memory purge complete")
        except Exception as e:
            print(f"[Server] memory purge failed : {e}")


        return None

    def get_schedule(self):
        cursor = self.get_cursor()
        tmp = ""
        try:
            tmp = cursor.get("schedule").decode('utf-8')
            if tmp == "":
                raise Exception("No schedule")
        except Exception as e:
            print(f"[Server] get schedule failed : {e}")

        print("[Server] get schedule complete")
        return tmp

    def set_schedule(self, schedule):
        cursor = self.get_cursor()
        try:
            cursor.set('schedule', schedule)
        except Exception as e:
            print(f"[Server] set schedule failed : {e}")
            return False
        return True



    # def get_contents(self):
    #     print("================== Get contents ==================")
    #     cursor = self.get_cursor()
    #
    #     if cursor is None:
    #         print("[Server] Redis cursor is None. 데이터 조회 불가.")
    #         return ItemList()
    #
    #     keys = cursor.smembers("keys")
    #     items = ItemList()
    #
    #     if len(keys) <= 0:
    #         print("[Server] can't find key")
    #         return items
    #
    #     print(f"[Server] find key : count = {len(keys)}")
    #
    #     pipe = cursor.pipeline()
    #     for k in keys:
    #         pipe.hgetall(k)
    #
    #     results = pipe.execute()
    #
    #     print(f"[Server] find contents : count = {len(results), type(results[0])}")
    #
    #     for result in results:
    #         if result:
    #             item = {}
    #             for k, v in result.items():
    #                 k = k.decode("UTF-8")
    #                 v = v.decode("UTF-8")
    #                 item[k] = v
    #             print(f"[Server] get item : {item.items()}")
    #             items.add_item(
    #                 Item_info(
    #                     img=item["img"],
    #                     title=item["title"],
    #                     organize=item['org'],
    #                     date=item["date"],
    #                     link=item["link"]
    #                 )
    #             )
    #
    #     print(f"[Server] get contents complete : {len(items)}")
    #     return items