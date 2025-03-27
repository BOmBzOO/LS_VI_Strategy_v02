"""웹소켓 클라이언트"""

import json
import websocket
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import threading
from functools import partial
import ssl
import time

from .websocket_base import BaseWebSocket, WebSocketState, WebSocketConfig, WebSocketMessage, DEFAULT_CONFIG
from api.errors import WebSocketError
from config.logging_config import setup_logger

class MessageQueue:
    """메시지 큐 관리 클래스"""
    
    def __init__(self, ws_client: 'WebSocketClient'):
        self.queue = asyncio.PriorityQueue()
        self.processing = False
        self.ws_client = ws_client
        
    async def add(self, priority: int, message: str) -> None:
        """메시지 추가
        
        Args:
            priority (int): 우선순위
            message (str): 메시지
        """
        await self.queue.put((priority, message))
        if not self.processing:
            asyncio.create_task(self._process())
            
    async def _process(self) -> None:
        """메시지 처리"""
        self.processing = True
        try:
            while not self.queue.empty():
                _, message = await self.queue.get()
                if self.ws_client.ws and self.ws_client.is_connected:
                    self.ws_client.ws.send(message)
                self.queue.task_done()
        finally:
            self.processing = False

class EventLoopManager:
    """이벤트 루프 관리 클래스"""
    
    def __init__(self):
        self.loop = None
        self.tasks = set()
        
    def get_loop(self) -> asyncio.AbstractEventLoop:
        """이벤트 루프 반환"""
        if self.loop is None:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        return self.loop
        
    async def create_task(self, coro) -> asyncio.Task:
        """태스크 생성
        
        Args:
            coro: 코루틴
            
        Returns:
            asyncio.Task: 생성된 태스크
        """
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

class WebSocketClient(BaseWebSocket):
    """웹소켓 클라이언트 클래스"""
    
    def __init__(self, url: str, token: str):
        """초기화

        Args:
            url (str): 웹소켓 URL
            token (str): 인증 토큰
        """
        self.logger = setup_logger(__name__)
        
        # 기본 설정에 URL과 토큰 추가
        self.config = DEFAULT_CONFIG.copy()
        self.config.update({
            "url": url,
            "token": token
        })
        
        self.ws = None
        self.is_connected = False
        # self.state = WebSocketState.CLOSED
        self.state = None
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.thread = None
        self.is_running = False
        
        # 메시지 큐와 이벤트 루프 관리자 초기화
        self.message_queue = MessageQueue(self)
        self.event_loop_manager = EventLoopManager()
        
    async def connect(self) -> None:
        """웹소켓 연결"""
        try:
            self.state = WebSocketState.CONNECTING
            self.logger.info(f"웹소켓 연결 시도 중... URL: {self.config['url']}")
            
            # SSL 검증 비활성화
            websocket.enableTrace(True)  # 디버깅을 위해 활성화
            
            # 헤더 설정
            headers = {
                "Authorization": f"Bearer {self.config['token']}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            
            # SSL 옵션 설정
            ssl_opts = {
                "cert_reqs": ssl.CERT_NONE,
                "check_hostname": False,
                "ssl_version": ssl.PROTOCOL_TLSv1_2
            }
            
            # 웹소켓 옵션 설정
            websocket.setdefaulttimeout(30)
            
            # 기존 연결이 있다면 정리
            if self.ws:
                self.ws.close()
                self.ws = None
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
                self.thread = None
            
            # 상태 초기화
            self.is_connected = False
            self.state = WebSocketState.CONNECTING
            
            self.ws = websocket.WebSocketApp(
                self.config["url"],
                header=headers,
                on_message=self._handle_message_wrapper,
                on_error=self._handle_error_wrapper,
                on_close=self._handle_close_wrapper,
                on_open=self._handle_open_wrapper,
                on_ping=self._handle_ping,
                on_pong=self._handle_pong
            )
            
            # 웹소켓 연결 시작
            self.thread = threading.Thread(
                target=lambda: self.ws.run_forever(
                    sslopt=ssl_opts,
                    ping_interval=20,
                    ping_timeout=10
                )
            )
            self.thread.daemon = True
            self.thread.start()
            
            # 연결될 때까지 대기
            timeout = 30  # 30초 타임아웃
            start_time = time.time()
            
            while not self.is_connected and self.state != WebSocketState.ERROR:
                if time.time() - start_time > timeout:
                    self.logger.error("웹소켓 연결 타임아웃")
                    raise Exception("웹소켓 연결 타임아웃")
                await asyncio.sleep(0.1)
            
            if self.state == WebSocketState.ERROR:
                self.logger.error("웹소켓 연결 실패")
                raise Exception("웹소켓 연결 실패")
            
            self.state = WebSocketState.CONNECTED
            self.logger.info("웹소켓이 연결되었습니다.")
            
        except Exception as e:
            self.state = WebSocketState.ERROR
            self.is_connected = False
            self.logger.error(f"웹소켓 연결 중 오류: {str(e)}")
            raise

    def _handle_message_wrapper(self, ws: websocket.WebSocketApp, message: str) -> None:
        """웹소켓 메시지 수신 핸들러"""
        try:
            data = json.loads(message)
            for handler in self.event_handlers.get("message", []):
                asyncio.create_task(handler(data))
        except Exception as e:
            self.logger.error(f"메시지 처리 중 오류: {str(e)}")

    def _handle_ping(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Ping 메시지 처리"""
        try:
            ws.send(message)
        except Exception as e:
            self.logger.error(f"Ping 처리 중 오류: {str(e)}")

    def _handle_pong(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Pong 메시지 처리"""
        try:
            self.logger.debug("Pong 메시지 수신")
        except Exception as e:
            self.logger.error(f"Pong 처리 중 오류: {str(e)}")

    def _handle_error_wrapper(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """웹소켓 에러 핸들러"""
        self.state = WebSocketState.ERROR
        self.is_connected = False
        self.logger.error(f"웹소켓 에러: {str(error)}")
        for handler in self.event_handlers.get("error", []):
            asyncio.create_task(handler({"error": str(error)}))

    def _handle_close_wrapper(self, ws: websocket.WebSocketApp, 
                            close_status_code: int, close_msg: str) -> None:
        """웹소켓 연결 종료 핸들러"""
        try:
            self.is_connected = False
            self.state = WebSocketState.CLOSED
            self.logger.info(f"웹소켓 연결이 종료되었습니다. (코드: {close_status_code}, 메시지: {close_msg})")
            
            # 연결 종료 이벤트 발생
            for handler in self.event_handlers.get("close", []):
                asyncio.create_task(handler({
                    "code": close_status_code,
                    "message": close_msg
                }))
        except Exception as e:
            self.logger.error(f"연결 종료 핸들러 처리 중 오류: {str(e)}")

    def _handle_open_wrapper(self, ws: websocket.WebSocketApp) -> None:
        """웹소켓 연결 성공 핸들러"""
        try:
            self.is_connected = True
            self.state = WebSocketState.CONNECTED
            self.logger.info("웹소켓 연결이 열렸습니다.")
            
            # 연결 성공 이벤트 발생
            for handler in self.event_handlers.get("open", []):
                asyncio.create_task(handler(None))
        except Exception as e:
            self.logger.error(f"연결 성공 핸들러 처리 중 오류: {str(e)}")
            
    async def send(self, data: Dict[str, Any], priority: int = 1) -> None:
        """데이터 전송
        
        Args:
            data (Dict[str, Any]): 전송할 데이터
            priority (int, optional): 우선순위. Defaults to 1.
        """
        try:
            if not self.is_connected:
                raise WebSocketError("웹소켓이 연결되지 않았습니다.")
            
            message = json.dumps(data)
            await self.message_queue.add(priority, message)
            
        except Exception as e:
            self.logger.error(f"메시지 전송 중 오류 발생: {str(e)}")
            raise
            
    async def _handle_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """메시지 수신 처리"""
        try:
            data = json.loads(message)
            await self.emit_event("message", data)
        except Exception as e:
            self.logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
            
    async def _handle_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """에러 처리"""
        self.state = WebSocketState.ERROR
        self.logger.error(f"웹소켓 에러: {str(error)}")
        await self.emit_event("error", {"error": str(error)})
            
    async def _handle_close(self, ws: websocket.WebSocketApp, 
                          close_status_code: int, close_msg: str) -> None:
        """연결 종료 처리"""
        self.state = WebSocketState.CLOSED
        self.is_connected = False
        self.logger.info("웹소켓 연결이 종료되었습니다.")
        await self.emit_event("close", {
            "code": close_status_code,
            "message": close_msg
        })
            
    async def _handle_open(self, ws: websocket.WebSocketApp) -> None:
        """연결 시작 처리"""
        self.state = WebSocketState.CONNECTED
        self.is_connected = True
        self.logger.info("웹소켓 연결이 열렸습니다.")
            
    async def close(self) -> None:
        """연결 종료"""
        try:
            if self.ws:
                self.state = WebSocketState.CLOSED
                self.is_connected = False
                self.ws.close()
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
        except Exception as e:
            self.logger.error(f"웹소켓 종료 중 오류: {str(e)}")
            raise

    def set_token(self, token: str) -> None:
        """토큰 설정
        
        Args:
            token (str): 인증 토큰
        """
        self.config['token'] = token 