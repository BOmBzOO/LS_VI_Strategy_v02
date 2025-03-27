"""기본 설정

API URL, 타임존 등의 기본 설정을 제공합니다.
"""

import os
from dotenv import load_dotenv
from datetime import datetime, time, timezone, timedelta
import pytz

# 환경 변수 로드
load_dotenv()

# API 설정
LS_APP_KEY = os.getenv('LS_APP_KEY')
LS_SECRET_KEY = os.getenv('LS_SECRET_KEY')
LS_APP_ACCESS_TOKEN = os.getenv('LS_ACCESS_TOKEN')
LS_TOKEN_EXPIRES_AT = os.getenv('LS_TOKEN_EXPIRES_AT')

# API 엔드포인트
LS_BASE_URL = 'https://openapi.ls-sec.co.kr:8080'
LS_WS_URL = 'wss://openapi.ls-sec.co.kr:9443/websocket'

# MAC 주소 설정
LS_MAC_ADDRESS = os.getenv('LS_MAC_ADDRESS', '00-00-00-00-00-00')

# 시간대 설정
TIMEZONE = 'Asia/Seoul'
KST = timezone(timedelta(hours=9))

# 장 시간 설정
MARKET_START_TIME = time(9, 0)    # 장 시작 시간 (9:00)
MARKET_END_TIME = time(15, 30)    # 장 종료 시간 (15:30)

# 토큰 관련 설정
TOKEN_URL = f"{LS_BASE_URL}/oauth2/token"
TOKEN_REFRESH_MARGIN = 300  # 토큰 갱신 여유 시간 (초)

# 웹소켓 설정
WS_RECONNECT_INTERVAL = int(os.getenv("WS_RECONNECT_INTERVAL", "5"))
WS_MAX_RECONNECT_ATTEMPTS = 5  # 최대 재연결 시도 횟수
WS_DEBUG_MODE = False  # 웹소켓 디버그 모드 (기본값: False)

# VI 모니터링 설정
VI_MONITORING_INTERVAL = 180  # VI 모니터링 시간 (초)
VI_UNSUBSCRIBE_DELAY = 180   # VI 해제 후 구독 취소까지 대기 시간 (초)

# 로깅 설정
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/trading.log')

# 시간 설정
KST = timezone(timedelta(hours=9))
MARKET_START_TIME = time(9, 0)  # 장 시작 시간 (9:00)
MARKET_END_TIME = time(15, 30)  # 장 종료 시간 (15:30)

# 재시도 설정
MAX_RETRIES = 3
RETRY_INTERVAL = 1.0

# 캐시 설정
CACHE_EXPIRY = 60  # 캐시 만료 시간 (초)
MAX_CACHE_SIZE = 1000  # 최대 캐시 크기

# 주문 설정
ORDER_TIMEOUT = 10  # 주문 타임아웃 (초)
MAX_PENDING_ORDERS = 10  # 최대 미체결 주문 수

# VI 설정
VI_MIN_VOLUME_RATE = 2.0  # 최소 거래량 배율
VI_MIN_PRICE_CHANGE_RATE = 0.03  # 최소 가격 변동률
VI_MAX_PRICE_CHANGE_RATE = 0.10  # 최대 가격 변동률
VI_TREND_WINDOW = 20  # 추세 분석 기간

# 시간대 설정
TIMEZONE = 'Asia/Seoul'

# 기타 설정들... 