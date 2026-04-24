import redis
import json
import requests
import time
import sys
from analyzer import SentimentAnalyzer
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

REDIS_CONF = {
    "host": os.getenv("REDIS_HOST"),
    "port": int(os.getenv("REDIS_PORT", 6379)),  # 숫자는 int형 변환 필요
    "password": os.getenv("REDIS_PASSWORD"),
    "decode_responses": os.getenv("REDIS_DECODE_RESPONSES", "True").lower() == "true",
    "socket_timeout": int(os.getenv("REDIS_SOCKET_TIMEOUT", 60)),
    "socket_connect_timeout": int(os.getenv("REDIS_CONNECT_TIMEOUT", 10)),
    "retry_on_timeout": os.getenv("REDIS_RETRY_ON_TIMEOUT", "True").lower() == "true"
}

DB_SERVER_URL = os.getenv("DB_SERVER_URL")

# 확인용 (배포 시에는 삭제하세요)
print(f"Redis Host: {REDIS_CONF['host']}")
print(f"DB URL: {DB_SERVER_URL}")

def process_stream():
    rd = redis.Redis(**REDIS_CONF)
    # --- 그룹 및 스트림 강제 생성 로직 추가 ---
    try:
        # mkstream=True 옵션이 스트림 키가 없으면 자동으로 만들어줍니다.
        rd.xgroup_create("news:batch_ready", "finbert-ingest-group", id="0", mkstream=True)
        print("[+] 소비자 그룹 'finbert-ingest-group' 생성 완료!")
    except redis.exceptions.ResponseError as e:
        if "already exists" in str(e):
            print("[*] 소비자 그룹이 이미 존재합니다.")
        else:
            print(f"[!] 그룹 생성 중 다른 에러 발생: {e}")
    # ------------------------------------------
    # 1. 모델 로딩 (시간이 좀 걸림)
    print("[*] FinBERT 모델 로딩 중... 잠시만 기다려 주세요.")
    analyzer = SentimentAnalyzer()
    print(f"[*] 모델 디바이스: {analyzer.device}")
    print("[+] 모델 로딩 완료!")

    print(f"[*] 분석 워커 가동! (Target: {DB_SERVER_URL})")

    while True:
        try:
            # 2. 데이터 수신 대기 로그
            # ID를 ">"로 하면 '새로운' 데이터만, "0"으로 하면 '처리 안 된(Pending)' 데이터부터 가져옵니다.
            # 우선 안전하게 ">"를 사용하되, block 시간을 줄여서 로그가 자주 찍히게 했습니다.
            streams = rd.xreadgroup("finbert-ingest-group", "finbert-worker-1", {"news:batch_ready": ">"}, count=1, block=5000)
            
            if not streams:
                print(f"[{time.strftime('%H:%M:%S')}] 대기 중... (Redis에 새로운 데이터가 없습니다)")
                continue

            for _, messages in streams:
                for message_id, payload in messages:
                    print(f"\n[>>>] 데이터 수신! (ID: {message_id})")
                    
                    batch_data = json.loads(payload['payload'])
                    items = batch_data.get('items', [])
                    item_count = len(items)
                    
                    print(f"[*] 총 {item_count}개의 뉴스 분석 시작...")
                    
                    start_time = time.time()
                    
                    # 3. 개별 아이템 분석 로그
                    for idx, item in enumerate(items, 1):
                        res = analyzer.analyze(item['title'])
                        item['sentiment'] = res
                        if idx % 5 == 0 or idx == item_count: # 5개마다 진행률 표시
                            print(f"    - 분석 진행 중... ({idx}/{item_count})")

                    end_time = time.time()
                    print(f"[+] 분석 완료! (소요시간: {end_time - start_time:.2f}초)")

                    # 4. DB 전송 로그
                    print(f"[*] DB 서버로 전송 중... ({DB_SERVER_URL})")
                    response = requests.post(DB_SERVER_URL, json=batch_data, timeout=15)
                    
                    if response.status_code == 200:
                        rd.xack("news:batch_ready", "writer-group", message_id)
                        print(f"[OK] 배치 {message_id} 최종 완료 및 ACK 전송")
                    else:
                        print(f"[ERR] DB 서버 전송 실패 (Status: {response.status_code})")

        except Exception as e:
            print(f"\n[!] 에러 발생: {e}")
            time.sleep(3)

if __name__ == "__main__":
    process_stream()