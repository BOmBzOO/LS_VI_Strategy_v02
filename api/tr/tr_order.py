"""주문 TR API"""

from typing import Dict, Any, Optional
from api.tr.tr_base import BaseAPI
from api.constants import TRCode
from config.logging_config import setup_logger

class OrderTRAPI(BaseAPI):
    """주문 TR API"""

    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)

    def send_order(self, order_info: Dict[str, Any]) -> Dict[str, Any]:
        """주문 전송
        
        Args:
            order_info: 주문 정보
                - 계좌번호: str
                - 종목코드: str
                - 주문유형: str (1: 매도, 2: 매수, 3: 취소, 4: 정정)
                - 가격유형: str (00: 지정가, 03: 시장가, 05: 조건부지정가)
                - 주문수량: int
                - 주문가격: int (지정가 주문 시)
                - 원주문번호: str (취소/정정 주문 시)
        """
        try:
            # TR 입력값 설정
            input_data = {
                "계좌번호": order_info["계좌번호"],
                "종목코드": order_info["종목코드"],
                "주문구분": order_info["주문유형"],
                "호가유형": order_info["가격유형"],
                "주문수량": str(order_info["주문수량"]),
            }

            # 지정가 주문인 경우 주문가격 추가
            if "주문가격" in order_info:
                input_data["주문가격"] = str(order_info["주문가격"])

            # 취소/정정 주문인 경우 원주문번호 추가
            if "원주문번호" in order_info:
                input_data["원주문번호"] = order_info["원주문번호"]

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.SEND_ORDER,
                input_data=input_data
            )

            # 응답 처리
            result = {
                "order_no": response.get("주문번호"),
                "status": response.get("주문상태"),
                "message": response.get("메시지"),
                "error_code": response.get("에러코드"),
                "error_message": response.get("에러메시지")
            }

            # 로깅
            if result["error_code"]:
                self.logger.error(f"주문 실패: {result['error_message']}")
            else:
                self.logger.info(f"주문 성공: {result['message']}")

            return result

        except Exception as e:
            self.logger.error(f"주문 전송 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_order_status(self, order_no: str) -> Dict[str, Any]:
        """주문 상태 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "주문번호": order_no
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.ORDER_STATUS,
                input_data=input_data
            )

            # 응답 처리
            result = {
                "order_no": response.get("주문번호"),
                "stock_code": response.get("종목코드"),
                "order_type": response.get("주문구분"),
                "order_price": response.get("주문가격"),
                "order_quantity": response.get("주문수량"),
                "filled_quantity": response.get("체결수량"),
                "remaining_quantity": response.get("미체결수량"),
                "order_status": response.get("주문상태"),
                "order_time": response.get("주문시각"),
                "filled_time": response.get("체결시각")
            }

            return result

        except Exception as e:
            self.logger.error(f"주문 상태 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_order_history(self, 
                         account_no: str,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> Dict[str, Any]:
        """주문 내역 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "계좌번호": account_no
            }

            if start_date:
                input_data["시작일자"] = start_date
            if end_date:
                input_data["종료일자"] = end_date

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.ORDER_HISTORY,
                input_data=input_data
            )

            # 응답 처리
            orders = []
            for order in response.get("주문내역", []):
                orders.append({
                    "order_no": order.get("주문번호"),
                    "stock_code": order.get("종목코드"),
                    "stock_name": order.get("종목명"),
                    "order_type": order.get("주문구분"),
                    "order_price": order.get("주문가격"),
                    "order_quantity": order.get("주문수량"),
                    "filled_quantity": order.get("체결수량"),
                    "remaining_quantity": order.get("미체결수량"),
                    "order_status": order.get("주문상태"),
                    "order_time": order.get("주문시각"),
                    "filled_time": order.get("체결시각")
                })

            return {
                "orders": orders,
                "total_count": len(orders)
            }

        except Exception as e:
            self.logger.error(f"주문 내역 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            } 