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

        # 콜백 함수 관리 - 메시지 타입별로 구분
        self.callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {
            "VI_": [],  # VI 메시지 콜백
            "S3_": [],  # KOSPI 체결 메시지 콜백
            "K3_": [],  # KOSDAQ 체결 메시지 콜백
            "default": [],  # 기타 메시지 콜백
            "SC0": [],  # 주문 접수 콜백
            "SC1": [],  # 주문 체결 콜백
            "SC2": [],  # 주문 정정 콜백
            "SC3": [],  # 주문 취소 콜백
            "SC4": []  # 주문 거부 콜백
        }
        
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

    def add_callback(self, callback: Callable[[Dict[str, Any]], None], message_type: str = "default") -> None:
        """콜백 함수 등록
        
        Args:
            callback: 콜백 함수
            message_type: 메시지 타입 (VI_, S3_, K3_, SC0, SC1, SC2, SC3, SC4)
        """
        if message_type not in self.callbacks:
            self.callbacks[message_type] = []
        if callback not in self.callbacks[message_type]:
            self.callbacks[message_type].append(callback)
            
    def remove_callback(self, callback: Callable[[Dict[str, Any]], None], message_type: str = "default") -> None:
        """콜백 함수 제거"""
        if message_type in self.callbacks and callback in self.callbacks[message_type]:
            self.callbacks[message_type].remove(callback)
            if not self.callbacks[message_type]:  # 리스트가 비면 제거
                del self.callbacks[message_type]

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """메시지 수신 처리"""
        # print(f"메시지 수신: {data}")/
        try:
            # 메시지 타입 확인
            header = data.get("header", {}) if data else {}
            body = data.get("body", {}) if data else {}
            if not isinstance(header, dict):
                header = {}
            if not isinstance(body, dict):
                body = {}
                
            tr_cd = header.get("tr_cd", "")  # 헤더에서 tr_cd 확인
            if not tr_cd:  # 헤더에 없으면 바디에서 확인
                tr_cd = body.get("tr_cd", "")
            
            # 응답 코드 확인 및 로깅
            if "rsp_cd" in header:
                rsp_cd = header.get("rsp_cd", "")
                rsp_msg = header.get("rsp_msg", "알 수 없는 메시지")
                if rsp_cd == "00000":
                    self.logger.debug(f"응답: {rsp_msg}")
                else:
                    self.logger.error(f"오류 응답 (코드: {rsp_cd}): {rsp_msg}")
                    
                # 오류 응답도 이벤트 큐에 추가
                await self.event_queue.put(("message", data))
                return
            
            # 콜백 실행
            callbacks_to_execute = []
            
            # 주식 주문 메시지 처리
            if tr_cd.startswith("SC"):
                if tr_cd == "SC0":  # 주문 접수
                    callbacks_to_execute.extend(self.callbacks.get("SC0", []))
                elif tr_cd == "SC1":  # 주문 체결
                    callbacks_to_execute.extend(self.callbacks.get("SC1", []))
                elif tr_cd == "SC2":  # 주문 정정
                    callbacks_to_execute.extend(self.callbacks.get("SC2", []))
                elif tr_cd == "SC3":  # 주문 취소
                    callbacks_to_execute.extend(self.callbacks.get("SC3", []))
                elif tr_cd == "SC4":  # 주문 거부
                    callbacks_to_execute.extend(self.callbacks.get("SC4", []))
                    
            # VI 메시지 처리
            elif tr_cd.startswith("VI_"):
                callbacks_to_execute.extend(self.callbacks.get("VI_", []))
                
            # 체결 메시지 처리
            elif tr_cd.startswith("S3_"):  # KOSPI 체결
                callbacks_to_execute.extend(self.callbacks.get("S3_", []))
            elif tr_cd.startswith("K3_"):  # KOSDAQ 체결
                callbacks_to_execute.extend(self.callbacks.get("K3_", []))
                
            # 기본 콜백도 실행
            callbacks_to_execute.extend(self.callbacks.get("default", []))
            
            # 콜백이 있으면 실행
            if callbacks_to_execute:
                for callback in callbacks_to_execute:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        self.logger.error(f"콜백 함수 실행 중 오류: {str(e)}\n{traceback.format_exc()}")
            else:
                # 콜백이 없는 경우에만 메시지 출력
                self.logger.debug(f"메시지 수신: {json.dumps(data, ensure_ascii=False)}")
            
            # 모든 메시지를 이벤트 큐에 추가
            await self.event_queue.put(("message", data))
            
        except Exception as e:
            self.logger.error(f"메시지 처리 중 오류: {str(e)}\n{traceback.format_exc()}")
            # 오류가 발생해도 이벤트 큐에 추가
            await self.event_queue.put(("error", {"error": str(e), "traceback": traceback.format_exc()}))

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
        
        # tr_type 설정
        tr_type = "1"  # 기본값: 계좌등록
        if tr_code.startswith("SC"):  # 주문 관련 메시지
            tr_type = "1"  # 계좌등록
        elif tr_code.startswith("VI_"):  # VI 메시지
            tr_type = "3"  # 실시간 시세 등록
        
        # 구독 메시지 생성
        message = {
            "header": {
                "token": self.config["token"],
                "tr_type": tr_type
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
            # tr_type 설정
            tr_type = "2"  # 기본값: 계좌해제
            if tr_code.startswith("SC"):  # 주문 관련 메시지
                tr_type = "2"  # 계좌해제
            elif tr_code.startswith("VI_"):  # VI 메시지
                tr_type = "4"  # 실시간 시세 해제
            
            # 구독 해제 메시지 전송
            message = {
                "header": {
                    "token": self.config["token"],
                    "tr_type": tr_type
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