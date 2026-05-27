import pymysql
from config import DB_CONFIG

def get_connection(autocommit=False):
    """안전한 DB 커넥션을 반환합니다."""
    return pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset=DB_CONFIG['charset'],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=autocommit
    )