"""웹소켓 메시지 핸들러"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from datetime import datetime
import pytz
import json
from config.logging_config import setup_logger
from .websocket_base import WebSocketMessage

class WebSocketHandler(ABC):
    """웹소켓 메시지 핸들러 기본 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.kst = pytz.timezone('Asia/Seoul')

    @abstractmethod
    async def handle_message(self, message: WebSocketMessage) -> None:
        """메시지 처리
        
        Args:
            message (WebSocketMessage): 처리할 메시지
        """
        pass

    @abstractmethod
    async def handle_error(self, error: Exception) -> None:
        """에러 처리
        
        Args:
            error (Exception): 처리할 에러
        """
        pass

    def format_message(self, message: WebSocketMessage) -> str:
        """메시지 포맷팅
        
        Args:
            message (WebSocketMessage): 포맷팅할 메시지
            
        Returns:
            str: 포맷팅된 메시지
        """
        try:
            header = message.get("header", {})
            body = message.get("body", {})
            tr_cd = header.get("tr_cd", "")
            tr_key = body.get("tr_key", "")
            msg_type = message.get("type", "UNKNOWN")
            
            return (
                f"[{self.get_timestamp()}] "
                f"Type: {msg_type}, TR: {tr_cd}, Key: {tr_key}"
            )
        except Exception as e:
            self.logger.error(f"메시지 포맷팅 중 오류: {str(e)}")
            return f"[{self.get_timestamp()}] 메시지 포맷팅 오류"

    def get_current_time(self) -> datetime:
        """현재 시간 반환
        
        Returns:
            datetime: 현재 시간 (KST)
        """
        return datetime.now(self.kst)

    def get_timestamp(self) -> str:
        """현재 시간 문자열 반환
        
        Returns:
            str: 현재 시간 문자열
        """
        return self.get_current_time().strftime("%Y-%m-%d %H:%M:%S")

    def validate_message(self, message: Union[Dict[str, Any], WebSocketMessage]) -> bool:
        """메시지 유효성 검사
        
        Args:
            message (Union[Dict[str, Any], WebSocketMessage]): 검사할 메시지
            
        Returns:
            bool: 유효성 여부
        """
        try:
            if not isinstance(message, dict):
                return False
                
            if "header" not in message or "body" not in message:
                return False
                
            header = message.get("header", {})
            if not isinstance(header, dict):
                return False
                
            body = message.get("body", {})
            if not isinstance(body, dict):
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"메시지 유효성 검사 중 오류: {str(e)}")
            return False

class DefaultWebSocketHandler(WebSocketHandler):
    """기본 웹소켓 메시지 핸들러"""
    
    async def handle_message(self, message: WebSocketMessage) -> None:
        """메시지 처리
        
        Args:
            message (WebSocketMessage): 처리할 메시지
        """
        try:
            if not self.validate_message(message):
                self.logger.error("잘못된 메시지 형식")
                return
                
            formatted_message = self.format_message(message)
            self.logger.info(f"메시지 수신: {formatted_message}")
            
        except Exception as e:
            await self.handle_error(e)

    async def handle_error(self, error: Exception) -> None:
        """에러 처리
        
        Args:
            error (Exception): 처리할 에러
        """
        self.logger.error(f"에러 발생: {str(error)}")

    def format_message(self, message: WebSocketMessage) -> str:
        """메시지 포맷팅
        
        Args:
            message (WebSocketMessage): 포맷팅할 메시지
            
        Returns:
            str: 포맷팅된 메시지
        """
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
        except Exception as e:
            self.logger.error(f"메시지 포맷팅 중 오류: {str(e)}")
            return f"[{self.get_timestamp()}] 메시지 포맷팅 오류" 