from ..classes import ItemList, ItemInfo
from .redis_connection import  RedisConnection


class UserConn(RedisConnection):
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


    
    def get_contents(self):
        print("================== Get contents ==================")
        cursor = self.get_cursor()

        try:
            keys = cursor.smembers("keys")
            items = ItemList()

            if len(keys) <= 0:
                print("[User] can't find key")
                return items

            print(f"[User] find key : count = {len(keys)}")

            pipe = cursor.pipeline()
            for k in keys:
                pipe.hgetall(k)

            results = pipe.execute()

            print(f"[User] find contents : count = {len(results), type(results[0])}")

            for result in results:
                if result:
                    item = {}
                    for k, v in result.items():
                        k = k.decode("UTF-8")
                        v = v.decode("UTF-8")
                        item[k] = v
                    # print(f"[User] get item : {item.items()}")
                    items.add_item(
                        ItemInfo(
                            img=item["img"],
                            title=item["title"],
                            organize=item['org'],
                            date=item["date"],
                            link=item["link"]
                        )
                    )

            print(f"[User] get contents complete : {len(items)}")
        except Exception as e:
            print(f"[User] get contents failed : {e}")
            return ItemList()

        return items
