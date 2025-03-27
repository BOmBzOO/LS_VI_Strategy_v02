"""실시간 체결 모니터링 서비스

실시간 체결 데이터 모니터링을 위한 서비스 클래스를 제공합니다.
"""

from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime
from config.logging_config import setup_logger
from api.realtime.ccld.ccld_handler import CCLDHandler
from core.utils.validation import validate_stock_code
from core.utils.time_utils import get_current_time

class CCLDMonitorService:
    """실시간 체결 모니터링 서비스 클래스"""

    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        
        # 체결 핸들러
        self.ccld_handler = CCLDHandler()
        
        # 모니터링 중인 종목
        self._monitoring_stocks: Set[str] = set()
        
        # 체결 콜백
        self._ccld_callbacks: Dict[str, List[Callable]] = {
            "TRADE": [],           # 체결
            "QUOTE": [],           # 호가
            "TICK": [],           # 틱
            "MARKET_STATUS": []    # 시장 상태
        }
        
        # 체결 핸들러 콜백 등록
        self.ccld_handler.add_callback("TRADE", self._handle_trade)
        self.ccld_handler.add_callback("QUOTE", self._handle_quote)
        self.ccld_handler.add_callback("TICK", self._handle_tick)
        self.ccld_handler.add_callback("MARKET_STATUS", self._handle_market_status)

    def start_monitoring(self, stock_code: str) -> bool:
        """종목 체결 모니터링 시작

        Args:
            stock_code (str): 종목 코드

        Returns:
            bool: 성공 여부
        """
        if not validate_stock_code(stock_code):
            self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
            return False
        
        if stock_code in self._monitoring_stocks:
            self.logger.warning(f"이미 모니터링 중인 종목: {stock_code}")
            return True
        
        try:
            # 체결 웹소켓 등록
            success = self.ccld_handler.subscribe(
                stock_code=stock_code,
                tr_type="3",  # 실시간 시세 등록
                tr_cd="S3_"   # 주식 체결
            )
            
            if success:
                self._monitoring_stocks.add(stock_code)
                self.logger.info(f"체결 모니터링 시작: {stock_code}")
                return True
            else:
                self.logger.error(f"체결 웹소켓 등록 실패: {stock_code}")
                return False
        except Exception as e:
            self.logger.error(f"체결 모니터링 시작 중 오류 발생: {str(e)}")
            return False

    def stop_monitoring(self, stock_code: str) -> bool:
        """종목 체결 모니터링 중지

        Args:
            stock_code (str): 종목 코드

        Returns:
            bool: 성공 여부
        """
        if not validate_stock_code(stock_code):
            self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
            return False
        
        if stock_code not in self._monitoring_stocks:
            self.logger.warning(f"모니터링 중이 아닌 종목: {stock_code}")
            return True
        
        try:
            # 체결 웹소켓 해제
            success = self.ccld_handler.unsubscribe(
                stock_code=stock_code,
                tr_type="4",  # 실시간 시세 해제
                tr_cd="S3_"   # 주식 체결
            )
            
            if success:
                self._monitoring_stocks.remove(stock_code)
                self.logger.info(f"체결 모니터링 중지: {stock_code}")
                return True
            else:
                self.logger.error(f"체결 웹소켓 해제 실패: {stock_code}")
                return False
        except Exception as e:
            self.logger.error(f"체결 모니터링 중지 중 오류 발생: {str(e)}")
            return False

    def add_ccld_callback(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """체결 이벤트 콜백 등록

        Args:
            event_type (str): 이벤트 타입 ("TRADE", "QUOTE", "TICK", "MARKET_STATUS")
            callback (Callable[[Dict[str, Any]], None]): 콜백 함수
        """
        if event_type not in self._ccld_callbacks:
            self.logger.error(f"유효하지 않은 이벤트 타입: {event_type}")
            return
        
        if callback not in self._ccld_callbacks[event_type]:
            self._ccld_callbacks[event_type].append(callback)
            self.logger.debug(f"체결 콜백 등록: {event_type}")

    def remove_ccld_callback(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """체결 이벤트 콜백 제거

        Args:
            event_type (str): 이벤트 타입 ("TRADE", "QUOTE", "TICK", "MARKET_STATUS")
            callback (Callable[[Dict[str, Any]], None]): 콜백 함수
        """
        if event_type not in self._ccld_callbacks:
            self.logger.error(f"유효하지 않은 이벤트 타입: {event_type}")
            return
        
        if callback in self._ccld_callbacks[event_type]:
            self._ccld_callbacks[event_type].remove(callback)
            self.logger.debug(f"체결 콜백 제거: {event_type}")

    def _handle_trade(self, data: Dict[str, Any]) -> None:
        """체결 데이터 처리"""
        stock_code = data.get("shcode", "")
        if not stock_code:
            return
        
        # 콜백 실행
        for callback in self._ccld_callbacks["TRADE"]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"체결 콜백 실행 중 오류 발생: {str(e)}")

    def _handle_quote(self, data: Dict[str, Any]) -> None:
        """호가 데이터 처리"""
        stock_code = data.get("shcode", "")
        if not stock_code:
            return
        
        # 콜백 실행
        for callback in self._ccld_callbacks["QUOTE"]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"호가 콜백 실행 중 오류 발생: {str(e)}")

    def _handle_tick(self, data: Dict[str, Any]) -> None:
        """틱 데이터 처리"""
        stock_code = data.get("shcode", "")
        if not stock_code:
            return
        
        # 콜백 실행
        for callback in self._ccld_callbacks["TICK"]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"틱 콜백 실행 중 오류 발생: {str(e)}")

    def _handle_market_status(self, data: Dict[str, Any]) -> None:
        """시장 상태 데이터 처리"""
        # 콜백 실행
        for callback in self._ccld_callbacks["MARKET_STATUS"]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"시장 상태 콜백 실행 중 오류 발생: {str(e)}")

    def get_monitoring_stocks(self) -> Set[str]:
        """모니터링 중인 종목 목록 조회

        Returns:
            Set[str]: 종목 코드 목록
        """
        return self._monitoring_stocks.copy()

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보 반환"""
        return {
            "monitoring_stocks": len(self._monitoring_stocks),
            "ccld_callbacks": {
                event_type: len(callbacks)
                for event_type, callbacks in self._ccld_callbacks.items()
            }
        } 