"""웹소켓 연결 관리"""

import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import pytz
import time
import traceback
from api.realtime.websocket.websocket_client import WebSocketClient
from api.errors import WebSocketError
from config.settings import WS_RECONNECT_INTERVAL, WS_MAX_RECONNECT_ATTEMPTS
from config.logging_config import setup_logger
from api.realtime.websocket.websocket_base import BaseWebSocket, WebSocketState, WebSocketConfig, WebSocketMessage

class CacheManager:
    """캐시 관리 클래스"""
    
    def __init__(self, max_size: int, expiry: int):
        """초기화
        
        Args:
            max_size (int): 최대 캐시 크기
            expiry (int): 캐시 만료 시간 (초)
        """
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.max_size = max_size
        self.expiry = expiry
        
    def get(self, key: str) -> Optional[Any]:
        """캐시 데이터 조회
        
        Args:
            key (str): 캐시 키
            
        Returns:
            Optional[Any]: 캐시 데이터
        """
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.expiry:
                return data
            del self.cache[key]
        return None
        
    def set(self, key: str, value: Any) -> None:
        """캐시 데이터 저장
        
        Args:
            key (str): 캐시 키
            value (Any): 저장할 데이터
        """
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
            del self.cache[oldest_key]
        self.cache[key] = (value, time.time())
        
    def clear(self) -> None:
        """캐시 초기화"""
        self.cache.clear()

class WebSocketManager(BaseWebSocket):
    """웹소켓 연결 관리 클래스"""
    
    def __init__(self, config: WebSocketConfig):
        """초기화
        
        Args:
            config (WebSocketConfig): 웹소켓 설정
        """
        super().__init__(config)
        self.client: Optional[WebSocketClient] = None
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.logger = setup_logger(__name__)
        self.kst = pytz.timezone('Asia/Seoul')
        self.event_queue = asyncio.Queue()  # 이벤트 큐 추가
        
        # 캐시 관리자 초기화
        self.cache_manager = CacheManager(
            max_size=config.get("max_cache_size", 1000),
            expiry=config.get("cache_expiry", 60)
        )
        
        # 이벤트 처리 태스크 시작
        asyncio.create_task(self._process_events())

    async def _process_events(self) -> None:
        """이벤트 큐 처리"""
        while True:
            try:
                event_type, data = await self.event_queue.get()
                if event_type == "connected":
                    self.update_state(WebSocketState.CONNECTED)
                    self.logger.info("웹소켓 연결이 성공적으로 이루어졌습니다.")
                    await self.emit_event("connected", data)
                elif event_type == "message":
                    header = data.get("header", {})
                    tr_code = header.get("tr_cd")
                    
                    # body가 None인 경우 빈 딕셔너리로 처리
                    body = data.get("body", {}) if data.get("body") is not None else {}
                    tr_key = body.get("tr_key", "")
                    
                    subscription_key = f"{tr_code}_{tr_key}"
                    if subscription_key in self.subscriptions:
                        callback = self.subscriptions[subscription_key]["callback"]
                        # 원본 메시지를 그대로 전달
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                elif event_type == "error":
                    self.logger.error(f"웹소켓 에러 발생: {str(data)}")
                    self.update_state(WebSocketState.ERROR)
                    await self._connect()
                elif event_type == "close":
                    code = data.get("code")
                    message = data.get("message")
                    self.logger.warning(f"웹소켓 연결 종료 (코드: {code}, 메시지: {message})")
                    self.update_state(WebSocketState.DISCONNECTED)
                    await self._connect()
            except Exception as e:
                self.logger.error(f"이벤트 처리 중 오류: {str(e)}")
            finally:
                self.event_queue.task_done()

    def is_connected(self) -> bool:
        """웹소켓 연결 상태 확인
        
        Returns:
            bool: 연결 여부
        """
        return (self.client and 
                self.client.ws and 
                self.client.ws.sock and 
                self.client.ws.sock.connected and 
                self.state == WebSocketState.CONNECTED)

    async def start(self) -> None:
        """웹소켓 연결 시작"""
        try:
            self.logger.info("웹소켓 매니저 시작 중...")
            
            # 기존 연결 정리
            if self.client:
                await self.close()

            # WebSocketClient 초기화
            self.client = WebSocketClient(
                url=self.config["url"],
                token=self.config["token"]
            )
            
            # 추가 설정 적용
            self.client.config.update({
                "max_subscriptions": self.config.get("max_subscriptions", 100),
                "max_reconnect_attempts": self.config.get("max_reconnect_attempts", 5),
                "reconnect_delay": self.config.get("reconnect_delay", 5),
                "ping_interval": self.config.get("ping_interval", 30),
                "ping_timeout": self.config.get("ping_timeout", 10)
            })
            
            # 이벤트 핸들러 등록
            self.client.add_event_handler("message", self._handle_message)
            self.client.add_event_handler("error", self._handle_error)
            self.client.add_event_handler("close", self._handle_close)
            self.client.add_event_handler("open", self._handle_open)
            
            # 연결 시작
            self.logger.info("웹소켓 클라이언트 연결 시도 중...")
            await self._connect()
            
        except Exception as e:
            self.logger.error(f"웹소켓 연결 시작 중 오류 발생: {str(e)}")
            raise

    async def _connect(self) -> None:
        """웹소켓 연결"""
        try:
            self.logger.info("웹소켓 연결 시도 중...")
            await self.client.connect()
            
            # 연결 상태 확인
            if not self.client.is_connected:
                self.logger.error("웹소켓 연결 실패")
                raise Exception("웹소켓 연결 실패")
                
            self.logger.info("웹소켓 연결 성공")
            
        except Exception as e:
            self.logger.error(f"웹소켓 연결 중 오류 발생: {str(e)}")
            raise

    async def _handle_open(self, _: Any) -> None:
        try:
            self.update_state(WebSocketState.CONNECTED)
            await self.event_queue.put(("connected", None))
            
        except Exception as e:
            self.logger.error(f"연결 시작 처리 중 오류 (line {traceback.extract_tb(e.__traceback__)[-1].lineno}): {str(e)}")

    async def subscribe(self, 
                        tr_code: str, 
                        tr_key: str, 
                        callback: Callable[[Dict[str, Any]], None]) -> None:
        """실시간 데이터 구독
        
        Args:
            tr_code (str): TR 코드
            tr_key (str): TR 키
            callback (Callable[[Dict[str, Any]], None]): 콜백 함수
        """
        if len(self.subscriptions) >= self.config["max_subscriptions"]:
            raise Exception("최대 구독 개수 초과")
            
        subscription_key = f"{tr_code}_{tr_key}"
        
        # 캐시된 구독 정보 확인
        cached_subscription = self.cache_manager.get(subscription_key)
        if cached_subscription:
            self.subscriptions[subscription_key] = cached_subscription
            return
            
        # VI 구독 메시지 형식 수정
        message = {
            "header": {
                "token": self.config["token"],
                "tr_type": "3"  # 실시간 시세 등록
            },
            "body": {
                "tr_cd": tr_code,
                "tr_key": tr_key
            }
        }
        
        subscription_data = {
            "message": message,
            "callback": callback,
            "subscribe_time": self.get_timestamp()
        }
        
        self.subscriptions[subscription_key] = subscription_data
        self.cache_manager.set(subscription_key, subscription_data)
        
        if self.is_connected():
            try:
                await self.client.send(message)
                self.logger.info(f"VI 구독 요청 전송 완료: {tr_code}_{tr_key}")
            except Exception as e:
                self.logger.error(f"VI 구독 요청 전송 실패: {str(e)}")
                raise

    async def unsubscribe(self, tr_code: str, tr_key: str) -> None:
        """실시간 데이터 구독 해제
        
        Args:
            tr_code (str): TR 코드
            tr_key (str): TR 키
        """
        subscription_key = f"{tr_code}_{tr_key}"
        if subscription_key in self.subscriptions:
            message = {
                "header": {
                    "token": self.config["token"],
                    "tr_type": "4"  # 실시간 시세 해제
                },
                "body": {
                    "tr_cd": tr_code,
                    "tr_key": tr_key
                }
            }
            
            if self.is_connected():
                try:
                    await self.client.send(message)
                    self.logger.info(f"VI 구독 해제 요청 전송 완료: {tr_code}_{tr_key}")
                except Exception as e:
                    self.logger.error(f"VI 구독 해제 요청 전송 실패: {str(e)}")
                    raise
                
            del self.subscriptions[subscription_key]

    def _handle_message(self, data: Dict[str, Any]) -> None:
        """수신된 메시지 처리"""
        try:
            # 이벤트 큐에 메시지 이벤트 추가
            asyncio.create_task(self.event_queue.put(("message", data)))
        except Exception as e:
            import traceback
            self.logger.error(f"메시지 처리 중 오류 (line {traceback.extract_tb(e.__traceback__)[-1].lineno}): {str(e)}")

    def _handle_error(self, error: Exception) -> None:
        """에러 발생 시 처리"""
        try:
            # 이벤트 큐에 에러 이벤트 추가
            asyncio.create_task(self.event_queue.put(("error", error)))
        except Exception as e:
            self.logger.error(f"에러 처리 중 오류: {str(e)}")

    def _handle_close(self, data: Dict[str, Any]) -> None:
        """연결 종료 시 처리"""
        try:
            # 이벤트 큐에 종료 이벤트 추가
            asyncio.create_task(self.event_queue.put(("close", data)))
        except Exception as e:
            self.logger.error(f"종료 처리 중 오류: {str(e)}")

    async def close(self) -> None:
        """연결 종료"""
        if self.client:
            await self.client.close()
            self.client = None
            self.subscriptions.clear() 