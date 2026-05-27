# config.py
import os
from dotenv import load_dotenv

# .env 파일 로드 (이 코드가 실행되면서 환경 변수가 세팅됩니다)
load_dotenv()

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
# os.environ.get("변수명") 으로 값을 가져옵니다.
RIOT_API_KEY = os.environ.get("RIOT_API_KEY")

URL_ASIA = "https://asia.api.riotgames.com"
URL_KR = "https://kr.api.riotgames.com"

DB_CONFIG = {
    'host': os.environ.get("DB_HOST", "localhost"),
    'user': os.environ.get("DB_USER", "root"),
    'password': os.environ.get("DB_PASSWORD", ""),
    'database': os.environ.get("DB_NAME", "lol"),
    'charset': os.environ.get("DB_CHARSET", "utf8mb4")
}