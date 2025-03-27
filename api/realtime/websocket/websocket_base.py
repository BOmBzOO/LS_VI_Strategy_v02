"""웹소켓 기본 클래스"""

import logging
from typing import Dict, Any, Optional, Callable, TypedDict, Literal, Union
from datetime import datetime
from enum import Enum
import pytz
import websocket
import asyncio
from functools import partial
from config.logging_config import setup_logger

class WebSocketState(Enum):
    """웹소켓 연결 상태"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"

class WebSocketConfig(TypedDict):
    """웹소켓 설정"""
    url: str  # 웹소켓 URL
    token: str  # 인증 토큰
    max_subscriptions: int  # 최대 구독 개수
    max_reconnect_attempts: int  # 최대 재연결 시도 횟수
    reconnect_delay: int  # 재연결 대기 시간 (초)
    ping_interval: int  # ping 전송 간격 (초)
    ping_timeout: int  # ping 타임아웃 (초)

class WebSocketMessage(TypedDict):
    """웹소켓 메시지"""
    header: Dict[str, Any]
    body: Dict[str, Any]
    type: Literal["REQUEST", "RESPONSE", "EVENT"]

# 기본 웹소켓 설정
DEFAULT_CONFIG: WebSocketConfig = {
    "url": "",  # URL은 초기화 시 설정
    "token": "",  # 토큰은 초기화 시 설정
    "max_subscriptions": 100,  # 최대 100개 구독 가능
    "max_reconnect_attempts": 5,
    "reconnect_delay": 5,
    "ping_interval": 30,
    "ping_timeout": 10
}

class RetryManager:
    """재시도 관리 클래스"""
    
    def __init__(self, max_retries: int, base_delay: float):
        """초기화
        
        Args:
            max_retries (int): 최대 재시도 횟수
            base_delay (float): 기본 지연 시간
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.current_retry = 0
        
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """함수 실행 및 재시도
        
        Args:
            func (Callable): 실행할 함수
            *args: 함수 인자
            **kwargs: 함수 키워드 인자
            
        Returns:
            Any: 함수 실행 결과
        """
        while self.current_retry < self.max_retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.current_retry += 1
                if self.current_retry == self.max_retries:
                    raise
                delay = self.base_delay * (2 ** (self.current_retry - 1))
                await asyncio.sleep(delay)
        return None

class BaseWebSocket:
    """웹소켓 기본 클래스"""
    
    def __init__(self, config: WebSocketConfig):
        """초기화"""
        self.config = config
        self.logger = setup_logger(__name__)
        self.kst = pytz.timezone('Asia/Seoul')
        self.state = WebSocketState.DISCONNECTED
        self.last_ping_time: Optional[datetime] = None
        self.reconnection_count: int = 0
        self.event_handlers: Dict[str, list[Callable]] = {}
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 재시도 관리자 초기화
        self.retry_manager = RetryManager(
            max_retries=self.config.get("max_reconnect_attempts", 5),
            base_delay=self.config.get("reconnect_delay", 5.0)
        )
        
        # 웹소켓 디버그 모드 비활성화
        websocket.enableTrace(False)
        
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 등록"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        if handler not in self.event_handlers[event_type]:
            self.event_handlers[event_type].append(handler)
        
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 제거"""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            if not self.event_handlers[event_type]:
                del self.event_handlers[event_type]
            
    async def emit_event(self, event_type: str, data: Any) -> None:
        """이벤트 발생"""
        if event_type not in self.event_handlers:
            return

        for handler in self.event_handlers[event_type]:
            try:
                if self.event_loop is None:
                    try:
                        self.event_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        self.event_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self.event_loop)

                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    if self.event_loop.is_running():
                        self.event_loop.call_soon_threadsafe(partial(handler, data))
                    else:
                        handler(data)
            except Exception as e:
                self.logger.error(f"이벤트 핸들러 실행 중 오류 발생: {str(e)}")
                    
    def get_current_time(self) -> datetime:
        """현재 시간 반환"""
        return datetime.now(self.kst)
    
    def get_timestamp(self) -> str:
        """현재 시간 문자열 반환"""
        return self.get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    
    def update_state(self, new_state: WebSocketState) -> None:
        """상태 업데이트"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            # asyncio.create_task(self.emit_event(
            #     "state_changed", 
            #     {"old_state": old_state, "new_state": new_state}
            # ))
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.emit_event(
                    "state_changed", 
                    {"old_state": old_state, "new_state": new_state}
                ))
            except RuntimeError:
                # 실행 중인 루프가 없을 경우 새 루프 생성 및 실행
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.emit_event(
                    "state_changed", 
                    {"old_state": old_state, "new_state": new_state}
                ))

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.state == WebSocketState.CONNECTED

    def calculate_reconnect_delay(self) -> float:
        """재연결 지연 시간 계산"""
        base_delay = float(self.config["reconnect_delay"])
        max_delay = 30.0
        delay = min(base_delay * (2 ** (self.reconnection_count - 1)), max_delay)
        return delay

    async def close(self) -> None:
        """연결 종료"""
        self.update_state(WebSocketState.DISCONNECTED)
        if self.event_loop and not self.event_loop.is_closed():
            await self.emit_event("close", None)
            self.event_loop.stop()
            self.event_loop = None 