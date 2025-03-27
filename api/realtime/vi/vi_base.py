"""VI 기본 클래스"""

from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime
import asyncio
import json
from config.logging_config import setup_logger
from api.realtime.websocket.websocket_base import BaseWebSocket, WebSocketState, WebSocketConfig, WebSocketMessage

class VIBase(BaseWebSocket):
    """VI 기본 클래스"""

    def __init__(self, config: WebSocketConfig):
        """초기화

        Args:
            config (WebSocketConfig): 웹소켓 설정
        """
        super().__init__(config)
        self.logger = setup_logger(__name__)
        self.vi_active_stocks: Dict[str, Dict[str, Any]] = {}
        self.monitoring_callbacks: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self.vi_types = {
            "0": "해제",
            "1": "정적",
            "2": "동적",
            "3": "정적&동적"
        }

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

            if not self.validate_vi_message(message):
                self.logger.error("잘못된 VI 메시지 형식입니다.")
                return False

            await self.emit_event("send_message", message)
            return True

        except Exception as e:
            self.logger.error(f"VI 메시지 전송 중 오류: {str(e)}")
            return False

    def validate_vi_message(self, message: Union[Dict[str, Any], WebSocketMessage]) -> bool:
        """VI 메시지 유효성 검사

        Args:
            message (Union[Dict[str, Any], WebSocketMessage]): 검사할 메시지

        Returns:
            bool: 유효성 여부
        """
        try:
            if not isinstance(message, dict):
                return False

            header = message.get("header", {})
            if not isinstance(header, dict) or "tr_cd" not in header:
                return False

            body = message.get("body", {})
            if not isinstance(body, dict) or "tr_key" not in body:
                return False

            return True

        except Exception as e:
            self.logger.error(f"VI 메시지 유효성 검사 중 오류: {str(e)}")
            return False

    async def handle_vi_message(self, message: WebSocketMessage) -> None:
        """VI 메시지 처리

        Args:
            message (WebSocketMessage): VI 메시지
        """
        try:
            if not self.validate_vi_message(message):
                self.logger.error("잘못된 VI 메시지 형식입니다.")
                return

            header = message.get("header", {})
            body = message.get("body", {})
            
            if header.get("tr_cd") == "VI_":
                vi_data = self._parse_vi_data(body)
                await self._update_vi_status(vi_data)
                await self._notify_callbacks(vi_data)
                await self.emit_event("vi_status_changed", vi_data)
                
        except Exception as e:
            self.logger.error(f"VI 메시지 처리 중 오류: {str(e)}")

    def _parse_vi_data(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """VI 데이터 파싱

        Args:
            body (Dict[str, Any]): 메시지 본문

        Returns:
            Dict[str, Any]: 파싱된 VI 데이터
        """
        try:
            current_time = self.get_current_time()
            return {
                "vi_gubun": body.get("vi_gubun", ""),
                "svi_recprice": body.get("svi_recprice", ""),
                "dvi_recprice": body.get("dvi_recprice", ""),
                "vi_trgprice": body.get("vi_trgprice", ""),
                "shcode": body.get("shcode", ""),
                "ref_shcode": body.get("ref_shcode", ""),
                "time": body.get("time", ""),
                "exchname": body.get("exchname", ""),
                "timestamp": current_time.isoformat(),
                "vi_type": self.vi_types.get(body.get("vi_gubun", ""), "알수없음"),
                "status": "해제" if body.get("vi_gubun") == "0" else "발동"
            }
        except Exception as e:
            self.logger.error(f"VI 데이터 파싱 중 오류: {str(e)}")
            return {}

    async def _update_vi_status(self, vi_data: Dict[str, Any]) -> None:
        """VI 상태 업데이트

        Args:
            vi_data (Dict[str, Any]): VI 데이터
        """
        try:
            stock_code = vi_data["shcode"]
            current_time = self.get_current_time()

            if vi_data["vi_gubun"] == "0":  # VI 해제
                if stock_code in self.vi_active_stocks:
                    release_data = {
                        **self.vi_active_stocks[stock_code],
                        "release_time": current_time,
                        "status": "해제",
                        "duration": (current_time - self.vi_active_stocks[stock_code]["activation_time"]).total_seconds()
                    }
                    del self.vi_active_stocks[stock_code]
                    await self.emit_event("vi_released", release_data)
                    self.logger.info(self.format_vi_message({"body": release_data}))
            else:  # VI 발동
                self.vi_active_stocks[stock_code] = {
                    **vi_data,
                    "activation_time": current_time
                }
                await self.emit_event("vi_activated", self.vi_active_stocks[stock_code])
                self.logger.info(self.format_vi_message({"body": self.vi_active_stocks[stock_code]}))

        except Exception as e:
            self.logger.error(f"VI 상태 업데이트 중 오류: {str(e)}")

    async def _notify_callbacks(self, vi_data: Dict[str, Any]) -> None:
        """콜백 함수 호출

        Args:
            vi_data (Dict[str, Any]): VI 데이터
        """
        try:
            stock_code = vi_data["shcode"]
            if stock_code in self.monitoring_callbacks:
                callback = self.monitoring_callbacks[stock_code]
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(vi_data)
                    else:
                        callback(vi_data)
                except Exception as e:
                    self.logger.error(f"콜백 함수 실행 중 오류: {str(e)}")

        except Exception as e:
            self.logger.error(f"콜백 알림 중 오류: {str(e)}")

    def get_active_stocks(self) -> Dict[str, Dict[str, Any]]:
        """현재 VI 발동 중인 종목 목록 반환

        Returns:
            Dict[str, Dict[str, Any]]: {종목코드: VI 상태 정보}
        """
        return self.vi_active_stocks.copy()

    def format_vi_message(self, message: WebSocketMessage) -> str:
        """VI 메시지 포맷팅

        Args:
            message (WebSocketMessage): VI 메시지

        Returns:
            str: 포맷팅된 메시지
        """
        try:
            body = message.get("body", {})
            vi_type = self.vi_types.get(body.get("vi_gubun", ""), "알수없음")
            status = body.get("status", "알수없음")
            
            return (
                f"[{self.get_timestamp()}] "
                f"종목: {body.get('shcode', '')}, "
                f"상태: {status}, "
                f"VI유형: {vi_type}, "
                f"발동가: {body.get('vi_trgprice', '')}"
            )
        except Exception as e:
            self.logger.error(f"메시지 포맷팅 중 오류: {str(e)}")
            return f"[{self.get_timestamp()}] 메시지 포맷팅 오류" 