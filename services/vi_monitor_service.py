"""VI 모니터링 서비스"""

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import asyncio
from config.logging_config import setup_logger
from api.realtime.websocket.websocket_manager import WebSocketManager
from api.realtime.websocket.websocket_base import WebSocketState, WebSocketConfig, WebSocketMessage
from api.realtime.websocket.websocket_handler import DefaultWebSocketHandler
from api.constants import TRCode, VIStatus
from config.settings import LS_WS_URL, VI_MONITORING_INTERVAL
import traceback

class VIData:
    """VI 데이터 클래스"""
    
    def __init__(self, data: Dict[str, Any]):
        """초기화"""
        # API 명세에 맞춰 필드 정의
        self.vi_gubun = data.get("vi_gubun", "")  # 구분(0:해제1:정적발동2:동적발동3:정적&동적)
        self.svi_recprice = data.get("svi_recprice", "")  # 정적VI발동기준가격
        self.dvi_recprice = data.get("dvi_recprice", "")  # 동적VI발동기준가격
        self.vi_trgprice = data.get("vi_trgprice", "")  # VI발동가격
        self.shcode = data.get("shcode", "")  # 단축코드(KEY)
        self.ref_shcode = data.get("ref_shcode", "")  # 참조코드
        self.time = data.get("time", "")  # 시간
        self.exchname = data.get("exchname", "")  # 거래소명
        self.timestamp = datetime.now().isoformat()
        
        # VI 상태 매핑
        vi_status_map = {
            "0": "해제",
            "1": "정적발동",
            "2": "동적발동",
            "3": "정적&동적"
        }
        self.vi_type = vi_status_map.get(self.vi_gubun, "알수없음")
        self.status = "해제" if self.vi_gubun == "0" else "발동"
        
        # 추가 상태 정보
        self.activation_time: Optional[datetime] = None
        self.release_time: Optional[datetime] = None
        self.duration: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "vi_gubun": self.vi_gubun,
            "svi_recprice": self.svi_recprice,
            "dvi_recprice": self.dvi_recprice,
            "vi_trgprice": self.vi_trgprice,
            "shcode": self.shcode,
            "ref_shcode": self.ref_shcode,
            "time": self.time,
            "exchname": self.exchname,
            "timestamp": self.timestamp,
            "vi_type": self.vi_type,
            "status": self.status,
            "activation_time": self.activation_time.isoformat() if self.activation_time else None,
            "release_time": self.release_time.isoformat() if self.release_time else None,
            "duration": self.duration
        }

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
        self.ws_handler: Optional[DefaultWebSocketHandler] = None
        self.state = WebSocketState.DISCONNECTED
        self.vi_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.vi_active_stocks: Dict[str, VIData] = {}
        
        # 웹소켓 설정
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
        
    async def start(self) -> None:
        """모니터링 시작"""
        try:
            if self.state != WebSocketState.DISCONNECTED:
                self.logger.warning(f"잘못된 상태에서의 시작 시도: {self.state.name}")
                return
                
            self.state = WebSocketState.CONNECTING
            
            # 웹소켓 핸들러 초기화
            self.ws_handler = DefaultWebSocketHandler()
            self.ws_handler.register_handler("VI_OCCUR", self._handle_vi_message)
            
            # 웹소켓 매니저 초기화
            self.ws_manager = WebSocketManager(self.ws_config)
            self.ws_manager.add_event_handler("message", self._handle_message)
            self.ws_manager.add_event_handler("error", self._handle_error)
            self.ws_manager.add_event_handler("close", self._handle_close)
            self.ws_manager.add_event_handler("open", self._handle_open)

                        # VI 데이터 처리 콜백 등록
            self.ws_manager.add_callback(self._handle_vi_message)
            
            # 웹소켓 연결 시작
            await self.ws_manager.start()
            
            # VI 구독 시작
            await self._subscribe_vi()
            
            self.state = WebSocketState.CONNECTED
            self.logger.info("VI 모니터링이 시작되었습니다.")
            
        except Exception as e:
            self.state = WebSocketState.ERROR
            self.logger.error(f"VI 모니터링 시작 중 오류 발생: {str(e)}")
            await self.stop()
            raise
            
    async def stop(self) -> None:
        """모니터링 중지"""
        try:
            if self.state == WebSocketState.DISCONNECTED:
                return
                
            self.state = WebSocketState.CLOSING
            
            # VI 구독 해제
            if self.ws_manager and self.ws_manager.is_connected():
                try:
                    await self._unsubscribe_vi()
                except Exception as e:
                    self.logger.warning(f"VI 구독 해제 중 오류 발생: {str(e)}")
                
            # 웹소켓 연결 종료
            if self.ws_manager:
                try:
                    await self.ws_manager.stop()
                except Exception as e:
                    self.logger.warning(f"웹소켓 연결 종료 중 오류 발생: {str(e)}")
                finally:
                    self.ws_manager = None
                    
            # 자원 정리
            self.ws_handler = None
            self.vi_callbacks.clear()
            self.vi_active_stocks.clear()
            self.state = WebSocketState.DISCONNECTED
            
            self.logger.info("VI 모니터링이 중지되었습니다.")
            
        except Exception as e:
            self.logger.error(f"VI 모니터링 중지 중 오류 발생: {str(e)}")
            self.state = WebSocketState.ERROR
            raise
            
    async def _subscribe_vi(self) -> None:
        """VI 구독"""
        if not self.ws_manager or not self.ws_manager.is_connected():
            raise RuntimeError("웹소켓이 연결되지 않았습니다.")
            
        await self.ws_manager.subscribe(
            tr_code=TRCode.VI_OCCUR,
            tr_key="000000",  # 전체 종목 구독
            callback=self._handle_vi_message
        )
        
    async def _unsubscribe_vi(self) -> None:
        """VI 구독 해제"""
        if not self.ws_manager or not self.ws_manager.is_connected():
            return
            
        await self.ws_manager.unsubscribe(
            tr_code=TRCode.VI_OCCUR,
            tr_key="000000"
        )
        
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 등록"""
        if callback not in self.vi_callbacks:
            self.vi_callbacks.append(callback)
            
    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 제거"""
        if callback in self.vi_callbacks:
            self.vi_callbacks.remove(callback)
            
    async def _handle_message(self, message: WebSocketMessage) -> None:
        """메시지 처리"""
        if not self.ws_handler:
            return
            
        await self.ws_handler.handle_message(message)
        
    async def _handle_vi_message(self, message: Dict[str, Any]) -> None:
        """VI 메시지 처리"""
        try:
            # 콜백이 있는 경우 전체 메시지를 전달
            if self.vi_callbacks:
                for callback in self.vi_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)
                    except Exception as e:
                        self.logger.error(f"콜백 함수 실행 중 오류: {str(e)}")
                return
                
            # 콜백이 없는 경우 메시지 처리 및 로깅
            header = message.get("header", {})
            body = message.get("body", {})
            
            # 응답 메시지 처리
            if "rsp_cd" in header:
                rsp_msg = header.get("rsp_msg", "알 수 없는 메시지")
                if header["rsp_cd"] == "00000":
                    self.logger.info(f"VI 응답: {rsp_msg}")
                else:
                    self.logger.error(f"VI 구독 오류: {rsp_msg}")
                return
                
            # VI 메시지가 아닌 경우 무시
            if header.get("tr_cd") != TRCode.VI_OCCUR:
                return
                
            # body가 None인 경우 무시
            if not body or not isinstance(body, dict):
                return
                
            # VI 데이터 처리 및 로깅
            vi_data = VIData(body)
            await self._update_vi_status(vi_data)
            self.logger.info(self._format_vi_message(vi_data))
                    
        except Exception as e:
            self.logger.error(f"VI 메시지 처리 중 오류: {str(e)}\n{traceback.format_exc()}")
            
    async def _update_vi_status(self, vi_data: VIData) -> None:
        """VI 상태 업데이트"""
        try:
            stock_code = vi_data.shcode
            current_time = datetime.now()
            
            if vi_data.vi_gubun == VIStatus.RELEASE:  # VI 해제
                if stock_code in self.vi_active_stocks:
                    active_data = self.vi_active_stocks[stock_code]
                    active_data.release_time = current_time
                    active_data.status = "해제"
                    active_data.duration = (current_time - active_data.activation_time).total_seconds() if active_data.activation_time else 0
                    
                    self.logger.info(self._format_vi_message(active_data))
                    del self.vi_active_stocks[stock_code]
            else:  # VI 발동
                vi_data.activation_time = current_time
                self.vi_active_stocks[stock_code] = vi_data
                self.logger.info(self._format_vi_message(vi_data))
                
        except Exception as e:
            self.logger.error(f"VI 상태 업데이트 중 오류: {str(e)}")
            
    def _format_vi_message(self, data: VIData) -> str:
        """VI 메시지 포맷팅"""
        try:
            duration_str = f", 지속시간: {data.duration:.1f}초" if data.duration is not None else ""
            
            return (
                f"[{data.timestamp}] "
                f"종목: {data.shcode}, "
                f"상태: {data.status}, "
                f"VI유형: {data.vi_type}, "
                f"발동가: {data.vi_trgprice}, "
                f"정적기준가: {data.svi_recprice}, "
                f"동적기준가: {data.dvi_recprice}"
                f"{duration_str}"
            )
        except Exception as e:
            self.logger.error(f"메시지 포맷팅 중 오류: {str(e)}")
            return f"[{datetime.now()}] 메시지 포맷팅 오류"
            
    async def _handle_error(self, error: Exception) -> None:
        """에러 처리"""
        self.logger.error(f"VI 모니터링 중 에러 발생: {str(error)}")
        self.state = WebSocketState.ERROR
        
    async def _handle_close(self, data: Dict[str, Any]) -> None:
        """연결 종료 처리"""
        code = data.get("code")
        message = data.get("message")
        self.logger.warning(f"VI 모니터링 연결 종료 (코드: {code}, 메시지: {message})")
        
        if self.state not in [WebSocketState.CLOSING, WebSocketState.DISCONNECTED]:
            self.state = WebSocketState.DISCONNECTED
            await self.start()  # 자동 재연결
            
    async def _handle_open(self, _: Any) -> None:
        """연결 시작 처리"""
        self.logger.info("VI 모니터링 연결이 열렸습니다.")
        
    def get_active_stocks(self) -> Dict[str, Dict[str, Any]]:
        """현재 VI 발동 중인 종목 목록 반환"""
        return {code: data.to_dict() for code, data in self.vi_active_stocks.items()} 