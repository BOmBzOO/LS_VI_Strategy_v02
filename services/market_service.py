"""시장 데이터 서비스

시장 데이터 처리 및 관리를 위한 서비스 클래스를 제공합니다.
"""

from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime
from config.logging_config import setup_logger
from data.market_data import MarketData
from data.stock_info import StockInfo
from core.utils.validation import validate_stock_code
from core.utils.time_utils import get_current_time, is_market_open
from api.constants import MarketType

class MarketService:
    """시장 데이터 서비스 클래스"""

    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.market_data = MarketData()
        self.stock_info = StockInfo()

    def get_market_index(self, market_type: str) -> Dict[str, Any]:
        """시장 지수 정보 조회

        Args:
            market_type (str): 시장 구분

        Returns:
            Dict[str, Any]: 시장 지수 정보
        """
        return self.market_data.get_market_index(market_type)

    def get_market_stocks(self, market_type: MarketType) -> Dict[str, Any]:
        """시장 종목 리스트 조회

        Args:
            market_type (MarketType): 시장 구분 (MarketType.ALL: 전체, MarketType.KOSPI: 코스피, MarketType.KOSDAQ: 코스닥)

        Returns:
            Dict[str, Any]: 종목 리스트 응답
                - t8430OutBlock (List[Dict[str, Any]]): 종목 정보 리스트
                    - hname (str): 종목명
                    - shcode (str): 단축코드
                    - expcode (str): 확장코드
                    - etfgubun (str): ETF구분(1:ETF)
                    - uplmtprice (str): 상한가
                    - dnlmtprice (str): 하한가
                    - jnilclose (str): 전일가
                    - memedan (str): 주문수량단위
                    - recprice (str): 기준가
                    - gubun (str): 구분(1:코스피2:코스닥)
        """
        return self.market_data.get_market_stocks(market_type)

    def get_stock_price(self, stock_code: str) -> Dict[str, Any]:
        """종목 현재가 조회

        Args:
            stock_code (str): 종목 코드

        Returns:
            Dict[str, Any]: 현재가 정보
        """
        if not validate_stock_code(stock_code):
            self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
            return {}
        return self.stock_info.get_price_info(stock_code)

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보 반환"""
        return {
            "market_data_cache": self.market_data.get_cache_status(),
            "stock_info_cache": self.stock_info.get_cache_status()
        } 