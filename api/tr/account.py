"""계좌 TR API"""

from typing import Dict, Any, List, Optional
from api.tr.base import BaseAPI
from api.constants import TRCode
from config.logging_config import setup_logger

class AccountTRAPI(BaseAPI):
    """계좌 TR API"""

    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)

    def get_account_info(self, account_no: str) -> Dict[str, Any]:
        """계좌 기본 정보 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "계좌번호": account_no
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.ACCOUNT_INFO,
                input_data=input_data
            )

            # 응답 처리
            result = {
                "account_no": response.get("계좌번호"),
                "account_name": response.get("계좌명"),
                "account_type": response.get("계좌구분"),
                "deposit": response.get("예수금", 0),
                "available_amount": response.get("주문가능금액", 0),
                "total_balance": response.get("잔고평가금액", 0),
                "total_profit_loss": response.get("평가손익금액", 0),
                "profit_loss_ratio": response.get("수익률", 0.0)
            }

            return result

        except Exception as e:
            self.logger.error(f"계좌 정보 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_balance(self, account_no: str) -> Dict[str, Any]:
        """계좌 잔고 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "계좌번호": account_no
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.BALANCE,
                input_data=input_data
            )

            # 응답 처리
            stocks = []
            for stock in response.get("보유종목", []):
                stocks.append({
                    "stock_code": stock.get("종목코드"),
                    "stock_name": stock.get("종목명"),
                    "quantity": stock.get("보유수량", 0),
                    "average_price": stock.get("평균단가", 0),
                    "current_price": stock.get("현재가", 0),
                    "total_amount": stock.get("평가금액", 0),
                    "profit_loss": stock.get("평가손익", 0),
                    "profit_loss_ratio": stock.get("수익률", 0.0),
                    "available_quantity": stock.get("매도가능수량", 0)
                })

            result = {
                "account_no": response.get("계좌번호"),
                "total_balance": response.get("잔고평가금액", 0),
                "total_profit_loss": response.get("평가손익금액", 0),
                "profit_loss_ratio": response.get("수익률", 0.0),
                "stocks": stocks
            }

            return result

        except Exception as e:
            self.logger.error(f"잔고 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_deposit(self, account_no: str) -> Dict[str, Any]:
        """예수금 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "계좌번호": account_no
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.DEPOSIT,
                input_data=input_data
            )

            # 응답 처리
            result = {
                "account_no": response.get("계좌번호"),
                "deposit": response.get("예수금", 0),
                "d1": response.get("D+1예수금", 0),
                "d2": response.get("D+2예수금", 0),
                "available_amount": response.get("주문가능금액", 0),
                "withdraw_available": response.get("출금가능금액", 0),
                "loan_amount": response.get("대출금액", 0)
            }

            return result

        except Exception as e:
            self.logger.error(f"예수금 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_trading_history(self,
                          account_no: str,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> Dict[str, Any]:
        """매매 이력 조회"""
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
                tr_code=TRCode.TRADING_HISTORY,
                input_data=input_data
            )

            # 응답 처리
            trades = []
            for trade in response.get("매매이력", []):
                trades.append({
                    "trade_date": trade.get("매매일자"),
                    "stock_code": trade.get("종목코드"),
                    "stock_name": trade.get("종목명"),
                    "trade_type": trade.get("매매구분"),
                    "quantity": trade.get("매매수량", 0),
                    "price": trade.get("매매단가", 0),
                    "amount": trade.get("매매금액", 0),
                    "fee": trade.get("수수료", 0),
                    "tax": trade.get("세금", 0),
                    "profit_loss": trade.get("손익금액", 0)
                })

            result = {
                "trades": trades,
                "total_count": len(trades),
                "total_profit_loss": sum(t["profit_loss"] for t in trades)
            }

            return result

        except Exception as e:
            self.logger.error(f"매매 이력 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            } 