import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from pymongo import MongoClient  # 💡 [추가] MongoDB 연동을 위한 라이브러리

import db_client
import api_client
import mongodb_client
import player_service
from config import URL_ASIA


def map_position(pos):
    pos = (pos or "").upper()
    mapping = {"TOP": "TOP", "JUNGLE": "JUNGLE", "MIDDLE": "MID", "BOTTOM": "ADC", "UTILITY": "SUPPORT"}
    return mapping.get(pos, "UNKNOWN")


def collect_match_ids_fast(max_workers=10):
    """1단계: DB 유저 기반 Match ID 대기열 채우기"""
    conn = db_client.get_connection(autocommit=False)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT `puuid` FROM lol_player WHERE `puuid` IS NOT NULL")
            players = cursor.fetchall()
            if not players:
                print("DB에 플레이어 정보가 없습니다. 1번 메뉴를 먼저 실행하세요.")
                return

            print(f"\n🚀 총 {len(players)}명 유저의 Match ID 대기열 수집 시작 (스레드 {max_workers})")
            total_added = 0

            def fetch_ids(puuid):
                url = f"{URL_ASIA}/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&start=0&count=100"
                return {'puuid': puuid, 'ids': api_client.fetch_riot_api(url) or []}

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(fetch_ids, p['puuid']): p for p in players}
                for future in as_completed(futures):
                    res = future.result()
                    if not res['ids']: continue

                    sql = "INSERT IGNORE INTO lol_match_list (`match_id`, `puuid`) VALUES (%s, %s)"
                    cursor.executemany(sql, [(m, res['puuid']) for m in res['ids']])
                    conn.commit()

                    added = cursor.rowcount
                    total_added += added
                    print(f"✔️ {res['puuid'][:8]}... 게임 {added}개 대기열 추가")

            print(f"\n🎉 1단계 완료! 총 {total_added}개의 신규 대기열 확보.")
    finally:
        conn.close()


# 💡 [수정] 인자에 raw_collection(MongoDB 컬렉션 객체) 추가
def fetch_and_parse_match(match_id, player_cache, raw_collection):
    """[워커 스레드] 매치 파싱 및 DB에 없는 유저 동적 패치"""
    match_data = api_client.fetch_riot_api(f"{URL_ASIA}/lol/match/v5/matches/{match_id}")
    timeline_data = api_client.fetch_riot_api(f"{URL_ASIA}/lol/match/v5/matches/{match_id}/timeline")

    if not match_data or not timeline_data:
        return {'match_id': match_id, 'status': 2}

    # 💡 [MongoDB Data Lake 적재 핵심 로직]
    # 파싱 에러로 데이터가 날아가는 것을 방지하기 위해 무조건 원본부터 MongoDB에 백업합니다.
    try:
        raw_collection.update_one(
            {"_id": match_id},
            {"$set": {
                "match_data": match_data,
                "timeline_data": timeline_data,
                "collected_at": datetime.now()
            }},
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ [{match_id}] MongoDB 원본 백업 실패: {e}")
        # MongoDB 저장이 실패해도 MySQL 파싱 로직은 멈추지 않고 계속 진행하도록 예외 처리만 합니다.

    try:
        info = match_data['info']
        frames = timeline_data.get('info', {}).get('frames', [])
        minutes = info['gameDuration'] / 60.0 if info['gameDuration'] > 0 else 1.0

        team_kills = {100: 0, 200: 0}
        for p in info['participants']: team_kills[p['teamId']] += p['kills']

        obj_kills = {i: {'tower': 0, 'dragon': 0, 'baron': 0} for i in range(1, 11)}
        for frame in frames:
            for event in frame.get('events', []):
                k_id = event.get('killerId', 0)
                if 1 <= k_id <= 10:
                    e_type, m_type = event.get('type'), event.get('monsterType')
                    if e_type == 'BUILDING_KILL' and event.get('buildingType') == 'TOWER_BUILDING':
                        obj_kills[k_id]['tower'] += 1
                    elif e_type == 'ELITE_MONSTER_KILL':
                        if m_type == 'DRAGON':
                            obj_kills[k_id]['dragon'] += 1
                        elif m_type == 'BARON_NASHOR':
                            obj_kills[k_id]['baron'] += 1

        game_date = datetime.fromtimestamp(info['gameStartTimestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        game_tuple = (match_id, info['gameDuration'], info['gameVersion'], game_date)

        team_tuples = []
        for t in info['teams']:
            obj = t['objectives']
            team_tuples.append(
                (match_id, t['teamId'], 1 if t['win'] else 0, obj['tower']['kills'], obj['dragon']['kills'],
                 obj['baron']['kills'], obj['champion']['kills']))

        new_players = []
        participant_tuples = []

        for p in info['participants']:
            puuid = p['puuid']

            # [핵심 로직] 캐시에 유저가 없으면 즉석에서 API 호출하여 정보 획득!
            if puuid not in player_cache:
                summ_data = api_client.get_summoner_info(puuid)
                rank_data = api_client.get_solo_rank_info(puuid)

                new_p = {
                    'summoner_name': f"{p.get('riotIdGameName', '')}#{p.get('riotIdTagline', '')}",
                    'puuid': puuid,
                    'tier': rank_data.get('tier') if rank_data else None,
                    'rank': rank_data.get('rank') if rank_data else None,
                    'league_points': rank_data.get('leaguePoints') if rank_data else None,
                    'wins': rank_data.get('wins') if rank_data else None,
                    'losses': rank_data.get('losses') if rank_data else None,
                    'summoner_level': summ_data.get('summonerLevel') if summ_data else None,
                    'profile_icon': summ_data.get('profileIconId') if summ_data else None
                }
                new_players.append(new_p)
                # 현재 스레드 내의 캐시 업데이트 (다음 플레이어 처리 시 활용)
                player_cache[puuid] = {'tier': new_p['tier'], 'rank': new_p['rank']}

            s_tier = player_cache[puuid]['tier']
            s_rank = player_cache[puuid]['rank']

            k, d, a = p['kills'], p['deaths'], p['assists']
            participant_tuples.append((
                match_id, p['participantId'], p['teamId'], puuid,
                f"{p.get('riotIdGameName', '')}#{p.get('riotIdTagline', '')}",
                s_tier, s_rank, map_position(p.get('teamPosition')), p['championId'], 1 if p['win'] else 0,
                k, d, a, (k + a) / d if d > 0 else (k + a), p['champLevel'],
                p.get('totalMinionsKilled', 0) + p.get('neutralMinionsKilled', 0),
                p['goldEarned'], p['totalDamageDealtToChampions'], p['totalDamageTaken'],
                (p.get('totalMinionsKilled', 0) + p.get('neutralMinionsKilled', 0)) / minutes,
                ((k + a) / team_kills[p['teamId']]) if team_kills[p['teamId']] > 0 else 0,
                p.get('wardsPlaced', 0), p.get('detectorWardsPlaced', 0), p.get('wardsKilled', 0),
                obj_kills[p['participantId']]['tower'], obj_kills[p['participantId']]['dragon'],
                obj_kills[p['participantId']]['baron'],
                json.dumps([p['item0'], p['item1'], p['item2'], p['item3'], p['item4'], p['item5'], p['item6']]),
                json.dumps(p.get('perks', {}).get('styles', [])), json.dumps([p['summoner1Id'], p['summoner2Id']])
            ))

        timeline_tuples = []
        for minute, frame in enumerate(frames):
            for p_idx in range(1, 11):
                pf = frame['participantFrames'].get(str(p_idx))
                if not pf: continue
                pos = pf.get('position', {})
                timeline_tuples.append((
                    match_id, p_idx, minute, frame['timestamp'], pf.get('level', 1), pf.get('xp', 0),
                    pf.get('totalGold', 0), pf.get('currentGold', 0), pf.get('minionsKilled', 0),
                    pf.get('jungleMinionsKilled', 0),
                    json.dumps(pf.get('damageStats', {})), pos.get('x', None), pos.get('y', None)
                ))

        return {
            'match_id': match_id, 'status': 1, 'new_players': new_players,
            'game': game_tuple, 'teams': team_tuples,
            'participants': participant_tuples, 'timelines': timeline_tuples
        }
    except Exception as e:
        print(f"⚠️ [{match_id}] 파싱 에러 발생: {e}")
        return {'match_id': match_id, 'status': 2}


def process_matches_fast(limit=1000, max_workers=20):
    """대기열 매치 수집 및 DB 동적 적재"""

    # 💡 [추가] MongoDB 커넥션 세팅 (스레드들이 공유할 수 있도록 풀 바깥에서 한 번만 생성)
    raw_collection = mongodb_client.get_mongo_collection("lol_data_lake", "raw_match_data")
    conn = db_client.get_connection(autocommit=False)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT `puuid`, `tier`, `rank` FROM lol_player WHERE `puuid` IS NOT NULL")
            player_cache = {r['puuid']: {'tier': r['tier'], 'rank': r['rank']} for r in cursor.fetchall()}

            cursor.execute(f"SELECT `match_id` FROM lol_match_list WHERE `status` = 0 LIMIT {limit}")
            pending = cursor.fetchall()
            if not pending:
                print("수집 대기 중인 매치가 없습니다.")
                return

            match_ids = [r['match_id'] for r in pending]
            print(f"🚀 {len(match_ids)}개 매치 수집 시작 (스레드 {max_workers})")

            success, error = 0, 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 💡 [수정] fetch_and_parse_match 함수 호출 시 raw_collection 전달
                futures = {executor.submit(fetch_and_parse_match, m, player_cache, raw_collection): m for m in
                           match_ids}

                for future in as_completed(futures):
                    res = future.result()
                    m_id = res['match_id']

                    if res['status'] == 2:
                        cursor.execute("UPDATE lol_match_list SET `status` = 2 WHERE `match_id` = %s", (m_id,))
                        conn.commit()
                        error += 1
                        continue

                    try:
                        # [신규] 매치에서 새로 발견된 플레이어들을 lol_player 테이블에 선행 저장
                        for np in res.get('new_players', []):
                            player_service.insert_or_update_player_data(cursor, np)

                        cursor.execute(
                            "INSERT IGNORE INTO lol_game_data (`game_id`, `game_length`, `version`, `game_date`, `created_at`) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)",
                            res['game'])
                        cursor.executemany(
                            "INSERT IGNORE INTO lol_game_data_team (`game_id`, `team_id`, `is_won`, `tower_kill`, `dragon_kill`, `baron_kill`, `total_kill`) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            res['teams'])
                        cursor.executemany(
                            "INSERT IGNORE INTO lol_game_data_participant (`game_id`, `participant_id`, `team_id`, `puuid`, `summoner_name`, `summoner_tier`, `summoner_rank`, `position`, `champion_id`, `is_won`, `kill`, `death`, `assist`, `kda`, `level`, `total_cs`, `total_gold`, `total_damage_to_champions`, `total_damage_taken`, `cspm`, `kp`, `ward_placed`, `control_ward_placed`, `ward_kill`, `tower_kill`, `dragon_kill`, `baron_kill`, `items`, `perks`, `summoner_spell`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            res['participants'])
                        cursor.executemany(
                            "INSERT IGNORE INTO lol_game_data_timeline (`game_id`, `participant_id`, `minute`, `timestamp_ms`, `level`, `experience`, `total_gold`, `current_gold`, `minions_killed`, `jungle_minions_killed`, `damage_stats`, `position_x`, `position_y`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            res['timelines'])

                        cursor.execute("UPDATE lol_match_list SET `status` = 1 WHERE `match_id` = %s", (m_id,))
                        conn.commit()
                        success += 1
                        print(f"✔️ [{success}] 저장 완료 (신규 유저 {len(res.get('new_players', []))}명 추가): {m_id}")
                    except Exception as e:
                        conn.rollback()
                        print(f"❌ [{m_id}] 적재 에러: {e}")
                        cursor.execute("UPDATE lol_match_list SET `status` = 2 WHERE `match_id` = %s", (m_id,))
                        conn.commit()
                        error += 1

            print(f"\n🎉 완료! (성공: {success} / 에러: {error})")
    finally:
        conn.close()