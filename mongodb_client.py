# 파일명: mongodb_client.py
from pymongo import MongoClient
from config import MONGO_CONFIG

def get_mongo_collection(db_name, collection_name):
    uri = MONGO_CONFIG['host'],
    try:
        mongo_client = MongoClient(uri)
        mongo_db = mongo_client[db_name]
        return mongo_db[collection_name]
    except Exception as e:
        print(f"⚠️ MongoDB 연결 실패: {e}")
        return None
