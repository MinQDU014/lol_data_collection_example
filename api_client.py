import requests
import time
from config import RIOT_API_KEY, URL_ASIA, URL_KR

def fetch_riot_api(url):
    """Riot API 공통 GET 요청 및 Rate Limit 자동 대기"""
    headers = {"X-Riot-Token": RIOT_API_KEY}
    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                print(f"⏳ [Rate Limit] {retry_after}초 대기 중... ({url[-30:]})")
                time.sleep(retry_after)
            elif response.status_code == 404:
                return None
            else:
                return None
        except Exception as e:
            time.sleep(3)

def get_puuid_by_riot_id(game_name, tag_line):
    url = f"{URL_ASIA}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    data = fetch_riot_api(url)
    return data['puuid'] if data and 'puuid' in data else None

def get_summoner_info(puuid):
    url = f"{URL_KR}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return fetch_riot_api(url)

def get_solo_rank_info(puuid):
    url = f"{URL_KR}/lol/league/v4/entries/by-puuid/{puuid}"
    data = fetch_riot_api(url)
    if data:
        for entry in data:
            if entry.get("queueType") == "RANKED_SOLO_5x5":
                return entry
    return None