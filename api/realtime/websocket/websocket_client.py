"""웹소켓 클라이언트"""

import json
import websocket
import asyncio
from typing import Dict, Any, Optional, Callable, List, Tuple
from datetime import datetime
import threading
from functools import partial
import ssl
import time
import traceback

from .websocket_base import BaseWebSocket, WebSocketState, WebSocketConfig, WebSocketMessage, DEFAULT_CONFIG
from api.errors import WebSocketError
from config.logging_config import setup_logger
from config.settings import WS_DEBUG_MODE

class MessageQueue:
    """메시지 큐 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.queue = asyncio.Queue()
        self.processing = False
        self.is_running = True
        self.processor_task = None
        self.message_count = 0
        self.error_count = 0
        
    async def add(self, message: str) -> None:
        """메시지 추가"""
        self.message_count += 1
        self.logger.debug(f"메시지 큐에 추가 (총 {self.message_count}개): {message[:200]}...")
        await self.queue.put(message)
        if not self.processing:
            self.processor_task = asyncio.create_task(self._process())
            
    async def _process(self) -> None:
        """메시지 처리"""
        self.processing = True
        try:
            while self.is_running:
                try:
                    if self.queue.empty():
                        await asyncio.sleep(0.1)
                        continue
                        
                    message = await self.queue.get()
                    if message is None:
                        self.logger.debug("메시지 큐 종료 시그널 수신")
                        break
                        
                    self.logger.debug(f"메시지 처리 시작: {message[:200]}...")
                    if hasattr(self, 'callback') and self.callback:
                        await self.callback(message)
                        self.logger.debug("메시지 처리 완료")
                        
                    self.queue.task_done()
                    
                except asyncio.CancelledError:
                    self.logger.debug("메시지 처리 태스크 취소됨")
                    break
                except Exception as e:
                    self.error_count += 1
                    self.logger.error(f"메시지 처리 중 오류 ({self.error_count}번째): {str(e)}\n{traceback.format_exc()}")
                    
        finally:
            self.processing = False
            self.logger.debug(f"메시지 큐 처리 종료 (처리: {self.message_count}개, 오류: {self.error_count}개)")
            
    def set_callback(self, callback: Callable[[str], None]) -> None:
        """콜백 함수 설정"""
        self.callback = callback
            
    async def stop(self) -> None:
        """메시지 큐 중지"""
        self.logger.debug("메시지 큐 중지 시작")
        self.is_running = False
        await self.queue.put(None)  # 종료 시그널
        
        if self.processor_task:
            try:
                await self.processor_task
                self.logger.debug("메시지 처리 태스크 정상 종료")
            except asyncio.CancelledError:
                self.logger.debug("메시지 처리 태스크 강제 종료")
            
        # 남은 메시지 제거
        remaining = 0
        while not self.queue.empty():
            try:
                await self.queue.get()
                self.queue.task_done()
                remaining += 1
            except Exception as e:
                self.logger.error(f"메시지 큐 정리 중 오류: {str(e)}\n{traceback.format_exc()}")
        if remaining > 0:
            self.logger.debug(f"미처리 메시지 {remaining}개 제거됨")

class WebSocketClient(BaseWebSocket):
    """웹소켓 클라이언트 클래스"""
    
    def __init__(self, url: str, token: str):
        """초기화"""
        super().__init__({
            "url": url,
            "token": token
        })
        self.logger = setup_logger(__name__)
        self.ws = None
        self.is_connected = False
        self.state = WebSocketState.CLOSED
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.message_queue = MessageQueue()
        self.message_queue.set_callback(self._send_message)
        self.thread = None
        self.event_loop = None
        self.connection_attempts = 0
        self.last_error = None
        self.last_state_change = datetime.now()
        self.message_stats = {
            "sent": 0,
            "received": 0,
            "errors": 0
        }
        
    def _log_state_change(self, new_state: WebSocketState) -> None:
        """상태 변경 로깅"""
        old_state = self.state
        self.state = new_state
        current_time = datetime.now()
        duration = (current_time - self.last_state_change).total_seconds()
        self.last_state_change = current_time
        self.logger.info(
            f"웹소켓 상태 변경: {old_state.name} -> {new_state.name} "
            f"(지속시간: {duration:.1f}초)"
        )
        
    async def _send_message(self, message: str) -> None:
        """메시지 전송"""
        if self.ws and self.is_connected:
            try:
                self.ws.send(message)
                self.message_stats["sent"] += 1
                self.logger.debug(f"메시지 전송 완료 (총 {self.message_stats['sent']}개): {message[:200]}...")
            except Exception as e:
                self.message_stats["errors"] += 1
                self.logger.error(
                    f"메시지 전송 중 오류 (총 {self.message_stats['errors']}개): {str(e)}\n"
                    f"메시지: {message[:200]}...\n"
                    f"{traceback.format_exc()}"
                )
        
    def set_event_handlers(self, handlers: Dict[str, List[Callable]]) -> None:
        """이벤트 핸들러 설정"""
        self.event_handlers = handlers
        self.logger.debug(f"이벤트 핸들러 등록: {list(handlers.keys())}")
        
    async def connect(self) -> None:
        """웹소켓 연결"""
        try:
            if self.is_connected:
                self.logger.warning("이미 연결된 상태입니다.")
                return
                
            self.connection_attempts += 1
            self.logger.info(f"웹소켓 연결 시작 (시도 {self.connection_attempts}번째)...")
            self._log_state_change(WebSocketState.CONNECTING)
            
            # 이벤트 루프 설정
            self.event_loop = asyncio.get_running_loop()
            
            # SSL 설정
            ssl_options = {
                "cert_reqs": ssl.CERT_NONE,
                "check_hostname": False,
                "ssl_version": ssl.PROTOCOL_TLSv1_2
            }
            
            # 헤더 설정
            headers = {
                "Authorization": f"Bearer {self.config['token']}",
                "Content-Type": "application/json"
            }
            
            self.logger.debug(f"연결 설정:\nURL: {self.config['url']}\nHeaders: {headers}\nSSL: {ssl_options}")
            
            # 웹소켓 설정
            websocket.enableTrace(WS_DEBUG_MODE)
            
            # 웹소켓 객체 생성
            self.ws = websocket.WebSocketApp(
                url=self.config["url"],
                header=headers,
                on_message=self._handle_message_wrapper,
                on_error=self._handle_error_wrapper,
                on_close=self._handle_close_wrapper,
                on_open=self._handle_open_wrapper,
                on_ping=self._handle_ping,
                on_pong=self._handle_pong
            )
            
            # 웹소켓 스레드 시작
            self.thread = threading.Thread(
                target=self._run_websocket,
                kwargs={
                    "sslopt": ssl_options,
                    "ping_interval": self.config.get("ping_interval", 30),
                    "ping_timeout": self.config.get("ping_timeout", 10)
                }
            )
            self.thread.daemon = True
            self.thread.start()
            
            # 연결 대기
            timeout = self.config.get("connect_timeout", 30)
            start_time = time.time()
            
            while not self.is_connected and (time.time() - start_time) < timeout:
                if self.state == WebSocketState.ERROR:
                    error_msg = getattr(self.ws, 'last_error', "알 수 없는 오류")
                    raise WebSocketError(f"웹소켓 연결 중 오류 발생: {error_msg}")
                await asyncio.sleep(0.1)
                
            if not self.is_connected:
                raise WebSocketError(f"웹소켓 연결 시간 초과 (timeout: {timeout}초)")
                
            self.logger.info("웹소켓 연결 성공")
            
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(
                f"웹소켓 연결 중 오류 (시도 {self.connection_attempts}번째): {str(e)}\n"
                f"{traceback.format_exc()}"
            )
            self._log_state_change(WebSocketState.ERROR)
            await self.close()
            raise
            
    def _run_websocket(self, **kwargs) -> None:
        """웹소켓 실행"""
        try:
            self.logger.debug(f"웹소켓 실행 시작 (설정: {kwargs})")
            self.ws.run_forever(**kwargs)
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"웹소켓 실행 중 오류: {str(e)}\n{traceback.format_exc()}")
            self._log_state_change(WebSocketState.ERROR)
            
    def _handle_message_wrapper(self, ws: websocket.WebSocketApp, message: str) -> None:
        """메시지 수신 처리"""
        try:
            if not message:
                self.logger.warning("빈 메시지가 수신되었습니다.")
                return
                
            self.message_stats["received"] += 1
            self.logger.debug(f"메시지 수신 (총 {self.message_stats['received']}개): {message[:200]}...")
            
            try:
                data = json.loads(message)
            except json.JSONDecodeError as e:
                self.message_stats["errors"] += 1
                self.logger.error(
                    f"JSON 파싱 오류 (총 {self.message_stats['errors']}개): {str(e)}\n"
                    f"메시지: {message[:200]}...\n"
                    f"{traceback.format_exc()}"
                )
                return
                
            if not isinstance(data, dict):
                self.message_stats["errors"] += 1
                self.logger.error(f"잘못된 메시지 형식: dictionary가 아님 (타입: {type(data)})")
                return
                
            # 응답 코드 확인
            header = data.get("header")
            if header is not None:
                rsp_cd = header.get("rsp_cd")
                if rsp_cd is not None and rsp_cd != "00000":
                    self.message_stats["errors"] += 1
                    self.logger.error(
                        f"서버 응답 오류 (코드: {rsp_cd}, "
                        f"메시지: {header.get('rsp_msg', '알 수 없는 오류')}, "
                        f"총 오류: {self.message_stats['errors']}개)"
                    )
                    return
                    
            # 이벤트 핸들러 실행
            handlers = self.event_handlers.get("message", [])
            if not handlers:
                self.logger.debug("등록된 메시지 핸들러가 없습니다.")
                return
                
            for handler in handlers:
                if handler is None:
                    continue
                    
                try:
                    if asyncio.iscoroutinefunction(handler):
                        if self.event_loop is None:
                            self.logger.error("이벤트 루프가 설정되지 않았습니다.")
                            continue
                        asyncio.run_coroutine_threadsafe(handler(data), self.event_loop)
                    else:
                        handler(data)
                except Exception as e:
                    self.message_stats["errors"] += 1
                    self.logger.error(
                        f"메시지 핸들러 실행 중 오류 (총 {self.message_stats['errors']}개): "
                        f"{str(e)}\n"
                        f"핸들러: {handler.__name__ if hasattr(handler, '__name__') else str(handler)}\n"
                        f"{traceback.format_exc()}"
                    )
                    
        except Exception as e:
            self.message_stats["errors"] += 1
            self.logger.error(
                f"메시지 처리 중 오류 (총 {self.message_stats['errors']}개): {str(e)}\n"
                f"메시지: {message[:200] if message else 'None'}\n"
                f"{traceback.format_exc()}"
            )
            
    def _handle_error_wrapper(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """에러 처리"""
        try:
            self.last_error = str(error)
            self._log_state_change(WebSocketState.ERROR)
            self.is_connected = False
            
            error_info = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc()
            }
            
            self.logger.error(
                f"웹소켓 에러 발생:\n"
                f"타입: {error_info['error_type']}\n"
                f"메시지: {error_info['error_message']}\n"
                f"스택트레이스:\n{error_info['traceback']}"
            )
            
            for handler in self.event_handlers.get("error", []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.run_coroutine_threadsafe(handler(error_info), self.event_loop)
                    else:
                        handler(error_info)
                except Exception as e:
                    self.logger.error(f"에러 핸들러 실행 중 오류: {str(e)}\n{traceback.format_exc()}")
                    
        except Exception as e:
            self.logger.error(f"에러 처리 중 오류: {str(e)}\n{traceback.format_exc()}")
            
    def _handle_close_wrapper(self, ws: websocket.WebSocketApp, 
                            close_status_code: int, close_msg: str) -> None:
        """연결 종료 처리"""
        try:
            self.is_connected = False
            self._log_state_change(WebSocketState.CLOSED)
            
            close_info = {
                "code": close_status_code,
                "message": close_msg,
                "stats": self.message_stats
            }
            
            self.logger.info(
                f"웹소켓 연결 종료:\n"
                f"상태 코드: {close_status_code}\n"
                f"메시지: {close_msg}\n"
                f"통계:\n"
                f"- 전송: {self.message_stats['sent']}개\n"
                f"- 수신: {self.message_stats['received']}개\n"
                f"- 오류: {self.message_stats['errors']}개"
            )
            
            for handler in self.event_handlers.get("close", []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.run_coroutine_threadsafe(handler(close_info), self.event_loop)
                    else:
                        handler(close_info)
                except Exception as e:
                    self.logger.error(f"종료 핸들러 실행 중 오류: {str(e)}\n{traceback.format_exc()}")
                    
        except Exception as e:
            self.logger.error(f"연결 종료 처리 중 오류: {str(e)}\n{traceback.format_exc()}")
            
    def _handle_open_wrapper(self, ws: websocket.WebSocketApp) -> None:
        """연결 성공 처리"""
        try:
            self.is_connected = True
            self._log_state_change(WebSocketState.CONNECTED)
            
            self.logger.info(f"웹소켓 연결 성공 (시도 {self.connection_attempts}번째), URL: {self.config['url']}")
            
            for handler in self.event_handlers.get("open", []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.run_coroutine_threadsafe(handler(None), self.event_loop)
                    else:
                        handler(None)
                except Exception as e:
                    self.logger.error(f"연결 성공 핸들러 실행 중 오류: {str(e)}\n{traceback.format_exc()}")
                    
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"연결 성공 처리 중 오류: {str(e)}\n{traceback.format_exc()}")
            self._log_state_change(WebSocketState.ERROR)
            
    def _handle_ping(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Ping 메시지 처리"""
        try:
            self.logger.debug(f"Ping 수신: {message}")
            ws.send(message)
        except Exception as e:
            self.logger.error(f"Ping 처리 중 오류: {str(e)}\n{traceback.format_exc()}")
            
    def _handle_pong(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Pong 메시지 처리"""
        self.logger.debug(f"Pong 수신: {message}")
        
    async def send(self, data: Dict[str, Any]) -> None:
        """데이터 전송"""
        try:
            if not self.is_connected:
                raise WebSocketError("웹소켓이 연결되지 않았습니다.")
                
            message = json.dumps(data)
            self.logger.debug(f"메시지 전송 요청: {message[:200]}...")
            await self.message_queue.add(message)
            
        except Exception as e:
            self.message_stats["errors"] += 1
            self.logger.error(
                f"메시지 전송 중 오류 (총 {self.message_stats['errors']}개): {str(e)}\n"
                f"데이터: {data}\n"
                f"{traceback.format_exc()}"
            )
            raise
            
    async def close(self) -> None:
        """웹소켓 연결 종료"""
        try:
            if self.state == WebSocketState.CLOSED:
                return
                
            self._log_state_change(WebSocketState.CLOSING)
            
            # 메시지 큐 중지
            if self.message_queue:
                await self.message_queue.stop()
                
            # 웹소켓 연결 종료
            if self.ws:
                self.ws.close()
                
            # 스레드 종료 대기
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5.0)
                
            self.logger.info(
                f"웹소켓 연결 종료 완료\n"
                f"통계:\n"
                f"- 연결 시도: {self.connection_attempts}번\n"
                f"- 전송: {self.message_stats['sent']}개\n"
                f"- 수신: {self.message_stats['received']}개\n"
                f"- 오류: {self.message_stats['errors']}개\n"
                f"마지막 오류: {self.last_error or '없음'}"
            )
            
        except Exception as e:
            self.logger.error(f"웹소켓 종료 중 오류: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.ws = None
            self.is_connected = False
            self._log_state_change(WebSocketState.CLOSED)
            self.event_handlers.clear()
            self.thread = None 