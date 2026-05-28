import json
import time
import redis
import db_client

# Redis 연결 설정 (도커로 띄운 기본 포트 6379)
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
except Exception as e:
    print(f"⚠️ Redis 연결 실패: {e}")
    redis_client = None


def get_champion_stats_with_cache():
    print("\n--- 📊 챔피언 KDA 랭킹 조회 (Redis 캐싱 실습) ---")
    if not redis_client:
        print("Redis가 실행되어 있지 않습니다.")
        return

    cache_key = "stats:champion_kda_top10"

    # [1단계] 무조건 Redis부터 찔러본다 (Cache Hit 검사)
    start_time = time.time()
    cached_data = redis_client.get(cache_key)

    if cached_data:
        # 🟢 [Cache Hit] 메모리에 데이터가 존재함! MySQL 안 가고 즉시 반환
        data = json.loads(cached_data)
        elapsed = time.time() - start_time
        print(f"⚡ [Cache HIT] Redis 메모리에서 즉시 가져왔습니다!")
        print(f"⏱️ 소요 시간: {elapsed:.4f}초 (거의 0초에 수렴)\n")

        for rank, row in enumerate(data, 1):
            print(f"{rank}위 | 챔피언ID: {row['champion_id']} | KDA: {row['avg_kda']:.2f} | 플레이 수: {row['play_count']}")
    else:
        # 🔴 [Cache Miss] 메모리에 데이터가 없음! MySQL에서 하드코어 연산 시작
        print("🐌 [Cache MISS] Redis에 데이터가 없습니다. MySQL에서 14만 건의 연산을 시작합니다...")
        conn = db_client.get_connection()
        try:
            with conn.cursor() as cursor:
                # 14만 명의 참여자 데이터를 그룹화하고 정렬하는 무거운 연산
                query = """
                SELECT champion_id, 
                       COUNT(*) as play_count, 
                       AVG(kda) as avg_kda
                FROM lol_game_data_participant
                WHERE kda IS NOT NULL
                GROUP BY champion_id
                HAVING play_count > 50
                ORDER BY avg_kda DESC
                LIMIT 10;
                """
                cursor.execute(query)
                result = cursor.fetchall()

                # Decimal 등 JSON 직렬화 불가 객체 변환
                for row in result:
                    row['avg_kda'] = float(row['avg_kda'])

                # [2단계] 힘들게 계산한 결과를 Redis에 60초(TTL) 동안 구워둔다!
                redis_client.setex(cache_key, 60, json.dumps(result))

                elapsed = time.time() - start_time
                print(f"💾 [DB 쿼리 완료] MySQL 디스크에서 계산하여 Redis에 저장했습니다.")
                print(f"⏱️ 소요 시간: {elapsed:.4f}초 (상대적으로 오래 걸림)\n")

                for rank, row in enumerate(result, 1):
                    print(
                        f"{rank}위 | 챔피언ID: {row['champion_id']} | KDA: {row['avg_kda']:.2f} | 플레이 수: {row['play_count']}")

                print("\n💡 팁: 지금 바로 5번 메뉴를 다시 실행해 보세요!")
        finally:
            conn.close()