"""계좌 체결 모니터링 서비스

계좌의 주문 체결 정보를 실시간으로 모니터링하는 서비스를 제공합니다.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import asyncio
from config.logging_config import setup_logger
from api.realtime.websocket.websocket_manager import WebSocketManager
from api.realtime.websocket.websocket_base import WebSocketState, WebSocketConfig
from api.realtime.websocket.websocket_handler import DefaultWebSocketHandler
from config.settings import LS_WS_URL
from api.constants import (
    OrderType, MessageType, OrderCode, OrderStatus, OrderTypeCode,
    MarketCode, CreditType, STATUS_MAP, ORDER_TYPE_MAP, MARKET_MAP, CREDIT_MAP
)
import traceback
import json

class AccountOrderData:
    """계좌 주문 체결 데이터 클래스"""
    
    def __init__(self, data: Dict[str, Any]):
        """초기화"""
        self._init_basic_info(data)
        self._init_order_info(data)
        self._init_stock_info(data)
        self._init_quantity_info(data)
        self._init_price_info(data)
        self._init_amount_info(data)
        self._init_account_info(data)
        self._init_message_info(data)
        self._init_other_info(data)
        self.timestamp = datetime.now().isoformat()

    def _init_basic_info(self, data: Dict[str, Any]) -> None:
        """기본 정보 초기화"""
        self.account_no = data.get("accno1", "")
        self.account_name = data.get("acntnm", "")
        self.order_no = data.get("ordno", "")
        self.original_order_no = data.get("orgordno", "")
        self.order_time = data.get("ordtm", "")
        self.exec_time = data.get("exectime", "")
        self.rcpt_exec_time = data.get("rcptexectime", "")

    def _init_order_info(self, data: Dict[str, Any]) -> None:
        """주문 정보 초기화"""
        self.order_status = data.get("ordxctptncode", "")
        self.order_type = data.get("ordptncode", "")
        self.market_code = data.get("ordmktcode", "")
        self.trade_type = data.get("ordtrdptncode", "")
        self.credit_type = data.get("mgntrncode", "")

    def _init_stock_info(self, data: Dict[str, Any]) -> None:
        """종목 정보 초기화"""
        self.shcode = data.get("shtnIsuno", "")
        self.expcode = data.get("Isuno", "")
        self.hname = data.get("Isunm", "")

    def _init_quantity_info(self, data: Dict[str, Any]) -> None:
        """수량 정보 초기화"""
        self.order_qty = data.get("ordqty", "0")
        self.exec_qty = data.get("execqty", "0")
        self.remain_qty = data.get("unercqty", "0")
        self.cancel_qty = data.get("canccnfqty", "0")
        self.modify_qty = data.get("mdfycnfqty", "0")
        self.reject_qty = data.get("rjtqty", "0")

    def _init_price_info(self, data: Dict[str, Any]) -> None:
        """가격 정보 초기화"""
        self.order_price = data.get("ordprc", "0")
        self.exec_price = data.get("execprc", "0")
        self.avg_price = data.get("ordavrexecprc", "0")

    def _init_amount_info(self, data: Dict[str, Any]) -> None:
        """금액 정보 초기화"""
        self.order_amt = data.get("ordamt", "0")
        self.exec_amt = data.get("mnyexecamt", "0")
        self.commission = data.get("cmsnamtexecamt", "0")

    def _init_account_info(self, data: Dict[str, Any]) -> None:
        """계좌 정보 초기화"""
        self.deposit = data.get("deposit", "0")
        self.ordable_money = data.get("ordablemny", "0")
        self.cash_margin = data.get("csgnmnymgn", "0")
        self.subst_margin = data.get("csgnsubstmgn", "0")

    def _init_message_info(self, data: Dict[str, Any]) -> None:
        """메시지 정보 초기화"""
        self.msg_code = data.get("msgcode", "")
        self.reject_reason = data.get("msgcode", "")

    def _init_other_info(self, data: Dict[str, Any]) -> None:
        """기타 정보 초기화"""
        self.user_id = data.get("userid", "")
        self.branch_no = data.get("bpno", "")
        self.trade_code = data.get("trcode", "")

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "account_no": self.account_no,
            "account_name": self.account_name,
            "order_no": self.order_no,
            "original_order_no": self.original_order_no,
            "order_time": self.order_time,
            "exec_time": self.exec_time,
            "rcpt_exec_time": self.rcpt_exec_time,
            "shcode": self.shcode,
            "expcode": self.expcode,
            "hname": self.hname,
            "order_status": self.order_status,
            "order_type": self.order_type,
            "market_code": self.market_code,
            "trade_type": self.trade_type,
            "credit_type": self.credit_type,
            "order_qty": self.order_qty,
            "exec_qty": self.exec_qty,
            "remain_qty": self.remain_qty,
            "cancel_qty": self.cancel_qty,
            "modify_qty": self.modify_qty,
            "reject_qty": self.reject_qty,
            "order_price": self.order_price,
            "exec_price": self.exec_price,
            "avg_price": self.avg_price,
            "order_amt": self.order_amt,
            "exec_amt": self.exec_amt,
            "commission": self.commission,
            "deposit": self.deposit,
            "ordable_money": self.ordable_money,
            "cash_margin": self.cash_margin,
            "subst_margin": self.subst_margin,
            "msg_code": self.msg_code,
            "reject_reason": self.reject_reason,
            "user_id": self.user_id,
            "branch_no": self.branch_no,
            "trade_code": self.trade_code,
            "timestamp": self.timestamp
        }

class AccountMonitorService:
    """계좌 체결 모니터링 서비스 클래스"""

    def __init__(self, token: str, account_no: str):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.token = token
        self.account_no = account_no
        self.ws_manager: Optional[WebSocketManager] = None
        self.ws_handler: Optional[DefaultWebSocketHandler] = None
        self.state = WebSocketState.DISCONNECTED
        self.order_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.current_orders: Dict[str, AccountOrderData] = {}
        self.order_executions: Dict[str, Dict[str, Any]] = {}
        
        self.ws_config: WebSocketConfig = {
            "url": LS_WS_URL,
            "token": token,
            "max_subscriptions": 1,
            "max_reconnect_attempts": 5,
            "reconnect_delay": 5,
            "ping_interval": 30,
            "ping_timeout": 10,
            "connect_timeout": 30
        }

    async def start(self) -> None:
        """모니터링 시작"""
        try:
            await self._initialize_websocket()
            await self._subscribe()
            self.state = WebSocketState.CONNECTED
            self.logger.info(f"계좌 체결 모니터링 시작 - 계좌: {self.account_no}")
        except Exception as e:
            self.state = WebSocketState.ERROR
            self.logger.error(f"계좌 체결 모니터링 시작 중 오류 발생: {str(e)}")
            await self.stop()
            raise

    async def _initialize_websocket(self) -> None:
        """웹소켓 초기화"""
        if not self.ws_handler:
            self.ws_handler = DefaultWebSocketHandler()
            for msg_type in [MessageType.ORDER, MessageType.EXECUTION, 
                           MessageType.EXECUTION_MODIFY, MessageType.CANCEL, 
                           MessageType.REJECT]:
                self.ws_handler.register_handler(msg_type, self._handle_order_message)

        if self.ws_manager and self.ws_manager.is_connected():
            self.logger.info("기존 웹소켓 매니저를 재사용합니다.")
            return

        if not self.ws_manager:
            self.ws_manager = WebSocketManager(self.ws_config)
            self.ws_manager.add_event_handler("error", self._handle_error)
            self.ws_manager.add_event_handler("close", self._handle_close)
            self.ws_manager.add_event_handler("open", self._handle_open)
            
            for msg_type in [MessageType.ORDER, MessageType.EXECUTION, 
                           MessageType.EXECUTION_MODIFY, MessageType.CANCEL, 
                           MessageType.REJECT]:
                self.ws_manager.add_callback(self._handle_order_message, msg_type)
            
            await self.ws_manager.start()

    async def stop(self) -> None:
        """모니터링 중지"""
        try:
            if self.state == WebSocketState.DISCONNECTED:
                return

            self.state = WebSocketState.CLOSING
            await self._unsubscribe()
            self._cleanup()
            self.state = WebSocketState.DISCONNECTED
            self.logger.info(f"계좌 체결 모니터링 중지 - 계좌: {self.account_no}")
        except Exception as e:
            self.logger.error(f"계좌 체결 모니터링 중지 중 오류 발생: {str(e)}")
            self.state = WebSocketState.ERROR
            raise

    def _cleanup(self) -> None:
        """자원 정리"""
        self.order_callbacks.clear()
        self.current_orders.clear()
        self.order_executions.clear()

    async def _subscribe(self) -> None:
        """계좌 구독"""
        if not self.ws_manager or not self.ws_manager.is_connected():
            raise RuntimeError("웹소켓이 연결되지 않았습니다.")

        for msg_type in [MessageType.ORDER, MessageType.EXECUTION, 
                        MessageType.EXECUTION_MODIFY, MessageType.CANCEL, 
                        MessageType.REJECT]:
            await self.ws_manager.subscribe(
                tr_code=msg_type,
                tr_key="",
                callback=self._handle_order_message
            )

    async def _unsubscribe(self) -> None:
        """계좌 구독 해제"""
        if not self.ws_manager or not self.ws_manager.is_connected():
            return

        for msg_type in [MessageType.ORDER, MessageType.EXECUTION, 
                        MessageType.EXECUTION_MODIFY, MessageType.CANCEL, 
                        MessageType.REJECT]:
            await self.ws_manager.unsubscribe(
                tr_code=msg_type,
                tr_key=""
            )

    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 등록"""
        if callback not in self.order_callbacks:
            self.order_callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 제거"""
        if callback in self.order_callbacks:
            self.order_callbacks.remove(callback)

    async def _handle_order_message(self, message: Dict[str, Any]) -> None:
        """주문 메시지 처리"""
        try:
            header = message.get("header", {})
            body = message.get("body", {})
            tr_cd = header.get("tr_cd", "") or body.get("tr_cd", "")

            if not tr_cd.startswith("SC"):
                return

            self.logger.debug(f"주문 메시지 처리: {message}")

            if self.order_callbacks:
                await self._handle_callbacks(message)
                return

            await self._process_order_message(tr_cd, body)

        except Exception as e:
            self.logger.error(f"주문 메시지 처리 중 오류: {str(e)}\n{traceback.format_exc()}")

    async def _handle_callbacks(self, message: Dict[str, Any]) -> None:
        """콜백 함수 실행"""
        for callback in self.order_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                self.logger.error(f"콜백 함수 실행 중 오류: {str(e)}")

    async def _process_order_message(self, tr_cd: str, body: Dict[str, Any]) -> None:
        """주문 메시지 처리 로직"""
        shcode, hname, time, price, qty, order_no, ordptncode, ordgb, ordchegb, singb = get_order_info(body)

        if not all([shcode, hname, time]):
            return

        prefix = get_order_type(body)

        if tr_cd == MessageType.ORDER:
            await self._handle_order_receipt(time, prefix, shcode, hname, price, qty, order_no, body)
        elif tr_cd == MessageType.EXECUTION:
            await self._handle_execution(time, prefix, shcode, hname, price, qty, order_no, ordptncode, singb)
        elif tr_cd == MessageType.EXECUTION_MODIFY:
            self.logger.info(f"[{time}] {prefix}정정완료: {shcode}({hname}) {price}원 x {qty}주")
        elif tr_cd == MessageType.CANCEL:
            await self._handle_cancel(time, prefix, shcode, hname, qty, order_no)
        elif tr_cd == MessageType.REJECT:
            await self._handle_reject(time, prefix, shcode, hname, order_no, body)

    async def _handle_order_receipt(self, time: str, prefix: str, shcode: str, 
                                  hname: str, price: str, qty: str, order_no: str, 
                                  body: Dict[str, Any]) -> None:
        """주문 접수 처리"""
        trcode = body.get("trcode", "")
        if trcode in OrderCode.NEW:
            self.order_executions[order_no] = {
                "order_qty": float(qty),
                "exec_qty": 0.0,
                "is_completed": False
            }
            self.logger.info(f"[{time}] {prefix}접수: {shcode}({hname}) {price}원 x {qty}주")
        elif trcode == OrderCode.MODIFY[0]:
            self.logger.info(f"[{time}] {prefix}정정접수: {shcode}({hname}) {price}원 x {qty}주")
        elif trcode == OrderCode.CANCEL[0]:
            self.logger.info(f"[{time}] {prefix}취소접수: {shcode}({hname}) {qty}주")
        else:
            self.logger.info(f"[{time}] {prefix}접수: {shcode}({hname}) {price}원 x {qty}주 (trcode: {trcode})")

    async def _handle_execution(self, time: str, prefix: str, shcode: str, 
                              hname: str, price: str, qty: str, order_no: str, 
                              ordptncode: str, singb: str) -> None:
        """체결 처리"""
        order_type = self._get_order_type_text(ordptncode)
        credit_type = self._get_credit_type_text(singb)
        
        if order_no in self.order_executions:
            exec_info = self.order_executions[order_no]
            exec_info["exec_qty"] += float(qty)
            completion_status = "체결완료" if exec_info["exec_qty"] >= exec_info["order_qty"] else "부분체결"
            
            self._log_execution(time, prefix, shcode, hname, price, qty, order_type, 
                              credit_type, completion_status, exec_info)
        else:
            self._log_execution(time, prefix, shcode, hname, price, qty, order_type, credit_type)

    def _get_order_type_text(self, ordptncode: str) -> str:
        """주문 유형 텍스트 반환"""
        return ORDER_TYPE_MAP.get(ordptncode, "")

    def _get_credit_type_text(self, singb: str) -> str:
        """신용 구분 텍스트 반환"""
        return CREDIT_MAP.get(singb, "")

    def _log_execution(self, time: str, prefix: str, shcode: str, hname: str, 
                      price: str, qty: str, order_type: str, credit_type: str, 
                      completion_status: str = "", exec_info: Dict[str, Any] = None) -> None:
        """체결 로그 출력"""
        msg = f"[{time}] {prefix}체결: {shcode}({hname}) {price}원 x {qty}주 [{order_type}]"
        
        if credit_type:
            msg += f"[{credit_type}]"
            
        if completion_status and exec_info:
            msg += f" ({completion_status}) ({exec_info['exec_qty']}/{exec_info['order_qty']})"
            
        self.logger.info(msg)

    async def _handle_cancel(self, time: str, prefix: str, shcode: str, 
                           hname: str, qty: str, order_no: str) -> None:
        """취소 처리"""
        if order_no in self.order_executions:
            del self.order_executions[order_no]
        self.logger.info(f"[{time}] {prefix}취소완료: {shcode}({hname}) {qty}주")

    async def _handle_reject(self, time: str, prefix: str, shcode: str, 
                           hname: str, order_no: str, body: Dict[str, Any]) -> None:
        """거부 처리"""
        if order_no in self.order_executions:
            del self.order_executions[order_no]
        reject_reason = body.get("rsp_msg", "알 수 없는 사유")
        self.logger.warning(f"[{time}] {prefix}거부: {shcode}({hname}) - {reject_reason}")

    async def _handle_error(self, error: Exception) -> None:
        """에러 처리"""
        self.logger.error(f"계좌 체결 모니터링 중 에러 발생: {str(error)}")
        self.state = WebSocketState.ERROR

    async def _handle_close(self, data: Dict[str, Any]) -> None:
        """연결 종료 처리"""
        code = data.get("code")
        message = data.get("message")
        self.logger.warning(f"계좌 체결 모니터링 연결 종료 (코드: {code}, 메시지: {message})")

        if self.state not in [WebSocketState.CLOSING, WebSocketState.DISCONNECTED]:
            self.state = WebSocketState.DISCONNECTED
            await self.start()

    async def _handle_open(self, _: Any) -> None:
        """연결 시작 처리"""
        self.logger.info("계좌 체결 모니터링 연결이 열렸습니다.")

    def get_order(self, order_no: str) -> Optional[Dict[str, Any]]:
        """특정 주문 정보 조회"""
        order_data = self.current_orders.get(order_no)
        return order_data.to_dict() if order_data else None

    def get_orders(self) -> List[Dict[str, Any]]:
        """전체 주문 목록 조회"""
        return [order.to_dict() for order in self.current_orders.values()]

def get_order_type(body: dict) -> str:
    """주문 유형을 판단하여 매수/매도 구분을 반환합니다."""
    for field, value in [
        ("ordptncode", OrderType.BUY),
        ("ordgb", OrderType.BUY),
        ("ordchegb", OrderType.BUY)
    ]:
        if body.get(field) == value:
            return "매수"
        elif body.get(field) == OrderType.SELL:
            return "매도"
    
    return "매도" if body.get("gubun") == "B" else "매수"

def get_order_info(body: dict) -> tuple:
    """주문 정보를 추출합니다."""
    shcode = body.get("shtcode", "") or body.get("shtnIsuno", "")
    hname = body.get("hname", "") or body.get("Isunm", "")
    time = body.get("ordtm", "") or body.get("exectime", "")
    
    # 가격 정보 추출 로직 개선
    price = "0"
    for price_field in ["execprc", "ordprice", "ordavrexecprc"]:
        if body.get(price_field):
            price = body.get(price_field)
            break
        
    qty = body.get("ordqty", "0") or body.get("execqty", "0")
    order_no = body.get("ordno", "")
    
    # 주문 관련 상세 정보
    ordptncode = body.get("ordptncode", "")
    ordgb = body.get("ordgb", "")
    ordchegb = body.get("ordchegb", "")
    singb = body.get("singb", "")
    
    return shcode, hname, time, price, qty, order_no, ordptncode, ordgb, ordchegb, singb 