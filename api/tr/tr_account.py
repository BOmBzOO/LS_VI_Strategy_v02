"""계좌 TR API"""

from typing import Dict, Any, List, Optional
from api.tr.tr_base import BaseAPI
from api.constants import TRCode
from config.logging_config import setup_logger

class AccountTRAPI(BaseAPI):
    """계좌 TR API"""

    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)

    
    def get_account_deposit(self, account_no: str) -> Dict[str, Any]:
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

    def get_account_history(self,
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
                tr_code=TRCode.ACCOUNT_HISTORY,
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

    def get_account_balance(self) -> Dict[str, Any]:
        """주식잔고2 조회 (t0424)
        
        Args:
            account_no (str): 계좌번호
            
        Returns:
            Dict[str, Any]: 주식잔고 정보
        """
        try:
            # TR 입력값 설정
            input_data = {
                "t0424InBlock": {
                    "prcgb": "",     # 단가구분
                    "chegb": "",     # 체결구분
                    "dangb": "",     # 단일가구분
                    "charge": "",    # 제비용포함여부
                    "cts_expcode": "" # CTS_종목번호
                }
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.ACCOUNT_BALANCE,
                input_data=input_data
            )

            if "error_code" in response:
                return response

            # 응답 데이터 변환
            result = {
                "total": {
                    "estimated_assets": response["t0424OutBlock"]["sunamt"],      # 추정순자산
                    "realized_profit": response["t0424OutBlock"]["dtsunik"],      # 실현손익
                    "total_purchase": response["t0424OutBlock"]["mamt"],          # 매입금액
                    "estimated_d2": response["t0424OutBlock"]["sunamt1"],         # 추정D2예수금
                    "total_evaluation": response["t0424OutBlock"]["tappamt"],     # 평가금액
                    "total_profit": response["t0424OutBlock"]["tdtsunik"]         # 평가손익
                },
                "stocks": []
            }

            # 보유종목 정보
            for stock in response.get("t0424OutBlock1", []):
                stock_info = {
                    "stock_code": stock["expcode"],           # 종목코드
                    "stock_name": stock["hname"],             # 종목명
                    "quantity": stock["janqty"],              # 잔고수량
                    "available_quantity": stock["mdposqt"],   # 매도가능수량
                    "average_price": stock["pamt"],           # 평균단가
                    "purchase_amount": stock["mamt"],         # 매입금액
                    "loan_amount": stock["sinamt"],           # 대출금액
                    "loan_date": stock["loandt"],             # 대출일자
                    "current_price": stock["price"],          # 현재가
                    "evaluation_amount": stock["appamt"],     # 평가금액
                    "profit_loss": stock["dtsunik"],          # 평가손익
                    "profit_loss_rate": stock["sunikrt"],     # 수익률
                    "fee": stock["fee"],                      # 수수료
                    "tax": stock["tax"],                      # 제세금
                    "interest": stock["sininter"],            # 신용이자
                    "today": {
                        "buy_amount": stock["msat"],          # 당일매수금액
                        "buy_price": stock["mpms"],           # 당일매수단가
                        "sell_amount": stock["mdat"],         # 당일매도금액
                        "sell_price": stock["mpmd"]           # 당일매도단가
                    },
                    "yesterday": {
                        "buy_amount": stock["jsat"],          # 전일매수금액
                        "buy_price": stock["jpms"],           # 전일매수단가
                        "sell_amount": stock["jdat"],         # 전일매도금액
                        "sell_price": stock["jpmd"]           # 전일매도단가
                    }
                }
                result["stocks"].append(stock_info)

            return result

        except Exception as e:
            self.logger.error(f"주식잔고2 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            } 