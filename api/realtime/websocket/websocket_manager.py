"""웹소켓 연결 관리"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import pytz
import time
import traceback
import json
from api.realtime.websocket.websocket_client import WebSocketClient
from api.errors import WebSocketError
from config.settings import WS_RECONNECT_INTERVAL, WS_MAX_RECONNECT_ATTEMPTS
from config.logging_config import setup_logger
from api.realtime.websocket.websocket_base import BaseWebSocket, WebSocketState, WebSocketConfig, WebSocketMessage

class WebSocketManager(BaseWebSocket):
    """웹소켓 연결 관리 클래스"""
    
    def __init__(self, config: WebSocketConfig):
        """초기화
        
        Args:
            config (WebSocketConfig): 웹소켓 설정
        """
        super().__init__(config)
        self.logger = setup_logger(__name__)
        self.client: Optional[WebSocketClient] = None
        self.event_queue = asyncio.Queue()
        self.event_task = None
        self.is_running = False

        # 콜백 함수 관리
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # 구독 관리
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        
        # 이벤트 핸들러
        self.event_handlers = {
            "message": [],
            "error": [],
            "close": [],
            "open": []
        }
        
        self.logger.info("웹소켓 매니저가 초기화되었습니다.")

    async def start(self) -> None:
        """웹소켓 매니저 시작"""
        try:
            if self.is_running:
                self.logger.warning("웹소켓 매니저가 이미 실행 중입니다.")
                return
                
            self.is_running = True
            self.logger.info("웹소켓 매니저 시작 중...")
            
            # 이벤트 처리 태스크 시작
            self.event_task = asyncio.create_task(self._process_events())
            
            # 웹소켓 연결 시작
            await self._connect()
            
        except Exception as e:
            self.is_running = False
            if self.event_task:
                self.event_task.cancel()
            self.logger.error(f"웹소켓 매니저 시작 중 오류: {str(e)}")
            raise

    async def stop(self) -> None:
        """웹소켓 매니저 중지"""
        if not self.is_running:
            return
            
        try:
            self.is_running = False
            
            # 모든 구독 해제
            for tr_code, tr_key in list(self.subscriptions.keys()):
                try:
                    await self.unsubscribe(tr_code, tr_key)
                except Exception as e:
                    self.logger.warning(f"구독 해제 중 오류: {str(e)}")
            
            # 웹소켓 연결 종료
            if self.client:
                await self.client.close()
                self.client = None
            
            # 이벤트 처리 태스크 종료
            if self.event_task:
                self.event_task.cancel()
                try:
                    await self.event_task
                except asyncio.CancelledError:
                    pass
            
            # 이벤트 큐 비우기
            while not self.event_queue.empty():
                try:
                    await self.event_queue.get()
                    self.event_queue.task_done()
                except Exception:
                    break

            self.callbacks.clear()
            self.subscriptions.clear()
                    
            self.logger.info("웹소켓 매니저가 중지되었습니다.")
            
        except Exception as e:
            self.logger.error(f"웹소켓 매니저 중지 중 오류: {str(e)}")
            raise

    async def _connect(self) -> None:
        """웹소켓 연결"""
        try:
            # URL과 토큰 검증
            if not self.config.get("url"):
                raise WebSocketError("웹소켓 URL이 설정되지 않았습니다.")
            if not self.config.get("token"):
                raise WebSocketError("인증 토큰이 설정되지 않았습니다.")
            
            # 기존 연결이 있고 연결된 상태면 재사용
            if self.client and self.client.is_connected:
                self.logger.info("기존 웹소켓 연결을 재사용합니다.")
                return
            
            # 기존 연결이 있지만 연결이 끊어진 경우에만 정리
            if self.client and not self.client.is_connected:
                await self.client.close()
                self.client = None
            
            # 새로운 클라이언트 생성 및 연결
            if not self.client:
                self.client = WebSocketClient(
                    url=self.config["url"],
                    token=self.config["token"]
                )
                
                # 이벤트 핸들러 등록
                self.client.set_event_handlers({
                    "message": [self._handle_message],
                    "error": [self._handle_error],
                    "close": [self._handle_close],
                    "open": [self._handle_open]
                })
                
                # 연결 시작
                await self.client.connect()
            
            # 기존 구독 복구
            for subscription_key, subscription_data in self.subscriptions.items():
                tr_code, tr_key = subscription_key.split("_")
                try:
                    await self.client.send(subscription_data["message"])
                    self.logger.info(f"구독 복구 완료: {subscription_key}")
                except Exception as e:
                    self.logger.error(f"구독 복구 실패: {subscription_key} - {str(e)}")
            
        except Exception as e:
            self.logger.error(f"웹소켓 연결 중 오류: {str(e)}")
            raise

    async def _process_events(self) -> None:
        """이벤트 처리 루프"""
        try:
            while self.is_running:
                try:
                    event_type, data = await self.event_queue.get()
                    handlers = self.event_handlers.get(event_type, [])
                    
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(data)
                            else:
                                handler(data)
                        except Exception as e:
                            self.logger.error(f"이벤트 핸들러 실행 중 오류: {str(e)}")
                    
                    self.event_queue.task_done()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"이벤트 처리 중 오류: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"이벤트 처리 루프 중 오류: {str(e)}")
        finally:
            self.is_running = False

    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 등록"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            
    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 제거"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """메시지 수신 처리"""
        try:
            # print(data)
            # print(self.callbacks)
            if self.callbacks:
                for callback in self.callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        self.logger.error(f"콜백 함수 실행 중 오류: {str(e)}\n{traceback.format_exc()}")
                return

            # 콜백이 없는 경우 메시지 출력
            header = data.get("header", {})
            
            if "rsp_cd" in header:
                rsp_msg = header.get("rsp_msg", "알 수 없는 메시지")
                if header["rsp_cd"] == "00000":
                    self.logger.info(f"응답: {rsp_msg}")
                else:
                    self.logger.error(f"오류: {rsp_msg}")
            else:
                pass
                # self.logger.info(f"메시지 수신: {json.dumps(data, ensure_ascii=False)}")
            
            # 이벤트 큐에 메시지 추가
            await self.event_queue.put(("message", data))
            
        except Exception as e:
            self.logger.error(f"메시지 처리 중 오류: {str(e)}\n{traceback.format_exc()}")

    async def _handle_error(self, error: Dict[str, Any]) -> None:
        """에러 처리"""
        try:
            self.logger.error(f"웹소켓 에러: {error}")
            await self.event_queue.put(("error", error))
            
            # 연결 재시도
            if self.is_running:
                await self._connect()
        except Exception as e:
            self.logger.error(f"에러 처리 중 오류: {str(e)}")

    async def _handle_close(self, data: Dict[str, Any]) -> None:
        """연결 종료 처리"""
        try:
            self.logger.info(f"웹소켓 연결 종료: {data}")
            await self.event_queue.put(("close", data))
            
            # 정상적인 종료가 아닌 경우 재연결 시도
            if self.is_running:
                await self._connect()
        except Exception as e:
            self.logger.error(f"연결 종료 처리 중 오류: {str(e)}")

    async def _handle_open(self, _: Any) -> None:
        """연결 시작 처리"""
        try:
            self.logger.info("웹소켓 연결이 열렸습니다.")
            await self.event_queue.put(("open", None))
        except Exception as e:
            self.logger.error(f"연결 시작 처리 중 오류: {str(e)}")

    async def subscribe(self, tr_code: str, tr_key: str, 
                       callback: Callable[[Dict[str, Any]], None]) -> None:
        """VI 데이터 구독
        
        Args:
            tr_code (str): TR 코드 (VI_)
            tr_key (str): 단축코드 6자리 또는 전체종목 '000000'
            callback (Callable[[Dict[str, Any]], None]): VI 데이터 수신 시 호출될 콜백 함수
        """
        subscription_key = f"{tr_code}_{tr_key}"
        
        # 구독 메시지 생성
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
        
        # 구독 정보 저장
        self.subscriptions[subscription_key] = {
            "message": message,
            "callback": callback,
            "subscribe_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 구독 요청 전송
        if self.client and self.client.is_connected:
            try:
                await self.client.send(message)
                self.logger.info(f"구독 요청 완료: {subscription_key}")
            except Exception as e:
                self.logger.error(f"구독 요청 실패: {str(e)}")
                del self.subscriptions[subscription_key]
                raise

    async def unsubscribe(self, tr_code: str, tr_key: str) -> None:
        """VI 데이터 구독 해제
        
        Args:
            tr_code (str): TR 코드 (VI_)
            tr_key (str): 단축코드 6자리 또는 전체종목 '000000'
        """
        subscription_key = f"{tr_code}_{tr_key}"
        
        if subscription_key in self.subscriptions:
            # 구독 해제 메시지 전송
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
            
            try:
                if self.client and self.client.is_connected:
                    await self.client.send(message)
                    self.logger.info(f"구독 해제 완료: {subscription_key}")
            except Exception as e:
                self.logger.error(f"구독 해제 실패: {str(e)}")
            finally:
                del self.subscriptions[subscription_key]

    def is_connected(self) -> bool:
        """웹소켓 연결 상태 확인"""
        return bool(self.client and self.client.is_connected) 