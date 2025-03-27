"""실시간 VI 발동/해제 처리 핸들러"""

from typing import Dict, Any, Optional, Union
from datetime import datetime
from config.logging_config import setup_logger
from api.realtime.websocket.websocket_handler import WebSocketHandler
from api.realtime.websocket.websocket_base import WebSocketMessage, WebSocketConfig

class VIHandler(WebSocketHandler):
    """VI 데이터 처리 핸들러"""
    
    def __init__(self):
        """초기화
        
        Args:
            config (WebSocketConfig): 웹소켓 설정
        """
        super().__init__()
        self.logger = setup_logger(__name__)
        self.vi_active_stocks: Dict[str, Dict[str, Any]] = {}
        self.vi_types = {
            "0": "해제",
            "1": "정적",
            "2": "동적",
            "3": "정적&동적"
        }
        
    async def handle_message(self, message: WebSocketMessage) -> None:
        """VI 메시지 처리
        
        Args:
            message (WebSocketMessage): VI 메시지
        """
        try:
            if not self.validate_message(message):
                self.logger.error("잘못된 메시지 형식")
                return

            header = message.get("header", {})
            body = message.get("body", {})
            
            if header.get("tr_cd") == "VI_":
                vi_data = self._parse_vi_data(body)
                await self._process_vi_data(vi_data)
                
        except Exception as e:
            await self.handle_error(e)

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

    async def _process_vi_data(self, vi_data: Dict[str, Any]) -> None:
        """VI 데이터 처리
        
        Args:
            vi_data (Dict[str, Any]): VI 데이터
        """
        try:
            if not vi_data:
                return

            stock_code = vi_data["shcode"]
            current_time = self.get_current_time()

            if vi_data["status"] == "해제":
                if stock_code in self.vi_active_stocks:
                    release_data = {
                        **self.vi_active_stocks[stock_code],
                        "release_time": current_time,
                        "status": "해제",
                        "duration": (current_time - self.vi_active_stocks[stock_code]["activation_time"]).total_seconds()
                    }
                    del self.vi_active_stocks[stock_code]
                    self.logger.info(self.format_message({"body": release_data}))
            else:
                self.vi_active_stocks[stock_code] = {
                    **vi_data,
                    "activation_time": current_time
                }
                self.logger.info(self.format_message({"body": self.vi_active_stocks[stock_code]}))

        except Exception as e:
            self.logger.error(f"VI 데이터 처리 중 오류: {str(e)}")

    async def handle_error(self, error: Exception) -> None:
        """에러 처리
        
        Args:
            error (Exception): 처리할 에러
        """
        self.logger.error(f"VI 처리 중 에러 발생: {str(error)}")
        
    def format_message(self, message: WebSocketMessage) -> str:
        """메시지 포맷팅
        
        Args:
            message (WebSocketMessage): VI 메시지
            
        Returns:
            str: 포맷팅된 메시지
        """
        try:
            body = message.get("body", {})
            vi_type = self.vi_types.get(body.get("vi_gubun", ""), "알수없음")
            status = body.get("status", "알수없음")
            duration = body.get("duration", "")
            duration_str = f", 지속시간: {duration:.1f}초" if duration else ""
            
            return (
                f"[{self.get_timestamp()}] "
                f"종목: {body.get('shcode', '')}, "
                f"상태: {status}, "
                f"VI유형: {vi_type}, "
                f"발동가: {body.get('vi_trgprice', '')}"
                f"{duration_str}"
            )
        except Exception as e:
            self.logger.error(f"메시지 포맷팅 중 오류: {str(e)}")
            return f"[{self.get_timestamp()}] 메시지 포맷팅 오류"

    def get_timestamp(self) -> str:
        """현재 시간 문자열 반환
        
        Returns:
            str: 현재 시간 문자열
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S") 