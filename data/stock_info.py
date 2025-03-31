"""종목 정보 관리

종목 정보를 관리하고 처리하는 클래스를 제공합니다.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from config.logging_config import setup_logger
from api.tr.tr_stock import StockTRAPI
from core.utils.time_utils import get_current_time, format_time
from core.utils.validation import validate_stock_code

class StockInfo:
    """종목 정보 관리 클래스"""

    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.stock_api = StockTRAPI()
        
        # 종목 정보 캐시
        self._stock_info: Dict[str, Dict[str, Any]] = {}     # 종목 기본 정보
        self._price_info: Dict[str, Dict[str, Any]] = {}     # 현재가 정보
        self._vi_info: Dict[str, Dict[str, Any]] = {}        # VI 발동 정보
        self._last_update: Dict[str, datetime] = {}          # 마지막 업데이트 시간
        
        # VI 관련 정보
        self._vi_activated_stocks: Set[str] = set()          # VI 발동 종목
        self._vi_released_stocks: Set[str] = set()           # VI 해제 종목

    def get_stock_info(self, stock_code: str, use_cache: bool = True) -> Dict[str, Any]:
        """종목 기본 정보 조회

        Args:
            stock_code (str): 종목 코드
            use_cache (bool): 캐시 사용 여부

        Returns:
            Dict[str, Any]: 종목 기본 정보
        """
        if not validate_stock_code(stock_code):
            self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
            return {}
        
        cache_key = f"info_{stock_code}"
        
        if use_cache and cache_key in self._stock_info:
            last_update = self._last_update.get(cache_key)
            if last_update and (get_current_time() - last_update).seconds < 3600:  # 1시간 이내
                return self._stock_info[cache_key]
        
        try:
            stock_info = self.stock_api.get_stock_info(stock_code)
            self._stock_info[cache_key] = stock_info
            self._last_update[cache_key] = get_current_time()
            return stock_info
        except Exception as e:
            self.logger.error(f"종목 정보 조회 중 오류 발생: {str(e)}")
            return {}

    def get_price_info(self, stock_code: str, use_cache: bool = True) -> Dict[str, Any]:
        """종목 현재가 정보 조회

        Args:
            stock_code (str): 종목 코드
            use_cache (bool): 캐시 사용 여부

        Returns:
            Dict[str, Any]: 현재가 정보
        """
        if not validate_stock_code(stock_code):
            self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
            return {}
        
        cache_key = f"price_{stock_code}"
        
        if use_cache and cache_key in self._price_info:
            last_update = self._last_update.get(cache_key)
            if last_update and (get_current_time() - last_update).seconds < 1:  # 1초 이내
                return self._price_info[cache_key]
        
        try:
            price_info = self.stock_api.get_stock_price(stock_code)
            self._price_info[cache_key] = price_info
            self._last_update[cache_key] = get_current_time()
            return price_info
        except Exception as e:
            self.logger.error(f"현재가 정보 조회 중 오류 발생: {str(e)}")
            return {}

    def update_vi_info(self, stock_code: str, vi_status: bool, vi_time: Optional[datetime] = None) -> None:
        """VI 정보 업데이트

        Args:
            stock_code (str): 종목 코드
            vi_status (bool): VI 발동 여부
            vi_time (Optional[datetime]): VI 발동/해제 시간
        """
        if not validate_stock_code(stock_code):
            self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
            return
        
        if vi_time is None:
            vi_time = get_current_time()
        
        vi_info = {
            "status": vi_status,
            "time": vi_time,
            "updated_at": get_current_time()
        }
        
        self._vi_info[stock_code] = vi_info
        
        if vi_status:
            self._vi_activated_stocks.add(stock_code)
            if stock_code in self._vi_released_stocks:
                self._vi_released_stocks.remove(stock_code)
        else:
            self._vi_released_stocks.add(stock_code)
            if stock_code in self._vi_activated_stocks:
                self._vi_activated_stocks.remove(stock_code)
        
        self.logger.debug(f"VI 정보 업데이트: {stock_code} ({'발동' if vi_status else '해제'})")

    def get_vi_info(self, stock_code: str) -> Dict[str, Any]:
        """VI 정보 조회

        Args:
            stock_code (str): 종목 코드

        Returns:
            Dict[str, Any]: VI 정보
        """
        if not validate_stock_code(stock_code):
            self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
            return {}
        
        return self._vi_info.get(stock_code, {})

    def get_vi_activated_stocks(self) -> Set[str]:
        """VI 발동 종목 목록 조회

        Returns:
            Set[str]: VI 발동 종목 코드 목록
        """
        return self._vi_activated_stocks.copy()

    def get_vi_released_stocks(self) -> Set[str]:
        """VI 해제 종목 목록 조회

        Returns:
            Set[str]: VI 해제 종목 코드 목록
        """
        return self._vi_released_stocks.copy()

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """캐시 데이터 초기화

        Args:
            cache_type (Optional[str]): 초기화할 캐시 타입 (None인 경우 전체 초기화)
        """
        if cache_type == "info":
            self._stock_info = {}
        elif cache_type == "price":
            self._price_info = {}
        elif cache_type == "vi":
            self._vi_info = {}
            self._vi_activated_stocks.clear()
            self._vi_released_stocks.clear()
        else:
            self._stock_info = {}
            self._price_info = {}
            self._vi_info = {}
            self._vi_activated_stocks.clear()
            self._vi_released_stocks.clear()
        
        self._last_update = {}
        self.logger.debug(f"캐시 초기화 완료: {cache_type if cache_type else '전체'}")

    def get_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 정보 반환"""
        return {
            "info": {
                "count": len(self._stock_info),
                "last_update": {k: format_time(v) for k, v in self._last_update.items() if k.startswith("info_")}
            },
            "price": {
                "count": len(self._price_info),
                "last_update": {k: format_time(v) for k, v in self._last_update.items() if k.startswith("price_")}
            },
            "vi": {
                "activated_count": len(self._vi_activated_stocks),
                "released_count": len(self._vi_released_stocks),
                "total_count": len(self._vi_info)
            }
        } 