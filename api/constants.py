"""API 관련 상수 정의"""

from enum import Enum, auto

class OrderType:
    """주문 유형"""
    BUY = "02"
    SELL = "01"

class MessageType:
    """메시지 타입"""
    # 주문 관련
    ORDER = "SC0"  # 주문 접수
    EXECUTION = "SC1"  # 체결
    EXECUTION_MODIFY = "SC2"  # 체결 정정
    CANCEL = "SC3"  # 주문 취소
    REJECT = "SC4"  # 주문 거부
    
    # 실시간 시세 관련
    SUBSCRIBE = "3"    # 실시간 시세 등록
    UNSUBSCRIBE = "4"  # 실시간 시세 해제

class OrderCode:
    """주문 코드"""
    NEW = ["SONAT000", "SONAT003"]  # 신규주문 접수
    MODIFY = ["SONAT001"]  # 정정주문 접수
    CANCEL = ["SONAT002"]  # 취소주문 접수
    EXEC = ["SONAS100"]  # 체결확인

class OrderStatus:
    """주문 상태"""
    ORDER = "01"  # 주문
    MODIFY = "02"  # 정정
    CANCEL = "03"  # 취소
    EXECUTION = "11"  # 체결
    MODIFY_CONFIRM = "12"  # 정정확인
    CANCEL_CONFIRM = "13"  # 취소확인
    REJECT = "14"  # 거부

class OrderTypeCode:
    """주문 유형 코드"""
    CASH_SELL = "01"  # 현금매도
    CASH_BUY = "02"  # 현금매수
    CREDIT_SELL = "03"  # 신용매도
    CREDIT_BUY = "04"  # 신용매수
    SAVING_SELL = "05"  # 저축매도
    SAVING_BUY = "06"  # 저축매수
    PRODUCT_SELL_MARGIN = "07"  # 상품매도(대차)
    PRODUCT_SELL = "09"  # 상품매도
    PRODUCT_BUY = "10"  # 상품매수

class MarketCode:
    """시장 코드"""
    UNLISTED = "00"  # 비상장
    KOSPI = "10"  # 코스피
    BOND = "11"  # 채권
    OTC = "19"  # 장외시장
    KOSDAQ = "20"  # 코스닥
    KONEX = "23"  # 코넥스
    FREEBORD = "30"  # 프리보드

class CreditType:
    """신용 거래 코드"""
    NORMAL = "000"  # 보통
    CIRCULATION_MARGIN_NEW = "001"  # 유통융자신규
    SELF_MARGIN_NEW = "003"  # 자기융자신규
    CIRCULATION_LOAN_NEW = "005"  # 유통대주신규
    SELF_LOAN_NEW = "007"  # 자기대주신규
    CIRCULATION_MARGIN_REPAY = "101"  # 유통융자상환
    SELF_MARGIN_REPAY = "103"  # 자기융자상환
    CIRCULATION_LOAN_REPAY = "105"  # 유통대주상환
    SELF_LOAN_REPAY = "107"  # 자기대주상환

class TRCode:
    """TR 코드"""
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
    """API URL 경로"""
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

# 상태 매핑
STATUS_MAP = {
    OrderStatus.ORDER: "주문",
    OrderStatus.MODIFY: "정정",
    OrderStatus.CANCEL: "취소",
    OrderStatus.EXECUTION: "체결",
    OrderStatus.MODIFY_CONFIRM: "정정확인",
    OrderStatus.CANCEL_CONFIRM: "취소확인",
    OrderStatus.REJECT: "거부"
}

# 주문 유형 매핑
ORDER_TYPE_MAP = {
    OrderTypeCode.CASH_SELL: "현금매도",
    OrderTypeCode.CASH_BUY: "현금매수",
    OrderTypeCode.CREDIT_SELL: "신용매도",
    OrderTypeCode.CREDIT_BUY: "신용매수",
    OrderTypeCode.SAVING_SELL: "저축매도",
    OrderTypeCode.SAVING_BUY: "저축매수",
    OrderTypeCode.PRODUCT_SELL_MARGIN: "상품매도(대차)",
    OrderTypeCode.PRODUCT_SELL: "상품매도",
    OrderTypeCode.PRODUCT_BUY: "상품매수"
}

# 시장 코드 매핑
MARKET_MAP = {
    MarketCode.UNLISTED: "비상장",
    MarketCode.KOSPI: "코스피",
    MarketCode.BOND: "채권",
    MarketCode.OTC: "장외시장",
    MarketCode.KOSDAQ: "코스닥",
    MarketCode.KONEX: "코넥스",
    MarketCode.FREEBORD: "프리보드"
}

# 신용 구분 매핑
CREDIT_MAP = {
    CreditType.NORMAL: "보통",
    CreditType.CIRCULATION_MARGIN_NEW: "유통융자",
    CreditType.SELF_MARGIN_NEW: "자기융자",
    CreditType.CIRCULATION_LOAN_NEW: "유통대주",
    CreditType.SELF_LOAN_NEW: "자기대주",
    CreditType.CIRCULATION_MARGIN_REPAY: "유통융자상환",
    CreditType.SELF_MARGIN_REPAY: "자기융자상환",
    CreditType.CIRCULATION_LOAN_REPAY: "유통대주상환",
    CreditType.SELF_LOAN_REPAY: "자기대주상환"
} 