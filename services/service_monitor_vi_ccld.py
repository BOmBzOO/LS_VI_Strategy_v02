"""VI 발동 종목 체결 모니터링 통합 서비스

VI 발동 종목을 실시간으로 모니터링하고, 해당 종목들의 체결 정보를 구독하는 서비스를 제공합니다.
"""

from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime
import asyncio
from config.logging_config import setup_logger
from services.service_monitor_vi import VIMonitorService, VIData
from services.service_monitor_ccld import CCLDMonitorService, CCLDData
from services.service_market_data import MarketService
from api.constants import MarketType
from api.realtime.websocket.websocket_base import WebSocketConfig
from api.realtime.websocket.websocket_manager import WebSocketManager
from config.settings import LS_WS_URL
import json

class VICCLDMonitorService:
    """VI 발동 종목 체결 모니터링 통합 서비스 클래스"""
    
    def __init__(self, token: str):
        """초기화
        
        Args:
            token (str): 인증 토큰
        """
        self.logger = setup_logger(__name__)
        self.token = token
        self.vi_monitor = VIMonitorService(token)
        self.market_service = MarketService()
        self.ccld_monitors: Dict[str, CCLDMonitorService] = {}  # 종목코드: 체결모니터 매핑
        self._market_stocks: Dict[str, str] = {}  # 종목코드: 시장구분 매핑
        self.vi_callbacks: List[Callable[[Dict[str, Any]], None]] = []  # VI 이벤트 콜백
        self.ccld_callbacks: List[Callable[[Dict[str, Any]], None]] = []  # 체결 이벤트 콜백
        
        # 공유 웹소켓 매니저
        self.ws_config: WebSocketConfig = {
            "url": LS_WS_URL,
            "token": token,
            "max_subscriptions": 100,
            "max_reconnect_attempts": 5,
            "reconnect_delay": 5,
            "ping_interval": 30,
            "ping_timeout": 10,
            "connect_timeout": 30
        }
        self.shared_ws_manager: Optional[WebSocketManager] = None

    def add_vi_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """VI 이벤트 콜백 함수 등록
        
        Args:
            callback (Callable[[Dict[str, Any]], None]): VI 이벤트 처리 콜백 함수
        """
        if callback not in self.vi_callbacks:
            self.vi_callbacks.append(callback)
            
    def remove_vi_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """VI 이벤트 콜백 함수 제거
        
        Args:
            callback (Callable[[Dict[str, Any]], None]): 제거할 VI 이벤트 콜백 함수
        """
        if callback in self.vi_callbacks:
            self.vi_callbacks.remove(callback)
            
    def add_ccld_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """체결 이벤트 콜백 함수 등록
        
        Args:
            callback (Callable[[Dict[str, Any]], None]): 체결 이벤트 처리 콜백 함수
        """
        if callback not in self.ccld_callbacks:
            self.ccld_callbacks.append(callback)
            
    def remove_ccld_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """체결 이벤트 콜백 함수 제거
        
        Args:
            callback (Callable[[Dict[str, Any]], None]): 제거할 체결 이벤트 콜백 함수
        """
        if callback in self.ccld_callbacks:
            self.ccld_callbacks.remove(callback)

    def _initialize_market_stocks(self) -> None:
        """시장 종목 정보 초기화"""
        try:
            # 코스피 종목 정보 조회
            kospi_stocks = self.market_service.get_market_stocks(MarketType.KOSPI)
            for stock in kospi_stocks.get("t8430OutBlock", []):
                self._market_stocks[stock["shcode"]] = MarketType.KOSPI
                
            # 코스닥 종목 정보 조회
            kosdaq_stocks = self.market_service.get_market_stocks(MarketType.KOSDAQ)
            for stock in kosdaq_stocks.get("t8430OutBlock", []):
                self._market_stocks[stock["shcode"]] = MarketType.KOSDAQ
                
            self.logger.info(f"시장 종목 정보 초기화 완료 (총 {len(self._market_stocks)}개 종목)")
            
        except Exception as e:
            self.logger.error(f"시장 종목 정보 초기화 중 오류: {str(e)}")
            raise
        
    async def start(self) -> None:
        """모니터링 시작"""
        try:
            # 시장 종목 정보 초기화
            self._initialize_market_stocks()
            
            # 공유 웹소켓 매니저 초기화
            if not self.shared_ws_manager:
                self.shared_ws_manager = WebSocketManager(self.ws_config)
                await self.shared_ws_manager.start()
            
            # VI 모니터링 시작
            await self.vi_monitor.start()
            
            # VI 발동/해제 콜백 등록
            self.vi_monitor.add_callback(self._handle_vi_event)
            
            self.logger.info("VI 발동 종목 체결 모니터링이 시작되었습니다.")
            
        except Exception as e:
            self.logger.error(f"VI 발동 종목 체결 모니터링 시작 중 오류 발생: {str(e)}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """모니터링 중지"""
        try:
            # 모든 체결 모니터링 중지
            for monitor in self.ccld_monitors.values():
                try:
                    await monitor.stop()
                except Exception as e:
                    self.logger.warning(f"체결 모니터링 중지 중 오류: {str(e)}")
            self.ccld_monitors.clear()
            
            # VI 모니터링 중지
            await self.vi_monitor.stop()
            
            # 공유 웹소켓 매니저 중지
            if self.shared_ws_manager:
                await self.shared_ws_manager.stop()
                self.shared_ws_manager = None
            
            self.logger.info("VI 발동 종목 체결 모니터링이 중지되었습니다.")
            
        except Exception as e:
            self.logger.error(f"VI 발동 종목 체결 모니터링 중지 중 오류: {str(e)}")
            raise
              
    async def _handle_vi_event(self, message: Dict[str, Any]) -> None:
        """VI 이벤트 처리"""
        try:
            self.logger.debug(f"VI 이벤트 처리: {message}")
            # VI 콜백이 있는 경우 전체 메시지를 전달
            if self.vi_callbacks:
                for callback in self.vi_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)
                    except Exception as e:
                        self.logger.error(f"VI 콜백 함수 실행 중 오류: {str(e)}")
                return
                
            # 콜백이 없는 경우 메시지 출력
            self.logger.info(f"VI 메시지 수신: {json.dumps(message, ensure_ascii=False)}")

            body = message.get("body", {})
            if not body:
                return
                
            vi_data = VIData(body)
            stock_code = vi_data.ref_shcode
            
            if vi_data.vi_type in ["정적발동", "동적발동", "정적&동적"]:  # VI 발동
                if stock_code not in self.ccld_monitors:
                    # 시장 구분 확인
                    market_type = self._market_stocks.get(stock_code)
                    if not market_type:
                        self.logger.warning(f"알 수 없는 종목코드: {stock_code}")
                        return

                    # 공유 웹소켓 매니저를 사용하여 모니터 생성
                    monitor = CCLDMonitorService(self.token, stock_code, market_type)
                    monitor.ws_manager = self.shared_ws_manager  # 웹소켓 매니저 공유
                    monitor.add_callback(self._handle_ccld_event)
                    await monitor.start()
                    self.ccld_monitors[stock_code] = monitor
                    self.logger.info(f"VI 발동 종목 체결 모니터링 시작: {stock_code} (시장: {market_type}, VI유형: {vi_data.vi_type})")
                    
            else:  # VI 해제
                if stock_code in self.ccld_monitors:
                    # 해당 종목의 체결 모니터링 중지
                    monitor = self.ccld_monitors.pop(stock_code)
                    await asyncio.sleep(1*60)  # 1분 대기
                    await monitor.stop()
                    self.logger.info(f"VI 발동 종목 체결 모니터링 중지: {stock_code}")
                    
        except Exception as e:
            self.logger.error(f"VI 이벤트 처리 중 오류: {str(e)}")
            
    async def _handle_ccld_event(self, message: Dict[str, Any]) -> None:
        """체결 이벤트 처리"""
        try:
            self.logger.debug(f"체결 이벤트 처리: {message}")
            # 체결 콜백이 있는 경우 전체 메시지를 전달
            if self.ccld_callbacks:
                for callback in self.ccld_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)
                    except Exception as e:
                        self.logger.error(f"체결 콜백 함수 실행 중 오류: {str(e)}")
                return

            # 콜백이 없는 경우 메시지 출력
            self.logger.info(f"체결 메시지 수신: {json.dumps(message, ensure_ascii=False)}")

            body = message.get("body", {})
            if not body:
                return
                
            ccld_data = CCLDData(body)
            stock_code = ccld_data.shcode
            
            # VI 발동 종목의 체결 데이터 처리
            if stock_code in self.ccld_monitors:
                self.logger.info(
                    f"VI 발동 종목 체결: {stock_code}, "
                    f"현재가: {ccld_data.price} ({ccld_data.sign}{ccld_data.change}, {ccld_data.drate}%), "
                    f"체결량: {ccld_data.cvolume}, "
                    f"체결강도: {ccld_data.cpower}%"
                )
                
        except Exception as e:
            self.logger.error(f"체결 이벤트 처리 중 오류: {str(e)}")
            
    def get_monitoring_stocks(self) -> List[str]:
        """현재 모니터링 중인 종목 코드 목록 반환"""
        return list(self.ccld_monitors.keys())
        
    def get_stock_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """특정 종목의 현재 체결 데이터 반환"""
        if stock_code in self.ccld_monitors:
            return self.ccld_monitors[stock_code].get_current_data()
        return None 