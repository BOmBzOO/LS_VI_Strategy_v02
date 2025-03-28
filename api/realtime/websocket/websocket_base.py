"""웹소켓 기본 클래스"""

import logging
from typing import Dict, Any, Optional, Callable, TypedDict, Literal, Union, List
from datetime import datetime
from enum import Enum, auto
import pytz
import websocket
import asyncio
from functools import partial
from config.logging_config import setup_logger

class WebSocketState(Enum):
    """웹소켓 연결 상태"""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    CLOSING = auto()
    CLOSED = auto()
    ERROR = auto()

class WebSocketConfig(TypedDict):
    """웹소켓 설정"""
    url: str  # 웹소켓 URL
    token: str  # 인증 토큰
    max_subscriptions: int  # 최대 구독 개수
    max_reconnect_attempts: int  # 최대 재연결 시도 횟수
    reconnect_delay: int  # 재연결 대기 시간 (초)
    ping_interval: int  # ping 전송 간격 (초)
    ping_timeout: int  # ping 타임아웃 (초)
    connect_timeout: int  # 연결 타임아웃 (초)

class WebSocketMessage(TypedDict):
    """웹소켓 메시지"""
    header: Dict[str, Any]  # 메시지 헤더
    body: Dict[str, Any]  # 메시지 본문
    type: Literal["REQUEST", "RESPONSE", "EVENT"]  # 메시지 타입

# 기본 웹소켓 설정
DEFAULT_CONFIG: WebSocketConfig = {
    "url": "",
    "token": "",
    "max_subscriptions": 100,
    "max_reconnect_attempts": 5,
    "reconnect_delay": 5,
    "ping_interval": 30,
    "ping_timeout": 10,
    "connect_timeout": 30
}

class EventEmitter:
    """이벤트 발생기"""
    
    def __init__(self):
        """초기화"""
        self.handlers: Dict[str, List[Callable]] = {}
        self.logger = setup_logger(__name__)
        
    def on(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 등록"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        if handler not in self.handlers[event_type]:
            self.handlers[event_type].append(handler)
            
    def off(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 제거"""
        if event_type in self.handlers and handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)
            if not self.handlers[event_type]:
                del self.handlers[event_type]
                
    async def emit(self, event_type: str, data: Any) -> None:
        """이벤트 발생"""
        if event_type not in self.handlers:
            return
            
        for handler in self.handlers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                self.logger.error(f"이벤트 핸들러 실행 중 오류: {str(e)}")

class BaseWebSocket:
    """웹소켓 기본 클래스"""
    
    def __init__(self, config: WebSocketConfig):
        """초기화"""
        self.config = config
        self.logger = setup_logger(__name__)
        self.kst = pytz.timezone('Asia/Seoul')
        self.state = WebSocketState.DISCONNECTED
        self.event_emitter = EventEmitter()
        self.reconnection_count = 0
        self.last_ping_time: Optional[datetime] = None
        
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 등록"""
        self.event_emitter.on(event_type, handler)
        
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 제거"""
        self.event_emitter.off(event_type, handler)
        
    async def emit_event(self, event_type: str, data: Any) -> None:
        """이벤트 발생"""
        await self.event_emitter.emit(event_type, data)
        
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
            asyncio.create_task(self.emit_event(
                "state_changed",
                {
                    "old_state": old_state.name,
                    "new_state": new_state.name,
                    "timestamp": self.get_timestamp()
                }
            ))
            
    def calculate_reconnect_delay(self) -> float:
        """재연결 지연 시간 계산"""
        base_delay = float(self.config["reconnect_delay"])
        max_delay = 30.0
        delay = min(base_delay * (2 ** self.reconnection_count), max_delay)
        return delay
        
    def should_reconnect(self) -> bool:
        """재연결 여부 확인"""
        return (
            self.state not in (WebSocketState.CONNECTED, WebSocketState.CONNECTING) and
            self.reconnection_count < self.config["max_reconnect_attempts"]
        )
        
    def reset_reconnection(self) -> None:
        """재연결 상태 초기화"""
        self.reconnection_count = 0
        
    def increment_reconnection(self) -> None:
        """재연결 시도 횟수 증가"""
        self.reconnection_count += 1
        
    async def handle_connection_error(self, error: Exception) -> None:
        """연결 에러 처리"""
        self.update_state(WebSocketState.ERROR)
        await self.emit_event("error", {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": self.get_timestamp()
        })
        
        if self.should_reconnect():
            self.increment_reconnection()
            delay = self.calculate_reconnect_delay()
            self.logger.info(f"재연결 대기 중... ({delay}초)")
            await asyncio.sleep(delay)
            return True
        return False
        
    def validate_config(self) -> None:
        """설정 유효성 검사"""
        if not self.config.get("url"):
            raise ValueError("웹소켓 URL이 설정되지 않았습니다.")
        if not self.config.get("token"):
            raise ValueError("인증 토큰이 설정되지 않았습니다.")
            
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.state == WebSocketState.CONNECTED 