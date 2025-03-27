"""데이터 검증 유틸리티

데이터 검증을 위한 유틸리티 함수들을 제공합니다.
"""

from typing import Any, Dict, List, Optional, Union
from decimal import Decimal
from datetime import datetime
from config.logging_config import setup_logger

logger = setup_logger(__name__)

def validate_stock_code(stock_code: str) -> bool:
    """주식 종목 코드 유효성 검사

    Args:
        stock_code (str): 종목 코드

    Returns:
        bool: 유효성 여부
    """
    if not stock_code:
        return False
    
    # 6자리 숫자 확인
    if not (len(stock_code) == 6 and stock_code.isdigit()):
        return False
    
    return True

def validate_order_quantity(quantity: Union[int, float, str]) -> bool:
    """주문 수량 유효성 검사

    Args:
        quantity (Union[int, float, str]): 주문 수량

    Returns:
        bool: 유효성 여부
    """
    try:
        qty = int(quantity)
        return qty > 0
    except (ValueError, TypeError):
        return False

def validate_order_price(price: Union[int, float, str, Decimal]) -> bool:
    """주문 가격 유효성 검사

    Args:
        price (Union[int, float, str, Decimal]): 주문 가격

    Returns:
        bool: 유효성 여부
    """
    try:
        price_decimal = Decimal(str(price))
        return price_decimal > 0
    except (ValueError, TypeError, decimal.InvalidOperation):
        return False

def validate_order_type(order_type: str) -> bool:
    """주문 유형 유효성 검사

    Args:
        order_type (str): 주문 유형

    Returns:
        bool: 유효성 여부
    """
    valid_types = ["MARKET", "LIMIT"]
    return order_type in valid_types

def validate_order_side(order_side: str) -> bool:
    """매수/매도 구분 유효성 검사

    Args:
        order_side (str): 매수/매도 구분

    Returns:
        bool: 유효성 여부
    """
    valid_sides = ["BUY", "SELL"]
    return order_side in valid_sides

def validate_order_params(params: Dict[str, Any]) -> List[str]:
    """주문 파라미터 유효성 검사

    Args:
        params (Dict[str, Any]): 주문 파라미터

    Returns:
        List[str]: 오류 메시지 목록
    """
    errors = []
    
    # 필수 파라미터 확인
    required_params = ["stock_code", "quantity", "order_type", "order_side"]
    for param in required_params:
        if param not in params:
            errors.append(f"필수 파라미터가 없습니다: {param}")
    
    # 각 파라미터 유효성 검사
    if "stock_code" in params and not validate_stock_code(params["stock_code"]):
        errors.append("유효하지 않은 종목 코드입니다.")
    
    if "quantity" in params and not validate_order_quantity(params["quantity"]):
        errors.append("유효하지 않은 주문 수량입니다.")
    
    if "price" in params and not validate_order_price(params["price"]):
        errors.append("유효하지 않은 주문 가격입니다.")
    
    if "order_type" in params and not validate_order_type(params["order_type"]):
        errors.append("유효하지 않은 주문 유형입니다.")
    
    if "order_side" in params and not validate_order_side(params["order_side"]):
        errors.append("유효하지 않은 매수/매도 구분입니다.")
    
    return errors

def validate_account_number(account_number: str) -> bool:
    """계좌번호 유효성 검사

    Args:
        account_number (str): 계좌번호

    Returns:
        bool: 유효성 여부
    """
    if not account_number:
        return False
    
    # 10자리 숫자 확인
    if not (len(account_number) == 10 and account_number.isdigit()):
        return False
    
    return True

def validate_date_format(date_str: str, format: str = "%Y-%m-%d") -> bool:
    """날짜 형식 유효성 검사

    Args:
        date_str (str): 날짜 문자열
        format (str): 날짜 형식 (기본값: %Y-%m-%d)

    Returns:
        bool: 유효성 여부
    """
    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False

def validate_time_format(time_str: str, format: str = "%H:%M:%S") -> bool:
    """시간 형식 유효성 검사

    Args:
        time_str (str): 시간 문자열
        format (str): 시간 형식 (기본값: %H:%M:%S)

    Returns:
        bool: 유효성 여부
    """
    try:
        datetime.strptime(time_str, format)
        return True
    except ValueError:
        return False

def validate_decimal_places(value: Union[float, Decimal], max_places: int) -> bool:
    """소수점 자릿수 유효성 검사

    Args:
        value (Union[float, Decimal]): 검사할 값
        max_places (int): 최대 소수점 자릿수

    Returns:
        bool: 유효성 여부
    """
    try:
        decimal_str = str(Decimal(str(value)))
        if '.' in decimal_str:
            places = len(decimal_str.split('.')[1])
            return places <= max_places
        return True
    except (ValueError, decimal.InvalidOperation):
        return False 