"""VI 모니터링 관리"""

from typing import Dict, Any, Optional, Callable, Union, List
from datetime import datetime, timedelta
import json
import asyncio
import pytz
from api.realtime.websocket.websocket_base import WebSocketMessage, WebSocketConfig
from api.constants import TRCode, MessageType, VIStatus
from config.settings import VI_MONITORING_INTERVAL, VI_UNSUBSCRIBE_DELAY, LS_WS_URL
from config.logging_config import setup_logger
from api.realtime.vi.vi_handler import VIHandler
from api.realtime.websocket.websocket_client import WebSocketClient

class VIManager(VIHandler):
    """VI 모니터링 관리"""

    def __init__(self, ws: WebSocketClient):
        """초기화

        Args:
            ws (WebSocketClient): 웹소켓 클라이언트
        """
        super().__init__()
        self.vi_pending_unsubscribe: Dict[str, datetime] = {}
        self.unsubscribed_stocks: Dict[str, Dict] = {}
        self.monitoring_active = False
        self.subscription_count = 0
        self.ws = ws
        self.config = ws.config  # 웹소켓 설정 공유
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.kst = pytz.timezone('Asia/Seoul')  # KST 타임존 추가
        
        # 이벤트 핸들러 등록
        self.ws.add_event_handler("message", self.handle_message)
        self.ws.add_event_handler("error", self.handle_error)
        self.ws.add_event_handler("close", self._handle_close)

    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 등록

        Args:
            event_type (str): 이벤트 타입
            handler (Callable): 핸들러 함수
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        if handler not in self.event_handlers[event_type]:
            self.event_handlers[event_type].append(handler)

    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 제거

        Args:
            event_type (str): 이벤트 타입
            handler (Callable): 핸들러 함수
        """
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)

    async def emit_event(self, event_type: str, data: Any) -> None:
        """이벤트 발생

        Args:
            event_type (str): 이벤트 타입
            data (Any): 이벤트 데이터
        """
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"이벤트 핸들러 실행 중 오류: {str(e)}")

    async def start(self) -> bool:
        """웹소켓 연결 시작

        Returns:
            bool: 연결 성공 여부
        """

    async def stop(self) -> None:
        """웹소켓 연결 종료"""
        try:
            if not self.is_connected():
                return

            await self.ws.close()
            self.logger.info("VI 웹소켓 연결 종료")

        except Exception as e:
            self.logger.error(f"VI 웹소켓 종료 중 오류: {str(e)}")

    def is_connected(self) -> bool:
        """웹소켓 연결 상태 확인

        Returns:
            bool: 연결 여부
        """
        return self.ws.is_connected if self.ws else False

    async def send_vi_message(self, message: WebSocketMessage) -> bool:
        """VI 메시지 전송

        Args:
            message (WebSocketMessage): 전송할 메시지

        Returns:
            bool: 성공 여부
        """
        try:
            if not self.is_connected():
                self.logger.warning("VI 웹소켓이 연결되지 않았습니다.")
                return False

            await self.ws.send(message)
            return True

        except Exception as e:
            self.logger.error(f"VI 메시지 전송 중 오류: {str(e)}")
            return False


    async def _handle_close(self, data: Dict[str, Any]) -> None:
        """연결 종료 처리
        
        Args:
            data (Dict[str, Any]): 종료 데이터
        """
        try:
            code = data.get("code")
            message = data.get("message")
            self.logger.warning(f"VI 웹소켓 연결 종료 (코드: {code}, 메시지: {message})")
            
            # 재연결 시도
            await self.start()
            
            # 재연결 성공 시 VI 구독 재시작
            if self.is_connected() and self.monitoring_active:
                await self.subscribe_vi("000000")
            
        except Exception as e:
            self.logger.error(f"VI 웹소켓 종료 처리 중 오류: {str(e)}")

    async def subscribe_vi(self, stock_code: str) -> bool:
        """VI 웹소켓 구독

        Args:
            stock_code (str): 종목 코드

        Returns:
            bool: 성공 여부
        """
        try:
            if self.subscription_count >= self.config["max_subscriptions"]:
                self.logger.error("최대 구독 개수 초과")
                return False

            if stock_code in self.vi_pending_unsubscribe:
                del self.vi_pending_unsubscribe[stock_code]

            message = {
                "header": {
                    "token": self.config["token"],
                    "tr_type": "3",
                    "tr_cd": "VI_"
                },
                "body": {
                    "tr_key": stock_code,
                    "data": {}
                },
                "type": "REQUEST"
            }

            if await self.send_vi_message(message):
                self.subscription_count += 1
                self.logger.info(f"VI 구독 성공: {stock_code}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"VI 구독 중 오류 발생: {str(e)}")
            return False

    async def unsubscribe_vi(self, stock_code: str) -> bool:
        """VI 웹소켓 구독 해제

        Args:
            stock_code (str): 종목 코드

        Returns:
            bool: 성공 여부
        """
        try:
            if stock_code not in self.vi_active_stocks and stock_code not in self.vi_pending_unsubscribe:
                return True

            message = {
                "header": {
                    "token": self.config["token"],
                    "tr_type": "4",
                    "tr_cd": "VI_"
                },
                "body": {
                    "tr_key": stock_code,
                    "data": {}
                },
                "type": "REQUEST"
            }

            if await self.send_vi_message(message):
                self.vi_pending_unsubscribe[stock_code] = self.get_current_time()
                if stock_code in self.vi_active_stocks:
                    self.unsubscribed_stocks[stock_code] = self.vi_active_stocks[stock_code]
                    del self.vi_active_stocks[stock_code]
                self.subscription_count = max(0, self.subscription_count - 1)
                self.logger.info(f"VI 구독 해제 성공: {stock_code}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"VI 구독 해제 중 오류 발생: {str(e)}")
            return False

    async def start_monitoring(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        """VI 모니터링 시작"""
        try:
            if self.monitoring_active:
                self.logger.warning("이미 모니터링이 실행 중입니다.")
                return

            if callback:
                self.add_event_handler("vi_status_changed", callback)

            self.monitoring_active = True
            self.logger.info("VI 모니터링 시작")

            # 전체 종목 구독
            await self.subscribe_vi("000000")

        except Exception as e:
            self.logger.error(f"VI 모니터링 시작 중 오류 발생: {str(e)}")
            self.monitoring_active = False
            raise

    async def stop_monitoring(self) -> None:
        """VI 모니터링 중지"""
        try:
            if not self.monitoring_active:
                return

            # 전체 종목 구독 해제
            await self.unsubscribe_vi("000000")

            self.monitoring_active = False
            self.event_handlers.clear()
            self.vi_active_stocks.clear()
            self.vi_pending_unsubscribe.clear()
            self.unsubscribed_stocks.clear()
            self.subscription_count = 0

            self.logger.info("VI 모니터링 중지")

        except Exception as e:
            self.logger.error(f"VI 모니터링 중지 중 오류 발생: {str(e)}")
            raise

    def get_pending_unsubscribe_stocks(self) -> Dict[str, datetime]:
        """구독 해제 대기 중인 종목 목록 반환"""
        return self.vi_pending_unsubscribe.copy()

    def get_unsubscribed_stocks(self) -> Dict[str, Dict]:
        """구독 해제 완료된 종목 목록 반환"""
        return self.unsubscribed_stocks.copy()

    def set_token(self, token: str) -> None:
        """토큰 설정

        Args:
            token (str): 새로운 토큰
        """
        self.config["token"] = token
        self.logger.info("토큰 업데이트 완료")

    async def close(self) -> None:
        """웹소켓 연결 종료"""
        try:
            if self.ws:
                await self.ws.close()
                self.logger.info("VI 웹소켓 연결 종료")
        except Exception as e:
            self.logger.error(f"VI 웹소켓 종료 중 오류: {str(e)}") 