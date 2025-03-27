"""VI 모니터링 서비스"""

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import asyncio
from config.logging_config import setup_logger
from api.realtime.websocket.websocket_manager import WebSocketManager
from api.realtime.websocket.websocket_base import WebSocketConfig
from api.constants import TRCode, VIStatus
from config.settings import LS_WS_URL, VI_MONITORING_INTERVAL

class VIMonitorService:
    """VI 모니터링 서비스 클래스"""
    
    def __init__(self, token: str):
        """초기화
        
        Args:
            token (str): 인증 토큰
        """
        self.logger = setup_logger(__name__)
        self.token = token
        self.ws_manager: Optional[WebSocketManager] = None
        self.monitoring_active = False
        self.vi_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.vi_active_stocks: Dict[str, Dict[str, Any]] = {}
        
        # 웹소켓 설정
        self.ws_config: WebSocketConfig = {
            "url": LS_WS_URL,
            "token": token,
            "max_subscriptions": 100,
            "max_reconnect_attempts": 5,
            "reconnect_delay": 5,
            "ping_interval": 30,
            "ping_timeout": 10,
            "max_cache_size": 1000,
            "cache_expiry": 60
        }
        
    async def start(self) -> None:
        """모니터링 시작"""
        try:
            if self.monitoring_active:
                self.logger.warning("이미 모니터링이 실행 중입니다.")
                return
                
            # 웹소켓 매니저 초기화
            self.ws_manager = WebSocketManager(self.ws_config)
            
            # 이벤트 핸들러 등록
            self.ws_manager.add_event_handler("message", self._handle_vi_message)
            self.ws_manager.add_event_handler("error", self._handle_error)
            self.ws_manager.add_event_handler("close", self._handle_close)
            
            # 웹소켓 연결 시작
            await self.ws_manager.start()
            
            # VI 구독 시작
            await self.ws_manager.subscribe(
                tr_code=TRCode.VI_OCCUR,
                tr_key="000000",  # 전체 종목 구독
                callback=self._handle_vi_message
            )
            
            self.monitoring_active = True
            self.logger.info("VI 모니터링이 시작되었습니다.")
            
        except Exception as e:
            self.logger.error(f"VI 모니터링 시작 중 오류 발생: {str(e)}")
            self.monitoring_active = False
            raise
            
    async def stop(self) -> None:
        """모니터링 중지"""
        try:
            if not self.monitoring_active:
                return
                
            # VI 구독 해제
            if self.ws_manager:
                await self.ws_manager.unsubscribe(
                    tr_code=TRCode.VI_OCCUR,
                    tr_key="000000"
                )
                
            # 웹소켓 연결 종료
            if self.ws_manager:
                await self.ws_manager.close()
                self.ws_manager = None
                
            self.monitoring_active = False
            self.vi_callbacks.clear()
            self.vi_active_stocks.clear()
            
            self.logger.info("VI 모니터링이 중지되었습니다.")
            
        except Exception as e:
            self.logger.error(f"VI 모니터링 중지 중 오류 발생: {str(e)}")
            raise
            
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 등록
        
        Args:
            callback (Callable[[Dict[str, Any]], None]): 콜백 함수
        """
        if callback not in self.vi_callbacks:
            self.vi_callbacks.append(callback)
            
    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 제거
        
        Args:
            callback (Callable[[Dict[str, Any]], None]): 콜백 함수
        """
        if callback in self.vi_callbacks:
            self.vi_callbacks.remove(callback)
            
    async def _handle_vi_message(self, message: Dict[str, Any]) -> None:
        """VI 메시지 처리
        
        Args:
            message (Dict[str, Any]): VI 메시지
        """
        try:
            header = message.get("header", {})
            body = message.get("body", {})
            
            if header.get("tr_cd") != TRCode.VI_OCCUR:
                return
                
            vi_data = self._parse_vi_data(body)
            if not vi_data:
                return
                
            # VI 상태 업데이트
            await self._update_vi_status(vi_data)
            
            # 콜백 함수 호출
            for callback in self.vi_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(vi_data)
                    else:
                        callback(vi_data)
                except Exception as e:
                    self.logger.error(f"콜백 함수 실행 중 오류: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"VI 메시지 처리 중 오류: {str(e)}")
            
    def _parse_vi_data(self, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """VI 데이터 파싱
        
        Args:
            body (Dict[str, Any]): 메시지 본문
            
        Returns:
            Optional[Dict[str, Any]]: 파싱된 VI 데이터
        """
        try:
            current_time = datetime.now()
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
                "vi_type": VIStatus.STATUS_MAP.get(body.get("vi_gubun", ""), "알수없음"),
                "status": "해제" if body.get("vi_gubun") == VIStatus.RELEASE else "발동"
            }
        except Exception as e:
            self.logger.error(f"VI 데이터 파싱 중 오류: {str(e)}")
            return None
            
    async def _update_vi_status(self, vi_data: Dict[str, Any]) -> None:
        """VI 상태 업데이트
        
        Args:
            vi_data (Dict[str, Any]): VI 데이터
        """
        try:
            stock_code = vi_data["shcode"]
            current_time = datetime.now()
            
            if vi_data["vi_gubun"] == VIStatus.RELEASE:  # VI 해제
                if stock_code in self.vi_active_stocks:
                    release_data = {
                        **self.vi_active_stocks[stock_code],
                        "release_time": current_time,
                        "status": "해제",
                        "duration": (current_time - self.vi_active_stocks[stock_code]["activation_time"]).total_seconds()
                    }
                    del self.vi_active_stocks[stock_code]
                    self.logger.info(self._format_vi_message(release_data))
            else:  # VI 발동
                self.vi_active_stocks[stock_code] = {
                    **vi_data,
                    "activation_time": current_time
                }
                self.logger.info(self._format_vi_message(self.vi_active_stocks[stock_code]))
                
        except Exception as e:
            self.logger.error(f"VI 상태 업데이트 중 오류: {str(e)}")
            
    def _format_vi_message(self, data: Dict[str, Any]) -> str:
        """VI 메시지 포맷팅
        
        Args:
            data (Dict[str, Any]): VI 데이터
            
        Returns:
            str: 포맷팅된 메시지
        """
        try:
            duration = data.get("duration", "")
            duration_str = f", 지속시간: {duration:.1f}초" if duration else ""
            
            return (
                f"[{data.get('timestamp', '')}] "
                f"종목: {data.get('shcode', '')}, "
                f"상태: {data.get('status', '')}, "
                f"VI유형: {data.get('vi_type', '')}, "
                f"발동가: {data.get('vi_trgprice', '')}"
                f"{duration_str}"
            )
        except Exception as e:
            self.logger.error(f"메시지 포맷팅 중 오류: {str(e)}")
            return f"[{datetime.now()}] 메시지 포맷팅 오류"
            
    async def _handle_error(self, error: Exception) -> None:
        """에러 처리
        
        Args:
            error (Exception): 에러 객체
        """
        self.logger.error(f"VI 모니터링 중 에러 발생: {str(error)}")
        
    async def _handle_close(self, data: Dict[str, Any]) -> None:
        """연결 종료 처리
        
        Args:
            data (Dict[str, Any]): 종료 데이터
        """
        code = data.get("code")
        message = data.get("message")
        self.logger.warning(f"VI 모니터링 연결 종료 (코드: {code}, 메시지: {message})")
        
        # 재연결 시도
        if self.monitoring_active:
            await self.start()
            
    def get_active_stocks(self) -> Dict[str, Dict[str, Any]]:
        """현재 VI 발동 중인 종목 목록 반환
        
        Returns:
            Dict[str, Dict[str, Any]]: {종목코드: VI 상태 정보}
        """
        return self.vi_active_stocks.copy() 