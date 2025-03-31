"""실시간 체결 모니터링 서비스

실시간 체결 데이터 모니터링을 위한 서비스 클래스를 제공합니다.
"""

from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime
from config.logging_config import setup_logger
import asyncio
from api.realtime.websocket.websocket_manager import WebSocketManager
from api.realtime.websocket.websocket_base import WebSocketState, WebSocketConfig, WebSocketMessage
from api.realtime.websocket.websocket_handler import DefaultWebSocketHandler
from api.constants import TRCode, MarketType
from config.settings import LS_WS_URL
import traceback
import json

class CCLDData:
    """체결 데이터 클래스"""
    
    def __init__(self, data: Dict[str, Any]):
        """초기화"""
        # API 명세에 맞춰 필드 정의
        self.shcode = data.get("shcode", "")  # 단축코드
        self.chetime = data.get("chetime", "")  # 체결시간
        self.sign = data.get("sign", "")  # 전일대비구분
        self.change = data.get("change", "")  # 전일대비
        self.drate = data.get("drate", "")  # 등락율
        self.price = data.get("price", "")  # 현재가
        self.opentime = data.get("opentime", "")  # 시가시간
        self.open = data.get("open", "")  # 시가
        self.hightime = data.get("hightime", "")  # 고가시간
        self.high = data.get("high", "")  # 고가
        self.lowtime = data.get("lowtime", "")  # 저가시간
        self.low = data.get("low", "")  # 저가
        self.cgubun = data.get("cgubun", "")  # 체결구분
        self.cvolume = data.get("cvolume", "")  # 체결량
        self.volume = data.get("volume", "")  # 누적거래량
        self.value = data.get("value", "")  # 누적거래대금
        self.mdvolume = data.get("mdvolume", "")  # 매도누적체결량
        self.mdchecnt = data.get("mdchecnt", "")  # 매도누적체결건수
        self.msvolume = data.get("msvolume", "")  # 매수누적체결량
        self.mschecnt = data.get("mschecnt", "")  # 매수누적체결건수
        self.cpower = data.get("cpower", "")  # 체결강도
        self.w_avrg = data.get("w_avrg", "")  # 가중평균가
        self.offerho = data.get("offerho", "")  # 매도호가
        self.bidho = data.get("bidho", "")  # 매수호가
        self.status = data.get("status", "")  # 장정보
        self.jnilvolume = data.get("jnilvolume", "")  # 전일동시간대거래량
        self.exchname = data.get("exchname", "")  # 거래소명
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "shcode": self.shcode,
            "chetime": self.chetime,
            "sign": self.sign,
            "change": self.change,
            "drate": self.drate,
            "price": self.price,
            "opentime": self.opentime,
            "open": self.open,
            "hightime": self.hightime,
            "high": self.high,
            "lowtime": self.lowtime,
            "low": self.low,
            "cgubun": self.cgubun,
            "cvolume": self.cvolume,
            "volume": self.volume,
            "value": self.value,
            "mdvolume": self.mdvolume,
            "mdchecnt": self.mdchecnt,
            "msvolume": self.msvolume,
            "mschecnt": self.mschecnt,
            "cpower": self.cpower,
            "w_avrg": self.w_avrg,
            "offerho": self.offerho,
            "bidho": self.bidho,
            "status": self.status,
            "jnilvolume": self.jnilvolume,
            "exchname": self.exchname,
            "timestamp": self.timestamp
        }

class CCLDMonitorService:
    """실시간 체결 모니터링 서비스 클래스"""

    def __init__(self, token: str, stock_code: str, market_type: str = MarketType.KOSPI):
        """초기화
        
        Args:
            token (str): 인증 토큰
            stock_code (str): 종목 코드
            market_type (str): 시장 구분 (KOSPI/KOSDAQ)
        """
        self.logger = setup_logger(__name__)
        self.token = token
        self.stock_code = stock_code
        self.market_type = market_type
        self.ws_manager: Optional[WebSocketManager] = None
        self.ws_handler: Optional[DefaultWebSocketHandler] = None
        self.state = WebSocketState.DISCONNECTED
        self.ccld_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.current_data: Optional[CCLDData] = None
        
        # 웹소켓 설정
        self.ws_config: WebSocketConfig = {
            "url": LS_WS_URL,
            "token": token,
            "max_subscriptions": 1,  # 단일 종목만 구독
            "max_reconnect_attempts": 5,
            "reconnect_delay": 5,
            "ping_interval": 30,
            "ping_timeout": 10,
            "connect_timeout": 30
        }
        
    async def start(self) -> None:
        """모니터링 시작"""
        try:
            # 웹소켓 핸들러 초기화
            if not self.ws_handler:
                self.ws_handler = DefaultWebSocketHandler()
                tr_code = "S3_" if self.market_type == MarketType.KOSPI else "K3_"
                self.ws_handler.register_handler(tr_code, self._handle_ccld_message)
            
            # 웹소켓 매니저가 이미 설정되어 있으면 재사용
            if self.ws_manager and self.ws_manager.is_connected():
                self.logger.info("기존 웹소켓 매니저를 재사용합니다.")
                await self._subscribe()
                self.state = WebSocketState.CONNECTED
                self.logger.info(f"체결 모니터링 시작 - 종목: {self.stock_code}")
                return
            
            # 웹소켓 매니저가 없으면 새로 생성
            if not self.ws_manager:
                self.ws_manager = WebSocketManager(self.ws_config)
                # 에러, 종료, 연결 이벤트만 핸들러로 등록
                self.ws_manager.add_event_handler("error", self._handle_error)
                self.ws_manager.add_event_handler("close", self._handle_close)
                self.ws_manager.add_event_handler("open", self._handle_open)
                # 메시지는 콜백으로만 처리 - 코스피, 코스닥 모두 등록
                self.ws_manager.add_callback(self._handle_ccld_message, "S3_")  # 코스피 체결 메시지
                self.ws_manager.add_callback(self._handle_ccld_message, "K3_")  # 코스닥 체결 메시지
                await self.ws_manager.start()
            
            # 종목 구독 시작
            await self._subscribe()
            
            self.state = WebSocketState.CONNECTED
            self.logger.info(f"체결 모니터링 시작 - 종목: {self.stock_code}")
            
        except Exception as e:
            self.state = WebSocketState.ERROR
            self.logger.error(f"체결 모니터링 시작 중 오류 발생: {str(e)}")
            await self.stop()
            raise
            
    async def stop(self) -> None:
        """모니터링 중지"""
        try:
            if self.state == WebSocketState.DISCONNECTED:
                return
                
            self.state = WebSocketState.CLOSING
            
            # 종목 구독 해제
            if self.ws_manager and self.ws_manager.is_connected():
                try:
                    await self._unsubscribe()
                except Exception as e:
                    self.logger.warning(f"종목 구독 해제 중 오류 발생: {str(e)}")
            
            # 웹소켓 매니저는 공유 자원이므로 종료하지 않음
            self.state = WebSocketState.DISCONNECTED
            
            # 자원 정리
            self.ccld_callbacks.clear()
            self.current_data = None
            
            self.logger.info(f"체결 모니터링 중지 - 종목: {self.stock_code}")
            
        except Exception as e:
            self.logger.error(f"체결 모니터링 중지 중 오류 발생: {str(e)}")
            self.state = WebSocketState.ERROR
            raise
            
    async def _subscribe(self) -> None:
        """종목 구독"""
        if not self.ws_manager or not self.ws_manager.is_connected():
            raise RuntimeError("웹소켓이 연결되지 않았습니다.")
            
        tr_code = "S3_" if self.market_type == MarketType.KOSPI else "K3_"
        await self.ws_manager.subscribe(
            tr_code=tr_code,
            tr_key=self.stock_code,
            callback=self._handle_ccld_message
        )
        
    async def _unsubscribe(self) -> None:
        """종목 구독 해제"""
        if not self.ws_manager or not self.ws_manager.is_connected():
            return
            
        tr_code = "S3_" if self.market_type == MarketType.KOSPI else "K3_"
        await self.ws_manager.unsubscribe(
            tr_code=tr_code,
            tr_key=self.stock_code
        )
        
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 등록"""
        if callback not in self.ccld_callbacks:
            self.ccld_callbacks.append(callback)
            
    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 제거"""
        if callback in self.ccld_callbacks:
            self.ccld_callbacks.remove(callback)
            
    async def _handle_ccld_message(self, message: Dict[str, Any]) -> None:
        """체결 메시지 처리"""
        try:
            # 메시지 타입 확인
            header = message.get("header", {})
            body = message.get("body", {})
            
            # 체결 메시지가 아닌 경우 무시
            tr_cd = header.get("tr_cd", "") or body.get("tr_cd", "")
            if not (tr_cd.startswith("S3_") or tr_cd.startswith("K3_")):
                return
                
            self.logger.debug(f"체결 메시지 처리: {message}")
            
            # 콜백이 있는 경우 전체 메시지를 전달
            if self.ccld_callbacks:
                for callback in self.ccld_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)
                    except Exception as e:
                        self.logger.error(f"콜백 함수 실행 중 오류: {str(e)}")
                return
                
            # 콜백이 없는 경우 메시지 출력
            self.logger.info(f"체결 메시지 수신: {json.dumps(message, ensure_ascii=False)}")
            
            # 응답 메시지 처리
            if "rsp_cd" in header:
                rsp_msg = header.get("rsp_msg", "알 수 없는 메시지")
                if header["rsp_cd"] == "00000":
                    self.logger.info(f"체결 응답: {rsp_msg}")
                else:
                    self.logger.error(f"체결 구독 오류: {rsp_msg}")
                return
                
            # body가 None인 경우 무시
            if not body or not isinstance(body, dict):
                return
                
            # 체결 데이터 처리 및 로깅
            ccld_data = CCLDData(body)
            if ccld_data.shcode == self.stock_code:  # 해당 종목의 데이터만 처리
                self.current_data = ccld_data
                self.logger.info(self._format_ccld_message(ccld_data))
                    
        except Exception as e:
            self.logger.error(f"체결 메시지 처리 중 오류: {str(e)}\n{traceback.format_exc()}")
            
    def _format_ccld_message(self, data: CCLDData) -> str:
        """체결 메시지 포맷팅"""
        try:
            return (
                f"[{data.chetime[:2]}:{data.chetime[2:4]}:{data.chetime[4:]}] "
                f"종목: {data.shcode} ({data.exchname}), "
                f"현재가: {data.price} ({data.sign}{data.change}, {data.drate}%), "
                f"체결량: {data.cvolume} ({data.cgubun}), "
                f"누적거래량: {data.volume}, "
                f"체결강도: {data.cpower}%, "
                f"매도호가: {data.offerho}, 매수호가: {data.bidho}"
            )
        except Exception as e:
            self.logger.error(f"메시지 포맷팅 중 오류: {str(e)}")
            return f"[{datetime.now()}] 메시지 포맷팅 오류"
            
    async def _handle_error(self, error: Exception) -> None:
        """에러 처리"""
        self.logger.error(f"체결 모니터링 중 에러 발생: {str(error)}")
        self.state = WebSocketState.ERROR
        
    async def _handle_close(self, data: Dict[str, Any]) -> None:
        """연결 종료 처리"""
        code = data.get("code")
        message = data.get("message")
        self.logger.warning(f"체결 모니터링 연결 종료 (코드: {code}, 메시지: {message})")
        
        if self.state not in [WebSocketState.CLOSING, WebSocketState.DISCONNECTED]:
            self.state = WebSocketState.DISCONNECTED
            await self.start()  # 자동 재연결
            
    async def _handle_open(self, _: Any) -> None:
        """연결 시작 처리"""
        self.logger.info("체결 모니터링 연결이 열렸습니다.")
        
    def get_current_data(self) -> Optional[Dict[str, Any]]:
        """현재 체결 데이터 반환"""
        return self.current_data.to_dict() if self.current_data else None 