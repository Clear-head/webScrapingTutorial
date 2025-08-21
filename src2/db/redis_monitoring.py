from .server_connection import ServerConn

class MonitoringRedis:
    def __init__(self):
        self.conn = ServerConn()

    def _analyze_redis_data_types(self):
        cursor = self.conn.get_cursor()

        if cursor is None:
            print("[Monitor] Redis cursor is None. 분석 불가.")
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
            print(f"[Monitor] 총 키 개수: {len(keys)}")
        except Exception as e:
            print(f"[Monitor] 키 조회 실패: {e}")
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
                    print(f"[Monitor] 메모리 사용량 확인 실패 (키: {key}): {memory_error}")
                    continue

            except Exception as key_error:
                print(f"[Monitor] 키 분석 실패 (키: {key}): {key_error}")
                continue

        return stats

    def using_redis_info(self):
        """

            Redis 사용량 정보 출력

        """
        cursor = self.conn.get_cursor()
        cursor.memory_purge()

        if cursor is None:
            print("[Monitor] Redis cursor is None. 정보 조회 불가.")
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
            print(f"[Monitor] 메모리 정보 조회 실패: {e}")

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