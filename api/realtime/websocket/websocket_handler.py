"""웹소켓 메시지 핸들러"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import pytz
import json
from config.logging_config import setup_logger
from .websocket_base import WebSocketMessage, WebSocketState

class MessageValidator:
    """메시지 유효성 검사기"""
    
    @staticmethod
    def validate_header(header: Dict[str, Any]) -> bool:
        """헤더 유효성 검사"""
        required_fields = ["tr_type", "token"]
        return all(field in header for field in required_fields)
        
    @staticmethod
    def validate_body(body: Dict[str, Any]) -> bool:
        """본문 유효성 검사"""
        required_fields = ["tr_cd", "tr_key"]
        return all(field in body for field in required_fields)
        
    @staticmethod
    def validate_message(message: Union[Dict[str, Any], WebSocketMessage]) -> bool:
        """메시지 유효성 검사"""
        try:
            if not isinstance(message, dict):
                return False
                
            if "header" not in message or "body" not in message:
                return False
                
            header = message["header"]
            if not isinstance(header, dict) or not MessageValidator.validate_header(header):
                return False
                
            body = message["body"]
            if not isinstance(body, dict) or not MessageValidator.validate_body(body):
                return False
                
            return True
            
        except Exception:
            return False

class MessageFormatter:
    """메시지 포맷터"""
    
    def __init__(self):
        """초기화"""
        self.kst = pytz.timezone('Asia/Seoul')
        
    def get_timestamp(self) -> str:
        """현재 시간 문자열 반환"""
        return datetime.now(self.kst).strftime("%Y-%m-%d %H:%M:%S")
        
    def format_message(self, message: WebSocketMessage) -> str:
        """메시지 포맷팅"""
        try:
            header = message.get("header", {})
            body = message.get("body", {})
            tr_cd = header.get("tr_cd", "")
            tr_key = body.get("tr_key", "")
            msg_type = message.get("type", "UNKNOWN")
            data = json.dumps(body.get("data", {}), ensure_ascii=False)
            
            return (
                f"[{self.get_timestamp()}] "
                f"Type: {msg_type}, TR: {tr_cd}, Key: {tr_key}, "
                f"Data: {data}"
            )
        except Exception:
            return f"[{self.get_timestamp()}] 메시지 포맷팅 오류"

class WebSocketHandler(ABC):
    """웹소켓 메시지 핸들러 기본 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.validator = MessageValidator()
        self.formatter = MessageFormatter()
        self.handlers: Dict[str, List[Any]] = {}
        
    def register_handler(self, message_type: str, handler: Any) -> None:
        """메시지 핸들러 등록"""
        if message_type not in self.handlers:
            self.handlers[message_type] = []
        self.handlers[message_type].append(handler)
        
    def unregister_handler(self, message_type: str, handler: Any) -> None:
        """메시지 핸들러 제거"""
        if message_type in self.handlers and handler in self.handlers[message_type]:
            self.handlers[message_type].remove(handler)
            
    async def process_message(self, message: WebSocketMessage) -> None:
        """메시지 처리"""
        try:
            if not self.validator.validate_message(message):
                self.logger.error("잘못된 메시지 형식")
                return
                
            message_type = message.get("type", "UNKNOWN")
            handlers = self.handlers.get(message_type, [])
            
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    self.logger.error(f"메시지 핸들러 실행 중 오류: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"메시지 처리 중 오류: {str(e)}")
            await self.handle_error(e)
            
    @abstractmethod
    async def handle_message(self, message: WebSocketMessage) -> None:
        """메시지 처리"""
        pass
        
    @abstractmethod
    async def handle_error(self, error: Exception) -> None:
        """에러 처리"""
        pass

class DefaultWebSocketHandler(WebSocketHandler):
    """기본 웹소켓 메시지 핸들러"""
    
    async def handle_message(self, message: WebSocketMessage) -> None:
        """메시지 처리"""
        try:
            if not self.validator.validate_message(message):
                self.logger.error("잘못된 메시지 형식")
                return
                
            formatted_message = self.formatter.format_message(message)
            self.logger.info(f"메시지 수신: {formatted_message}")
            await self.process_message(message)
            
        except Exception as e:
            await self.handle_error(e)
            
    async def handle_error(self, error: Exception) -> None:
        """에러 처리"""
        self.logger.error(f"에러 발생: {str(error)}")
        
    def format_message(self, message: WebSocketMessage) -> str:
        """메시지 포맷팅"""
        return self.formatter.format_message(message) 