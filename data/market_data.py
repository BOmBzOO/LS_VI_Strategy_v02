"""시장 데이터 처리

시장 데이터를 관리하고 처리하는 클래스를 제공합니다.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from config.logging_config import setup_logger
from api.tr.tr_market import MarketTRAPI
from api.tr.tr_stock import StockTRAPI
from api.constants import MarketType
from core.utils.time_utils import get_current_time, format_time

class MarketData:
    """시장 데이터 관리 클래스"""

    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.market_api = MarketTRAPI()
        self.stock_api = StockTRAPI()
        
        # 시장 데이터 캐시
        self._market_indices: Dict[str, Dict[str, Any]] = {}  # 시장 지수
        self._market_sectors: Dict[str, Dict[str, Any]] = {}  # 섹터 정보
        self._market_stocks: Dict[str, Dict[str, Any]] = {}        # 시장별 종목 리스트
        self._last_update: Dict[str, datetime] = {}           # 마지막 업데이트 시간

    def get_market_index(self, market_type: str, use_cache: bool = True) -> Dict[str, Any]:
        """시장 지수 정보 조회

        Args:
            market_type (str): 시장 구분
            use_cache (bool): 캐시 사용 여부

        Returns:
            Dict[str, Any]: 시장 지수 정보
        """
        cache_key = f"index_{market_type}"
        
        if use_cache and cache_key in self._market_indices:
            last_update = self._last_update.get(cache_key)
            if last_update and (get_current_time() - last_update).seconds < 60:  # 1분 이내
                return self._market_indices[cache_key]
        
        try:
            index_info = self.market_api.get_market_index(market_type)
            self._market_indices[cache_key] = index_info
            self._last_update[cache_key] = get_current_time()
            return index_info
        except Exception as e:
            self.logger.error(f"시장 지수 조회 중 오류 발생: {str(e)}")
            return {}

    def get_market_sectors(self, market_type: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """시장 섹터 정보 조회

        Args:
            market_type (str): 시장 구분
            use_cache (bool): 캐시 사용 여부

        Returns:
            List[Dict[str, Any]]: 섹터 정보 목록
        """
        cache_key = f"sectors_{market_type}"
        
        if use_cache and cache_key in self._market_sectors:
            last_update = self._last_update.get(cache_key)
            if last_update and (get_current_time() - last_update).seconds < 300:  # 5분 이내
                return self._market_sectors[cache_key]
        
        try:
            sector_info = self.market_api.get_market_sectors(market_type)
            self._market_sectors[cache_key] = sector_info
            self._last_update[cache_key] = get_current_time()
            return sector_info
        except Exception as e:
            self.logger.error(f"섹터 정보 조회 중 오류 발생: {str(e)}")
            return []

    def get_market_stocks(self, market_type: MarketType, use_cache: bool = True) -> Dict[str, Any]:
        """시장 종목 리스트 조회

        Args:
            market_type (MarketType): 시장 구분 (MarketType.ALL: 전체, MarketType.KOSPI: 코스피, MarketType.KOSDAQ: 코스닥)
            use_cache (bool): 캐시 사용 여부

        Returns:
            Dict[str, Any]: 종목 리스트 응답
                - rsp_cd (str): 응답 코드 (00000: 정상)
                - rsp_msg (str): 응답 메시지
                - t8430OutBlock (List[Dict[str, Any]]): 종목 정보 리스트
                    - hname (str): 종목명
                    - shcode (str): 단축코드
                    - expcode (str): 확장코드
                    - etfgubun (str): ETF구분(1:ETF)
                    - uplmtprice (int): 상한가
                    - dnlmtprice (int): 하한가
                    - jnilclose (int): 전일가
                    - memedan (str): 주문수량단위
                    - recprice (int): 기준가
                    - gubun (str): 구분(1:코스피2:코스닥)
        """
        cache_key = f"stocks_{market_type.value}"
        
        if use_cache and cache_key in self._market_stocks:
            last_update = self._last_update.get(cache_key)
            if last_update and (get_current_time() - last_update).seconds < 3600:  # 1시간 이내
                return self._market_stocks[cache_key]
        
        try:
            response = self.market_api.get_market_stocks(market_type)
            if response.get("rsp_cd") != "00000":
                self.logger.error(f"종목 리스트 조회 실패: {response.get('rsp_msg')}")
                return {
                    "rsp_cd": response.get("rsp_cd", "99999"),
                    "rsp_msg": response.get("rsp_msg", "조회 실패"),
                    "t8430OutBlock": []
                }
                
            self._market_stocks[cache_key] = response
            self._last_update[cache_key] = get_current_time()
            return response
            
        except Exception as e:
            self.logger.error(f"종목 리스트 조회 중 오류 발생: {str(e)}")
            return {
                "rsp_cd": "99999",
                "rsp_msg": str(e),
                "t8430OutBlock": []
            }

    def get_stock_price(self, stock_code: str) -> Dict[str, Any]:
        """종목 현재가 조회

        Args:
            stock_code (str): 종목 코드

        Returns:
            Dict[str, Any]: 현재가 정보
        """
        try:
            return self.stock_api.get_stock_price(stock_code)
        except Exception as e:
            self.logger.error(f"현재가 조회 중 오류 발생: {str(e)}")
            return {}

    def get_stock_orderbook(self, stock_code: str) -> Dict[str, Any]:
        """종목 호가 정보 조회

        Args:
            stock_code (str): 종목 코드

        Returns:
            Dict[str, Any]: 호가 정보
        """
        try:
            return self.stock_api.get_stock_orderbook(stock_code)
        except Exception as e:
            self.logger.error(f"호가 정보 조회 중 오류 발생: {str(e)}")
            return {}

    def get_stock_chart(self, stock_code: str, interval: str = "1D", count: int = 100) -> List[Dict[str, Any]]:
        """종목 차트 데이터 조회

        Args:
            stock_code (str): 종목 코드
            interval (str): 차트 간격 (1D: 일봉, 1W: 주봉, 1M: 월봉)
            count (int): 조회 개수

        Returns:
            List[Dict[str, Any]]: 차트 데이터
        """
        try:
            return self.stock_api.get_stock_chart(stock_code, interval, count)
        except Exception as e:
            self.logger.error(f"차트 데이터 조회 중 오류 발생: {str(e)}")
            return []

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """캐시 데이터 초기화

        Args:
            cache_type (Optional[str]): 초기화할 캐시 타입 (None인 경우 전체 초기화)
        """
        if cache_type == "indices":
            self._market_indices = {}
        elif cache_type == "sectors":
            self._market_sectors = {}
        elif cache_type == "stocks":
            self._market_stocks = {}
        else:
            self._market_indices = {}
            self._market_sectors = {}
            self._market_stocks = {}
        
        self._last_update = {}
        self.logger.debug(f"캐시 초기화 완료: {cache_type if cache_type else '전체'}")

    def get_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 정보 반환"""
        return {
            "indices": {
                "count": len(self._market_indices),
                "last_update": {k: format_time(v) for k, v in self._last_update.items() if k.startswith("index_")}
            },
            "sectors": {
                "count": len(self._market_sectors),
                "last_update": {k: format_time(v) for k, v in self._last_update.items() if k.startswith("sectors_")}
            },
            "stocks": {
                "count": len(self._market_stocks),
                "last_update": {k: format_time(v) for k, v in self._last_update.items() if k.startswith("stocks_")}
            }
        } 