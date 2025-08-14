import redis
from ..classes import ItemList, Item_info


class Conn:
    _instance = None
    _cursor = None
    HOST = "192.168.40.131"
    PORT = 6379

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        if cls._cursor is None:
            cls._cursor = cls.__connect_redis()
        return cls._instance

    # def __init__(self):
    #     if self._cursor is None:
    #         self._cursor = self.__connect_redis()

    @classmethod
    def __connect_redis(cls):
        try:
            r = redis.Redis(host=cls.HOST, port=cls.PORT)

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
                print(f"[debug] insert key success")

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
                # print(f"[debug] get item : {item.items()}")
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
        isin = self._cursor.sismember("keys", item_key)
        print(f"[debug] duplicate check : result = {True if isin else False}")
        return isin


    def _analyze_redis_data_types(self):
        """Redis 자료구조별 사용량 분석"""
        if self._cursor is None:
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
            keys = self._cursor.keys('*')
            stats['total_keys'] = len(keys)
            print(f"[debug] 총 키 개수: {len(keys)}")
        except Exception as e:
            print(f"[debug] 키 조회 실패: {e}")
            return stats

        for key in keys:
            try:
                # 키 타입 확인
                key_type = self._cursor.type(key).decode()
                if key_type in stats:
                    stats[key_type] += 1

                # 메모리 사용량 확인 (Redis 4.0+)
                try:
                    memory = self._cursor.memory_usage(key)
                    if memory:
                        stats['total_memory'] += memory
                except Exception as memory_error:
                    # Redis 버전이 낮거나 MEMORY USAGE를 지원하지 않는 경우
                    print(f"[debug] 메모리 사용량 확인 실패 (키: {key}): {memory_error}")
                    continue

            except Exception as key_error:
                print(f"[debug] 키 분석 실패 (키: {key}): {key_error}")
                continue

        return stats

    def using_redis_info(self):
        """Redis 사용량 정보 출력"""
        if self._cursor is None:
            print("[debug] Redis cursor is None. 정보 조회 불가.")
            return

        print("================== Redis 사용량 분석 ==================")

        # 기본 메모리 정보
        try:
            memory_info = self._cursor.info('memory')
            print(f"||\t\t\t\t\t[Redis 메모리 정보]\t\t\t\t||")
            print(f"||\t\t\t\t전체 사용 메모리: {memory_info.get('used_memory_human', 'N/A')}\t\t\t\t||")
            print(f"||\t\t\t\tRSS 메모리: {memory_info.get('used_memory_rss_human', 'N/A')}\t\t\t\t\t||")
            print("======================================================")
        except Exception as e:
            print(f"[debug] 메모리 정보 조회 실패: {e}")

        # 자료구조별 통계
        stats = self._analyze_redis_data_types()
        print("======================[자료구조별 통계]=====================")
        for data_type, count in stats.items():
            if data_type != 'total_memory' and data_type != 'total_keys':
                print(f"||\t\t\t\t\t\t{data_type}: {count}개\t\t\t\t\t\t||")
            elif data_type == 'total_keys':
                print(f"||\t\t\t\t\t\t{data_type}: {count}개\t\t\t\t||")
            else:
                if count > 0:
                    print(f"||\t\t\t총 메모리 사용량: {count} bytes\t\t\t\t\t||")
                else:
                    print(f"||\t\t\t\t총 메모리 사용량: 확인 불가\t\t\t\t\t||")

        print("=" * 58)

    def close(self):
        """Redis 연결 종료"""
        if self._cursor:
            self._cursor.close()
            print("[debug] Redis 연결 종료")