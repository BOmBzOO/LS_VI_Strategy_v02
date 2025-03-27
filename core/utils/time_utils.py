"""시간 관련 유틸리티

시간 처리 및 변환을 위한 유틸리티 함수들을 제공합니다.
"""

from datetime import datetime, time, timedelta
from typing import Optional, Tuple
import pytz
from config.settings import TIMEZONE

def get_current_time() -> datetime:
    """현재 시간 반환 (설정된 타임존 기준)

    Returns:
        datetime: 현재 시간
    """
    return datetime.now(pytz.timezone(TIMEZONE))

def get_market_time() -> time:
    """현재 시장 시간 반환

    Returns:
        time: 현재 시장 시간
    """
    return get_current_time().time()

def is_market_open() -> bool:
    """시장 개장 여부 확인

    Returns:
        bool: 시장 개장 여부
    """
    current_time = get_market_time()
    market_start = time(9, 0)  # 09:00
    market_end = time(15, 30)  # 15:30
    
    return market_start <= current_time <= market_end

def get_market_phase() -> str:
    """현재 시장 단계 반환

    Returns:
        str: 시장 단계
            - "BEFORE_MARKET": 장 시작 전
            - "MARKET_OPEN": 장 중
            - "MARKET_CLOSE": 장 마감
    """
    current_time = get_market_time()
    market_start = time(9, 0)   # 09:00
    market_end = time(15, 30)   # 15:30
    
    if current_time < market_start:
        return "BEFORE_MARKET"
    elif current_time > market_end:
        return "MARKET_CLOSE"
    else:
        return "MARKET_OPEN"

def get_time_to_market_open() -> Optional[timedelta]:
    """시장 개장까지 남은 시간 반환

    Returns:
        Optional[timedelta]: 시장 개장까지 남은 시간 (이미 개장한 경우 None)
    """
    current_time = get_current_time()
    market_start = current_time.replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    
    if current_time < market_start:
        return market_start - current_time
    return None

def get_time_to_market_close() -> Optional[timedelta]:
    """시장 마감까지 남은 시간 반환

    Returns:
        Optional[timedelta]: 시장 마감까지 남은 시간 (이미 마감한 경우 None)
    """
    current_time = get_current_time()
    market_end = current_time.replace(
        hour=15, minute=30, second=0, microsecond=0
    )
    
    if current_time < market_end:
        return market_end - current_time
    return None

def format_time(dt: datetime) -> str:
    """시간을 문자열로 포맷팅

    Args:
        dt (datetime): 변환할 시간

    Returns:
        str: 포맷팅된 시간 문자열 (YYYY-MM-DD HH:MM:SS)
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_time(time_str: str) -> datetime:
    """시간 문자열을 datetime 객체로 파싱

    Args:
        time_str (str): 파싱할 시간 문자열 (YYYY-MM-DD HH:MM:SS)

    Returns:
        datetime: 파싱된 시간
    """
    return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")

def get_trading_period(dt: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """거래일의 시작과 끝 시간 반환

    Args:
        dt (Optional[datetime]): 기준 시간 (기본값: 현재 시간)

    Returns:
        Tuple[datetime, datetime]: (거래 시작 시간, 거래 종료 시간)
    """
    if dt is None:
        dt = get_current_time()
    
    start_time = dt.replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    end_time = dt.replace(
        hour=15, minute=30, second=0, microsecond=0
    )
    
    return start_time, end_time

def is_same_trading_day(dt1: datetime, dt2: datetime) -> bool:
    """두 시간이 같은 거래일인지 확인

    Args:
        dt1 (datetime): 첫 번째 시간
        dt2 (datetime): 두 번째 시간

    Returns:
        bool: 같은 거래일 여부
    """
    return dt1.date() == dt2.date()

def get_next_trading_day(dt: Optional[datetime] = None) -> datetime:
    """다음 거래일 반환

    Args:
        dt (Optional[datetime]): 기준 시간 (기본값: 현재 시간)

    Returns:
        datetime: 다음 거래일
    """
    if dt is None:
        dt = get_current_time()
    
    next_day = dt + timedelta(days=1)
    while next_day.weekday() in [5, 6]:  # 토요일(5)과 일요일(6) 제외
        next_day += timedelta(days=1)
    
    return next_day.replace(
        hour=9, minute=0, second=0, microsecond=0
    ) 