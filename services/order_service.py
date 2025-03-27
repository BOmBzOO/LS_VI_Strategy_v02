"""주문 처리 서비스

주문 처리 및 관리를 위한 서비스 클래스를 제공합니다.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from config.logging_config import setup_logger
from api.tr.order import OrderTRAPI
from api.realtime.order.order_handler import OrderHandler
from core.utils.validation import validate_order_params, validate_stock_code

class OrderService:
    """주문 처리 서비스 클래스"""

    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.order_api = OrderTRAPI()
        self.order_handler = OrderHandler()
        
        # 주문 관리
        self._orders: Dict[str, Dict[str, Any]] = {}  # 주문번호: 주문 정보
        self._positions: Dict[str, Dict[str, Any]] = {}  # 종목코드: 포지션 정보
        
        # 콜백 등록
        self.order_handler.add_callback("ORDER_ACCEPTED", self._handle_order_accepted)
        self.order_handler.add_callback("ORDER_FILLED", self._handle_order_filled)
        self.order_handler.add_callback("ORDER_CANCELLED", self._handle_order_cancelled)
        self.order_handler.add_callback("ORDER_REJECTED", self._handle_order_rejected)

    def place_order(self, order_params: Dict[str, Any]) -> Optional[str]:
        """주문 실행

        Args:
            order_params (Dict[str, Any]): 주문 파라미터
                - stock_code (str): 종목 코드
                - quantity (int): 주문 수량
                - price (float): 주문 가격 (지정가 주문인 경우)
                - order_type (str): 주문 유형 (MARKET/LIMIT)
                - order_side (str): 매수/매도 구분 (BUY/SELL)

        Returns:
            Optional[str]: 주문번호 (실패 시 None)
        """
        # 주문 파라미터 검증
        errors = validate_order_params(order_params)
        if errors:
            for error in errors:
                self.logger.error(f"주문 파라미터 오류: {error}")
            return None
        
        try:
            order_no = self.order_api.place_order(order_params)
            if order_no:
                self._orders[order_no] = {
                    "params": order_params,
                    "status": "PENDING",
                    "filled_quantity": 0,
                    "filled_price": Decimal("0"),
                    "order_time": datetime.now()
                }
                self.logger.info(f"주문 실행: {order_no}")
            return order_no
        except Exception as e:
            self.logger.error(f"주문 실행 중 오류 발생: {str(e)}")
            return None

    def cancel_order(self, order_no: str) -> bool:
        """주문 취소

        Args:
            order_no (str): 주문번호

        Returns:
            bool: 취소 성공 여부
        """
        if order_no not in self._orders:
            self.logger.error(f"존재하지 않는 주문번호: {order_no}")
            return False
        
        try:
            if self.order_api.cancel_order(order_no):
                self.logger.info(f"주문 취소 요청: {order_no}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"주문 취소 중 오류 발생: {str(e)}")
            return False

    def get_order(self, order_no: str) -> Dict[str, Any]:
        """주문 정보 조회

        Args:
            order_no (str): 주문번호

        Returns:
            Dict[str, Any]: 주문 정보
        """
        return self._orders.get(order_no, {})

    def get_orders(self, stock_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """주문 목록 조회

        Args:
            stock_code (Optional[str]): 종목 코드 (None인 경우 전체 주문)

        Returns:
            List[Dict[str, Any]]: 주문 목록
        """
        if stock_code:
            if not validate_stock_code(stock_code):
                self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
                return []
            return [order for order in self._orders.values() 
                   if order["params"]["stock_code"] == stock_code]
        return list(self._orders.values())

    def get_position(self, stock_code: str) -> Dict[str, Any]:
        """포지션 정보 조회

        Args:
            stock_code (str): 종목 코드

        Returns:
            Dict[str, Any]: 포지션 정보
        """
        if not validate_stock_code(stock_code):
            self.logger.error(f"유효하지 않은 종목 코드: {stock_code}")
            return {}
        return self._positions.get(stock_code, {})

    def get_positions(self) -> List[Dict[str, Any]]:
        """전체 포지션 목록 조회

        Returns:
            List[Dict[str, Any]]: 포지션 목록
        """
        return list(self._positions.values())

    def _handle_order_accepted(self, data: Dict[str, Any]) -> None:
        """주문 접수 처리"""
        order_no = data["order_no"]
        if order_no in self._orders:
            self._orders[order_no]["status"] = "ACCEPTED"
            self._orders[order_no]["accepted_time"] = datetime.now()
            self.logger.info(f"주문 접수: {order_no}")

    def _handle_order_filled(self, data: Dict[str, Any]) -> None:
        """주문 체결 처리"""
        order_no = data["order_no"]
        if order_no in self._orders:
            order = self._orders[order_no]
            order["status"] = "FILLED"
            order["filled_quantity"] = data["quantity"]
            order["filled_price"] = data["price"]
            order["filled_time"] = datetime.now()
            
            # 포지션 업데이트
            stock_code = order["params"]["stock_code"]
            if stock_code not in self._positions:
                self._positions[stock_code] = {
                    "quantity": 0,
                    "average_price": Decimal("0")
                }
            
            position = self._positions[stock_code]
            if order["params"]["order_side"] == "BUY":
                position["quantity"] += data["quantity"]
                position["average_price"] = (
                    (position["average_price"] * (position["quantity"] - data["quantity"]) +
                     data["price"] * data["quantity"]) / position["quantity"]
                )
            else:  # SELL
                position["quantity"] -= data["quantity"]
                if position["quantity"] == 0:
                    position["average_price"] = Decimal("0")
            
            self.logger.info(f"주문 체결: {order_no}")

    def _handle_order_cancelled(self, data: Dict[str, Any]) -> None:
        """주문 취소 처리"""
        order_no = data["order_no"]
        if order_no in self._orders:
            self._orders[order_no]["status"] = "CANCELLED"
            self._orders[order_no]["cancelled_time"] = datetime.now()
            self.logger.info(f"주문 취소: {order_no}")

    def _handle_order_rejected(self, data: Dict[str, Any]) -> None:
        """주문 거부 처리"""
        order_no = data["order_no"]
        if order_no in self._orders:
            self._orders[order_no]["status"] = "REJECTED"
            self._orders[order_no]["rejected_time"] = datetime.now()
            self._orders[order_no]["reject_reason"] = data.get("reason", "")
            self.logger.warning(f"주문 거부: {order_no} ({data.get('reason', '')})")

    def clear_completed_orders(self) -> None:
        """완료된 주문 정리"""
        completed_statuses = {"FILLED", "CANCELLED", "REJECTED"}
        completed_orders = [
            order_no for order_no, order in self._orders.items()
            if order["status"] in completed_statuses
        ]
        
        for order_no in completed_orders:
            del self._orders[order_no]
        
        self.logger.debug(f"완료된 주문 정리: {len(completed_orders)}건") 