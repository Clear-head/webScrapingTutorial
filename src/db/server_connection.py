import redis

from . import user_connection
from ..classes import ItemList, Item_info
from datetime import datetime
from redis_connection import RedisConnection


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
                return True
            else:
                print(f"[Server] 키가 이미 존재합니다.")
                return False
        except RedisConnection as e:
            print(f"[Server] connect error: {e}")
            return False


    def _check_duplicate_key(self, item_key):
        cursor = self.get_cursor()
        isin = cursor.sismember("keys", item_key)
        print(f"[Server] duplicate check : result = {True if isin else False}")
        return isin


    def _analyze_redis_data_types(self):
        cursor = self.get_cursor()

        if cursor is None:
            print("[Server] Redis cursor is None. 분석 불가.")
            return {
                'string': 0, 'list': 0, 'set': 0, 'zset': 0,
                'hash': 0, 'stream': 0, 'total_keys': 0, 'total_memory': 0
            }

        stats = {
            'string': 0,
            'list': 0,
            'set': 0,
            'zset': 0,
            'hash': 0,
            'stream': 0,
            'total_keys': 0,
            'total_memory': 0
        }

        # 모든 키 가져오기
        try:
            keys = cursor.keys('*')
            stats['total_keys'] = len(keys)
            print(f"[debug] 총 키 개수: {len(keys)}")
        except Exception as e:
            print(f"[debug] 키 조회 실패: {e}")
            return stats

        for key in keys:
            try:
                key_type = cursor.type(key).decode()
                if key_type in stats:
                    stats[key_type] += 1
                try:
                    memory = cursor.memory_usage(key)
                    if memory:
                        stats['total_memory'] += memory
                except Exception as memory_error:
                    print(f"[debug] 메모리 사용량 확인 실패 (키: {key}): {memory_error}")
                    continue

            except Exception as key_error:
                print(f"[debug] 키 분석 실패 (키: {key}): {key_error}")
                continue

        return stats

    def using_redis_info(self):
        """

            Redis 사용량 정보 출력

        """
        cursor = self.get_cursor()
        cursor.memory_purge()

        if cursor is None:
            print("[debug] Redis cursor is None. 정보 조회 불가.")
            return

        print("================== Redis 사용량 분석 ==================")

        # 기본 메모리 정보
        try:
            memory_info = cursor.info('memory')
            print(f"||\t\t\t\t\t[Redis 메모리 정보]\t\t\t\t||")
            print(f"||\t\t\t\t\t전체 사용 메모리: {memory_info.get('used_memory_human', 'N/A')}\t\t\t||")
            print(f"||\t\t\t\t\tRSS 메모리: {memory_info.get('used_memory_rss_human', 'N/A')}\t\t\t\t||")
            print(f"||\t\t\t\t\t단편화 메모리: {memory_info.get("mem_fragmentation_ratio")}\t\t\t\t||")
            print("======================================================")
        except Exception as e:
            print(f"[debug] 메모리 정보 조회 실패: {e}")

        # 자료구조별 통계
        stats = self._analyze_redis_data_types()
        print("======================[자료구조별 통계]=====================")
        for data_type, count in stats.items():
            if data_type == 'set':
                print(f"||\t\t\t\t\t\t{data_type}: {cursor.scard("keys")} (+{count})개\t\t\t\t\t||")
            elif data_type != 'total_memory' and data_type != 'total_keys':
                print(f"||\t\t\t\t\t\t{data_type}: {count}개\t\t\t\t\t\t||")
            elif data_type == 'total_keys':
                print(f"||\t\t\t\t\t\t{data_type}: {count}개\t\t\t\t||")
            else:
                if count > 0:
                    print(f"||\t\t\t총 메모리 사용량: {count} bytes\t\t\t\t\t||")
                else:
                    print(f"||\t\t\t\t총 메모리 사용량: 확인 불가\t\t\t\t\t||")

        print("=" * 58)

    def del_over_day(self):
        print("="*100)
        print(f"[debug] delete start")
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
                print(f"[debug] delete 2000 year failed : {e}")
                continue

        print(f"[debug] delete complete 2000 year, {cnt} records")

        keys = cursor.smembers("keys")

        if len(keys) == 0:
            print("[debug] no keys")
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
                print(f"[debug] delete failed : {e}, key: {key}")
                continue
        print(f"[debug] delete complete , {cnt} records")
        try:
            cursor.memory_purge()
            print(f"[debug] memory purge complete")
        except Exception as e:
            print(f"[debug] memory purge failed : {e}")


        return None

    def get_schedule(self):
        cursor = self.get_cursor()
        if cursor is None:
            print("[debug] No cursor")


        tmp = ""
        try:
            tmp = cursor.get("schedule").decode('utf-8')
            if tmp == "":
                raise Exception("No schedule")
        except Exception as e:
            print(f"[debug] get schedule failed : {e}")

        print("[debug] get schedule complete")
        return tmp

    def set_schedule(self, schedule):
        cursor = self.get_cursor()
        if cursor is None:
            print("[debug] No cursor")

        try:
            cursor.set('schedule', schedule)
        except Exception as e:
            print(f"[debug] set schedule failed : {e}")
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