import redis
from ..classes import ItemList, Item_info
from datetime import datetime
from .config import db_config

class Conn:
    _instance = None
    _cursor = None
    __config = None
    __HOST = None
    __PORT = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            cls.__config = db_config()
            cls.__HOST, cls.__PORT = cls.__config.get_config()

            cls._connect_redis()  # 첫 생성 시에만 연결
        return cls._instance

    def __init__(self):
        pass

    @classmethod
    def _connect_redis(cls):
        if cls._cursor is None:
            try:
                r = redis.Redis(host=cls.__HOST, port=cls.__PORT)

                if r.ping():
                    print("[debug] Redis Connected!")
                    cls._cursor = r
                else:
                    raise redis.ConnectionError("[debug] Fail to Ping")

            except redis.ConnectionError as e:
                print(f"[debug] Redis connect failed, Connection Error: {e}")
                cls._cursor = None

            except Exception as e:
                print(f"[debug] Redis connect failed, error code: {e}")
                cls._cursor = None

    @classmethod
    def get_cursor(cls):

        if cls._cursor is None:
            try:
                cls._connect_redis()
            except Exception as e:
                print(f"[debug] Redis connect failed, Connection Error: {e}")
            finally:
                return cls._cursor
        return cls._cursor

    def insert_contents(self, item):
        print(f"================== Insert contents key: {item.key} ==================")
        cursor = self.get_cursor()

        if cursor is None:
            print("[debug] Redis cursor is None. 데이터 삽입 불가.")
            return False

        # 중복 체크
        if not self._check_duplicate_key(item.key):
            print(f"[debug] insert to redis")

            try:
                cursor.sadd("keys", item.key)
                print(f"[debug] insert key success")
            except Exception as e:
                print(f"[debug] insert key error : {e}")

            cursor.hset(item.key, mapping=item.to_dict())
            print("[debug] 적재 완료")
            return True
        else:
            print(f"[debug] 키가 이미 존재합니다.")
            return False

    def get_contents(self):
        print("================== Get contents ==================")
        cursor = self.get_cursor()

        if cursor is None:
            print("[debug] Redis cursor is None. 데이터 조회 불가.")
            return ItemList()

        keys = cursor.smembers("keys")
        items = ItemList()

        if len(keys) <= 0:
            print("[debug] can't find key")
            return items

        print(f"[debug] find key : count = {len(keys)}")

        pipe = cursor.pipeline()
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
                print(f"[debug] get item : {item.items()}")
                items.add_item(
                    Item_info(
                        img=item["img"],
                        title=item["title"],
                        organize=item['org'],
                        date=item["date"],
                        link=item["link"]
                    )
                )

        print(f"[debug] get contents complete : {len(items)}")
        return items

    def _check_duplicate_key(self, item_key):
        cursor = self.get_cursor()
        if cursor is None:
            return False

        isin = cursor.sismember("keys", item_key)
        print(f"[debug] duplicate check : result = {True if isin else False}")
        return isin

    @classmethod
    def _analyze_redis_data_types(cls):
        cursor = cls.get_cursor()

        if cursor is None:
            print("[debug] Redis cursor is None. 분석 불가.")
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
                # 키 타입 확인
                key_type = cursor.type(key).decode()
                if key_type in stats:
                    stats[key_type] += 1

                # 메모리 사용량 확인 (Redis 4.0+)
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

    @classmethod
    def using_redis_info(cls):
        """Redis 사용량 정보 출력"""
        cursor = cls.get_cursor()
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
        stats = cls._analyze_redis_data_types()
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

    @classmethod
    def del_over_day(cls):
        print("="*100)
        print(f"[debug] delete start")
        cursor = cls.get_cursor()

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


    @classmethod
    def close(cls):
        if cls._cursor:
            cls._cursor.memory_purge()
            cls._cursor.close()
            cls._cursor = None
            print("[debug] Redis 연결 종료")

    @classmethod
    def reconnect(cls):
        cls.close()
        cls._connect_redis()
        print("[debug] Redis 재연결 완료")


    @classmethod
    def get_schedule(cls):
        cursor = cls.get_cursor()
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

    @classmethod
    def set_schedule(cls, schedule):
        cursor = cls.get_cursor()
        if cursor is None:
            print("[debug] No cursor")

        try:
            cursor.set('schedule', schedule)
        except Exception as e:
            print(f"[debug] set schedule failed : {e}")
            return False
        return True
