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
import traceback
import json

class AccountOrderData:
    """계좌 주문 체결 데이터 클래스"""
    
    def __init__(self, data: Dict[str, Any]):
        """초기화"""
        # API 명세에 맞춰 필드 정의
        self.account_no = data.get("accno1", "")  # 계좌번호
        self.account_name = data.get("acntnm", "")  # 계좌명
        self.order_no = data.get("ordno", "")  # 주문번호
        self.original_order_no = data.get("orgordno", "")  # 원주문번호
        self.order_time = data.get("ordtm", "")  # 주문시각
        self.exec_time = data.get("exectime", "")  # 체결시각
        self.rcpt_exec_time = data.get("rcptexectime", "")  # 거래소수신체결시각
        
        # 종목 정보
        self.shcode = data.get("shtnIsuno", "")  # 단축종목번호
        self.expcode = data.get("Isuno", "")  # 표준종목번호
        self.hname = data.get("Isunm", "")  # 종목명
        
        # 주문 상태
        self.order_status = data.get("ordxctptncode", "")  # 주문체결유형코드
        self.order_type = data.get("ordptncode", "")  # 주문유형코드
        self.market_code = data.get("ordmktcode", "")  # 주문시장코드
        self.trade_type = data.get("ordtrdptncode", "")  # 주문거래유형코드
        self.credit_type = data.get("mgntrncode", "")  # 신용거래코드
        
        # 수량 정보
        self.order_qty = data.get("ordqty", "0")  # 주문수량
        self.exec_qty = data.get("execqty", "0")  # 체결수량
        self.remain_qty = data.get("unercqty", "0")  # 미체결수량
        self.cancel_qty = data.get("canccnfqty", "0")  # 취소확인수량
        self.modify_qty = data.get("mdfycnfqty", "0")  # 정정확인수량
        self.reject_qty = data.get("rjtqty", "0")  # 거부수량
        
        # 가격 정보
        self.order_price = data.get("ordprc", "0")  # 주문가격
        self.exec_price = data.get("execprc", "0")  # 체결가격
        self.avg_price = data.get("ordavrexecprc", "0")  # 주문평균체결가격
        
        # 금액 정보
        self.order_amt = data.get("ordamt", "0")  # 주문금액
        self.exec_amt = data.get("mnyexecamt", "0")  # 현금체결금액
        self.commission = data.get("cmsnamtexecamt", "0")  # 수수료체결금액
        
        # 계좌 정보
        self.deposit = data.get("deposit", "0")  # 예수금
        self.ordable_money = data.get("ordablemny", "0")  # 주문가능현금
        self.cash_margin = data.get("csgnmnymgn", "0")  # 위탁증거금현금
        self.subst_margin = data.get("csgnsubstmgn", "0")  # 위탁증거금대용
        
        # 메시지 정보
        self.msg_code = data.get("msgcode", "")  # 메시지코드
        self.reject_reason = data.get("msgcode", "")  # 거부사유코드
        
        # 기타 정보
        self.user_id = data.get("userid", "")  # 사용자ID
        self.branch_no = data.get("bpno", "")  # 지점번호
        self.trade_code = data.get("trcode", "")  # TR코드
        
        self.timestamp = datetime.now().isoformat()

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
        """초기화
        
        Args:
            token (str): 인증 토큰
            account_no (str): 계좌번호
        """
        self.logger = setup_logger(__name__)
        self.token = token
        self.account_no = account_no
        self.ws_manager: Optional[WebSocketManager] = None
        self.ws_handler: Optional[DefaultWebSocketHandler] = None
        self.state = WebSocketState.DISCONNECTED
        self.order_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.current_orders: Dict[str, AccountOrderData] = {}  # 주문번호: 주문데이터
        
        # 웹소켓 설정
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
            # 웹소켓 핸들러 초기화
            if not self.ws_handler:
                self.ws_handler = DefaultWebSocketHandler()
                self.ws_handler.register_handler("SC0", self._handle_order_message)  # 주문 접수
                self.ws_handler.register_handler("SC1", self._handle_order_message)  # 주문 체결
                self.ws_handler.register_handler("SC2", self._handle_order_message)  # 주문 정정
                self.ws_handler.register_handler("SC3", self._handle_order_message)  # 주문 취소
                self.ws_handler.register_handler("SC4", self._handle_order_message)  # 주문 거부
            
            # 웹소켓 매니저가 이미 설정되어 있으면 재사용
            if self.ws_manager and self.ws_manager.is_connected():
                self.logger.info("기존 웹소켓 매니저를 재사용합니다.")
                await self._subscribe()
                self.state = WebSocketState.CONNECTED
                self.logger.info(f"계좌 체결 모니터링 시작 - 계좌: {self.account_no}")
                return
            
            # 웹소켓 매니저가 없으면 새로 생성
            if not self.ws_manager:
                self.ws_manager = WebSocketManager(self.ws_config)
                # 에러, 종료, 연결 이벤트만 핸들러로 등록
                self.ws_manager.add_event_handler("error", self._handle_error)
                self.ws_manager.add_event_handler("close", self._handle_close)
                self.ws_manager.add_event_handler("open", self._handle_open)
                # 메시지는 콜백으로만 처리
                self.ws_manager.add_callback(self._handle_order_message, "SC0")  # 주문 접수
                self.ws_manager.add_callback(self._handle_order_message, "SC1")  # 주문 체결
                self.ws_manager.add_callback(self._handle_order_message, "SC2")  # 주문 정정
                self.ws_manager.add_callback(self._handle_order_message, "SC3")  # 주문 취소
                self.ws_manager.add_callback(self._handle_order_message, "SC4")  # 주문 거부
                await self.ws_manager.start()
            
            # 계좌 구독 시작
            await self._subscribe()
            
            self.state = WebSocketState.CONNECTED
            self.logger.info(f"계좌 체결 모니터링 시작 - 계좌: {self.account_no}")
            
        except Exception as e:
            self.state = WebSocketState.ERROR
            self.logger.error(f"계좌 체결 모니터링 시작 중 오류 발생: {str(e)}")
            await self.stop()
            raise
            
    async def stop(self) -> None:
        """모니터링 중지"""
        try:
            if self.state == WebSocketState.DISCONNECTED:
                return
                
            self.state = WebSocketState.CLOSING
            
            # 계좌 구독 해제
            if self.ws_manager and self.ws_manager.is_connected():
                try:
                    await self._unsubscribe()
                except Exception as e:
                    self.logger.warning(f"계좌 구독 해제 중 오류 발생: {str(e)}")
            
            # 웹소켓 매니저는 공유 자원이므로 종료하지 않음
            self.state = WebSocketState.DISCONNECTED
            
            # 자원 정리
            self.order_callbacks.clear()
            self.current_orders.clear()
            
            self.logger.info(f"계좌 체결 모니터링 중지 - 계좌: {self.account_no}")
            
        except Exception as e:
            self.logger.error(f"계좌 체결 모니터링 중지 중 오류 발생: {str(e)}")
            self.state = WebSocketState.ERROR
            raise
            
    async def _subscribe(self) -> None:
        """계좌 구독"""
        if not self.ws_manager or not self.ws_manager.is_connected():
            raise RuntimeError("웹소켓이 연결되지 않았습니다.")
            
        # 주문 접수 구독 (계좌번호 없이)
        await self.ws_manager.subscribe(
            tr_code="SC0",
            tr_key="",  # 계좌번호 없이 빈 문자열로 설정
            callback=self._handle_order_message
        )
        
        # 주문 체결 구독 (계좌번호 없이)
        await self.ws_manager.subscribe(
            tr_code="SC1",
            tr_key="",  # 계좌번호 없이 빈 문자열로 설정
            callback=self._handle_order_message
        )
        
        # 주문 정정 구독
        await self.ws_manager.subscribe(
            tr_code="SC2",
            tr_key="",
            callback=self._handle_order_message
        )
        
        # 주문 취소 구독 (계좌번호 없이)
        await self.ws_manager.subscribe(
            tr_code="SC3",
            tr_key="",  # 계좌번호 없이 빈 문자열로 설정
            callback=self._handle_order_message
        )
        
        # 주문 거부 구독 (계좌번호 없이)
        await self.ws_manager.subscribe(
            tr_code="SC4",
            tr_key="",  # 계좌번호 없이 빈 문자열로 설정
            callback=self._handle_order_message
        )
        
    async def _unsubscribe(self) -> None:
        """계좌 구독 해제"""
        if not self.ws_manager or not self.ws_manager.is_connected():
            return
            
        # 주문 접수 구독 해제
        await self.ws_manager.unsubscribe(
            tr_code="SC0",
            tr_key=""  # 계좌번호 없이 빈 문자열로 설정
        )
        
        # 주문 체결 구독 해제
        await self.ws_manager.unsubscribe(
            tr_code="SC1",
            tr_key=""  # 계좌번호 없이 빈 문자열로 설정
        )
        
        # 주문 정정 구독 해제
        await self.ws_manager.unsubscribe(
            tr_code="SC2",
            tr_key=""
        )
        
        # 주문 취소 구독 해제 (계좌번호 없이)
        await self.ws_manager.unsubscribe(
            tr_code="SC3",
            tr_key=""  # 계좌번호 없이 빈 문자열로 설정
        )
        
        # 주문 거부 구독 해제 (계좌번호 없이)
        await self.ws_manager.unsubscribe(
            tr_code="SC4",
            tr_key=""  # 계좌번호 없이 빈 문자열로 설정
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
            # 메시지 타입 확인
            header = message.get("header", {})
            body = message.get("body", {})
            
            # 주문 메시지가 아닌 경우 무시
            tr_cd = header.get("tr_cd", "") or body.get("tr_cd", "")
            if not tr_cd.startswith("SC"):  # SC0, SC1, SC2, SC3, SC4만 처리
                return
                
            self.logger.debug(f"주문 메시지 처리: {message}")
            
            # 콜백이 있는 경우 전체 메시지를 전달하고 리턴
            if self.order_callbacks:
                for callback in self.order_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)
                    except Exception as e:
                        self.logger.error(f"콜백 함수 실행 중 오류: {str(e)}")
                return
                
            # 콜백이 없는 경우에만 메시지 출력
            self.logger.info(f"주문 메시지 수신: {json.dumps(message, ensure_ascii=False)}")
            
            # 응답 메시지 처리
            if "rsp_cd" in header:
                rsp_msg = header.get("rsp_msg", "알 수 없는 메시지")
                if header["rsp_cd"] == "00000":
                    self.logger.info(f"주문 응답: {rsp_msg}")
                else:
                    self.logger.error(f"주문 구독 오류: {rsp_msg}")
                return
                
            # body가 None인 경우 무시
            if not body or not isinstance(body, dict):
                return
                
            # 주문 데이터 처리 및 로깅
            order_data = AccountOrderData(body)
            
            # SC0(주문접수), SC1(주문체결), SC2(주문정정), SC3(주문취소), SC4(주문거부)는 계좌번호 필터링 없이 처리
            if tr_cd in ["SC0", "SC1", "SC2", "SC3", "SC4"]:
                self.current_orders[order_data.order_no] = order_data
                self.logger.info(self._format_order_message(order_data))
            # 나머지는 해당 계좌의 데이터만 처리
            elif order_data.account_no == self.account_no:
                self.current_orders[order_data.order_no] = order_data
                self.logger.info(self._format_order_message(order_data))
                    
        except Exception as e:
            self.logger.error(f"주문 메시지 처리 중 오류: {str(e)}\n{traceback.format_exc()}")
            
    def _format_order_message(self, data: AccountOrderData) -> str:
        """주문 메시지 포맷팅"""
        try:
            status_map = {
                "01": "주문",
                "02": "정정",
                "03": "취소",
                "11": "체결",
                "12": "정정확인",
                "13": "취소확인",
                "14": "거부"
            }
            
            type_map = {
                "01": "현금매도",
                "02": "현금매수",
                "03": "신용매도",
                "04": "신용매수",
                "05": "저축매도",
                "06": "저축매수",
                "07": "상품매도(대차)",
                "09": "상품매도",
                "10": "상품매수"
            }
            
            market_map = {
                "00": "비상장",
                "10": "코스피",
                "11": "채권",
                "19": "장외시장",
                "20": "코스닥",
                "23": "코넥스",
                "30": "프리보드"
            }
            
            credit_map = {
                "000": "보통",
                "001": "유통융자신규",
                "003": "자기융자신규",
                "005": "유통대주신규",
                "007": "자기대주신규",
                "101": "유통융자상환",
                "103": "자기융자상환",
                "105": "유통대주상환",
                "107": "자기대주상환"
            }
            
            status = status_map.get(data.order_status, "알 수 없음")
            order_type = type_map.get(data.order_type, "알 수 없음")
            market = market_map.get(data.market_code, "알 수 없음")
            credit = credit_map.get(data.credit_type, "일반")
            
            msg = (
                f"[{data.order_time}] "
                f"계좌: {data.account_no}({data.account_name}), "
                f"주문번호: {data.order_no}, "
                f"종목: {data.shcode}({data.hname}), "
                f"시장: {market}, "
                f"상태: {status}, "
                f"구분: {order_type}({credit}), "
            )
            
            if data.order_status in ["01", "02", "03"]:  # 주문/정정/취소
                msg += f"주문: {data.order_price}원 x {data.order_qty}주"
            elif data.order_status == "11":  # 체결
                msg += (
                    f"체결: {data.exec_price}원 x {data.exec_qty}주, "
                    f"평균가: {data.avg_price}원, "
                    f"미체결: {data.remain_qty}주"
                )
            elif data.order_status == "14":  # 거부
                msg += f"거부수량: {data.reject_qty}주, 사유: {data.reject_reason}"
                
            return msg
            
        except Exception as e:
            self.logger.error(f"메시지 포맷팅 중 오류: {str(e)}")
            return f"[{datetime.now()}] 메시지 포맷팅 오류"
            
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
            await self.start()  # 자동 재연결
            
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