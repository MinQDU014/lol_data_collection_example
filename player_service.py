from concurrent.futures import ThreadPoolExecutor, as_completed
import db_client
import api_client

def process_player_api(player):
    """[워커 스레드] 1명의 유저 데이터를 종합 조회"""
    game_name, tag_line = player['gameName'], player['tagLine']
    full_name = f"{game_name}#{tag_line}"

    puuid = api_client.get_puuid_by_riot_id(game_name, tag_line)
    if not puuid: return None

    summoner_data = api_client.get_summoner_info(puuid)
    rank_data = api_client.get_solo_rank_info(puuid)

    return {
        'summoner_name': full_name,
        'puuid': puuid,
        'tier': rank_data.get('tier') if rank_data else None,
        'rank': rank_data.get('rank') if rank_data else None,
        'league_points': rank_data.get('leaguePoints') if rank_data else None,
        'wins': rank_data.get('wins') if rank_data else None,
        'losses': rank_data.get('losses') if rank_data else None,
        'summoner_level': summoner_data.get('summonerLevel') if summoner_data else None,
        'profile_icon': summoner_data.get('profileIconId') if summoner_data else None
    }

def insert_or_update_player_data(cursor, player_info):
    """DB에 플레이어 정보 INSERT 또는 UPDATE"""
    sql = """
        INSERT INTO lol_player (
            `summoner_name`, `puuid`, `tier`, `rank`, `league_points`, 
            `wins`, `losses`, `summoner_level`, `profile_icon`
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            `summoner_name` = VALUES(`summoner_name`),
            `tier` = VALUES(`tier`),
            `rank` = VALUES(`rank`),
            `league_points` = VALUES(`league_points`),
            `wins` = VALUES(`wins`),
            `losses` = VALUES(`losses`),
            `summoner_level` = VALUES(`summoner_level`),
            `profile_icon` = VALUES(`profile_icon`)
    """
    values = (
        player_info['summoner_name'], player_info['puuid'], player_info['tier'],
        player_info['rank'], player_info['league_points'], player_info['wins'],
        player_info['losses'], player_info['summoner_level'], player_info['profile_icon']
    )
    cursor.execute(sql, values)

def run_initial_player_load(file_path="challenger_player.txt"):
    """텍스트 파일에서 플레이어를 읽어 DB에 저장 (초기화용)"""
    players = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "#" in line:
                    g_name, t_line = line.split("#", 1)
                    players.append({"gameName": g_name, "tagLine": t_line})
    except FileNotFoundError:
        print(f"[에러] {file_path} 파일을 찾을 수 없습니다.")
        return

    print(f"\n🚀 총 {len(players)}명의 초기 플레이어 데이터 수집 시작...")
    valid_results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_player_api, p): p for p in players}
        for future in as_completed(futures):
            res = future.result()
            if res:
                print(f"✔️ 플레이어 확인: {res['summoner_name']}")
                valid_results.append(res)

    conn = db_client.get_connection(autocommit=False)
    try:
        with conn.cursor() as cursor:
            for info in valid_results:
                insert_or_update_player_data(cursor, info)
            conn.commit()
            print(f"🎉 {len(valid_results)}명의 플레이어 DB 저장 완료!")
    except Exception as e:
        print(f"❌ DB 에러: {e}")
        conn.rollback()
    finally:
        conn.close()