"""API 관련 상수 정의"""

from enum import Enum, auto

class TRCode:
    """TR 코드 상수"""
    # 종목 정보
    STOCK_LIST = "t8430"    # 종목 정보 조회
    STOCK_PRICE = "t1102"   # 현재가 조회
    STOCK_HISTORY = "t1305" # 일별 주가 조회
    
    # VI 관련
    VI_OCCUR = "VI_"       # VI 발동/해제
    
    # 주문 관련
    ORDER_NEW = "CSPAT00601"    # 주식 주문
    ORDER_CANCEL = "CSPAT00801" # 주문 취소

    # 시장 정보
    MARKET_INDEX = "t1511"      # 업종 현재가
    MARKET_SECTORS = "t8424"    # 업종 전체 조회
    MARKET_TRADING_INFO = "t1601"  # 투자자별 매매동향

    # 주식 정보
    STOCK_ORDERBOOK = "t1105"   # 주식 호가 조회
    STOCK_CHART = "t8410"       # 주식 차트 조회
    STOCK_LIST = "t8430"  # 종목 정보 조회
    STOCK_MINUTE_CHART = "t8412"  # N분봉 차트 조회
    STOCK_TICK_CHART = "t8411"  # N틱 차트 조회
    
    # 계좌 관련
    ACCOUNT_BALANCE = "t0424"   # 계좌 잔고
    ACCOUNT_HISTORY = "CDPCQ04700"   # 계좌 잔고
    ACCOUNT_DEPOSIT = "t0424"      # 예수금 상세 조회

class MarketType(str, Enum):
    """시장 구분 코드"""
    ALL = "0"      # 전체
    KOSPI = "1"    # 코스피
    KOSDAQ = "2"   # 코스닥
    
    # 실시간 시세 코드
    KOSPI_REAL = "S3_"  # 코스피 실시간
    KOSDAQ_REAL = "K3_" # 코스닥 실시간

class URLPath:
    """API URL 경로 상수"""
    STOCK_LIST = "/stock/etc"
    STOCK_ETC = "/stock/etc"
    STOCK_PRICE = "/stock/price"
    STOCK_ORDER = "/stock/order"
    STOCK_CHART = "/stock/chart"
    ACCOUNT_INFO = "/stock/accno"
    
    # TR 코드별 URL 매핑
    TR_URLS = {
        TRCode.STOCK_LIST: STOCK_ETC,        # 종목 정보 조회
        TRCode.STOCK_PRICE: STOCK_PRICE,     # 현재가 조회
        TRCode.ORDER_NEW: STOCK_ORDER,       # 주식 주문
        TRCode.ORDER_CANCEL: STOCK_ORDER,    # 주문 취소
        TRCode.MARKET_INDEX: STOCK_PRICE,    # 업종 현재가
        TRCode.MARKET_SECTORS: STOCK_ETC,    # 업종 전체 조회
        TRCode.MARKET_TRADING_INFO: STOCK_PRICE,  # 투자자별 매매동향
        TRCode.STOCK_ORDERBOOK: STOCK_PRICE, # 주식 호가 조회
        TRCode.STOCK_CHART: STOCK_CHART,     # 주식 차트 조회
        TRCode.STOCK_MINUTE_CHART: STOCK_CHART,  # N분봉 차트 조회
        TRCode.STOCK_TICK_CHART: STOCK_CHART,    # N틱 차트 조회
        TRCode.ACCOUNT_BALANCE: ACCOUNT_INFO,  # 신용거래동향
        TRCode.ACCOUNT_HISTORY: ACCOUNT_INFO    # 신용거래동향
    }

class MessageType:
    """메시지 타입"""
    SUBSCRIBE = "3"    # 실시간 시세 등록
    UNSUBSCRIBE = "4"  # 실시간 시세 해제

class VIStatus:
    """VI 상태 코드"""
    RELEASE = "0"     # 해제
    STATIC = "1"      # 정적 발동
    DYNAMIC = "2"     # 동적 발동
    BOTH = "3"        # 정적&동적 발동
    
    STATUS_MAP = {
        RELEASE: "해제",
        STATIC: "정적발동",
        DYNAMIC: "동적발동",
        BOTH: "정적&동적"
    } 