"""계좌 서비스 클래스"""

import os
from datetime import datetime
from dotenv import load_dotenv
from api.tr.tr_account import AccountTRAPI
from config.logging_config import setup_logger

class AccountService:
    """계좌 서비스 클래스"""
    
    def __init__(self, is_corporate: bool = False):
        """초기화
        
        Args:
            is_corporate (bool, optional): 법인 계정 여부. Defaults to False.
        """
        self.logger = setup_logger(__name__)
        self.is_corporate = is_corporate
        self._load_account_info()
        self.account_api = AccountTRAPI()
        
    def _load_account_info(self) -> None:
        """계좌 정보 로드
        
        Raises:
            ValueError: 필수 환경변수가 설정되지 않은 경우
        """
        load_dotenv()
        
        # 계좌번호 확인
        self.account_no = os.getenv('LS_ACCOUNT_NO')
        if not self.account_no:
            raise ValueError("LS_ACCOUNT_NO가 .env 파일에 설정되지 않았습니다.")
            
        # 접근 토큰 확인
        self.access_token = os.getenv('LS_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError("LS_ACCESS_TOKEN이 .env 파일에 설정되지 않았습니다.")
            
        # 법인계좌인 경우 MAC 주소 확인
        if self.is_corporate:
            self.mac_address = os.getenv('LS_MAC_ADDRESS')
            if not self.mac_address:
                raise ValueError("법인계좌는 LS_MAC_ADDRESS가 .env 파일에 설정되어야 합니다.")

    def _print_account_balance(self, balance_info: dict) -> None:
        """계좌 요약 정보 출력
        
        Args:
            balance_info (dict): 잔고 정보
        """
        try:
            print("\n" + "="*120)
            print(f"[계좌 현황] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*120)
            
            # 계좌 총괄 정보
            print(f"\n[계좌 총괄 정보]")
            print(f"추정순자산: {balance_info['total']['estimated_assets']:,}원")
            print(f"실현손익: {balance_info['total']['realized_profit']:,}원")
            print(f"매입금액: {balance_info['total']['total_purchase']:,}원")
            print(f"추정D2예수금: {balance_info['total']['estimated_d2']:,}원")
            print(f"평가금액: {balance_info['total']['total_evaluation']:,}원")
            print(f"평가손익: {balance_info['total']['total_profit']:,}원")
            
            # 보유종목 상세
            if balance_info['stocks']:
                print("\n[보유종목 상세]")
                print("-"*120)
                print(f"{'종목명':20} {'보유수량':>8} {'매도가능':>8} {'평균단가':>12} {'현재가':>12} "
                      f"{'평가금액':>15} {'평가손익':>12} {'수익률':>8} {'보유비중':>8}")
                print("-"*120)
                
                for stock in balance_info['stocks']:
                    # 기본 정보 출력
                    print(f"{stock['stock_name']:20} {stock['quantity']:>8,} {stock['available_quantity']:>8,} "
                          f"{stock['average_price']:>12,} {stock['current_price']:>12,} {stock['evaluation_amount']:>15,} "
                          f"{stock['profit_loss']:>12,} {stock['profit_loss_rate']:>7.2f}% {stock['holding_ratio']:>7.2f}%")
                    
                    # 매매 정보가 있는 경우 출력
                    if any(stock['today'].values()) or any(stock['yesterday'].values()):
                        print(f"  ├ 당일: 매수({stock['today']['buy_amount']:,}원@{stock['today']['buy_price']:,}) "
                              f"매도({stock['today']['sell_amount']:,}원@{stock['today']['sell_price']:,})")
                        print(f"  ├ 전일: 매수({stock['yesterday']['buy_amount']:,}원@{stock['yesterday']['buy_price']:,}) "
                              f"매도({stock['yesterday']['sell_amount']:,}원@{stock['yesterday']['sell_price']:,})")
                    
                    # 수수료 및 세금 정보 출력
                    print(f"  └ 비용: 수수료({stock['fee']:,}원) 세금({stock['tax']:,}원) "
                          f"이자({stock['interest']:,}원)")
            else:
                print("\n보유중인 종목이 없습니다.")
                
            print("\n" + "="*120)
            
        except Exception as e:
            self.logger.error(f"계좌 요약 정보 출력 중 오류 발생: {str(e)}")
            
            
    def get_account_balance(self) -> dict:
        """계좌 잔고 조회
        
        Returns:
            dict: 계좌 잔고 정보
            {
                "estimated_assets": 추정순자산,
                "realized_profit": 실현손익,
                "total_purchase": 매입금액,
                "estimated_d2": 추정D2예수금,
                "total_evaluation": 평가금액,
                "total_profit_loss": 평가손익,
                "stocks": [
                    {
                        "stock_code": 종목코드,
                        "stock_name": 종목명,
                        "quantity": 잔고수량,
                        "available_quantity": 매도가능수량,
                        "average_price": 평균단가,
                        "purchase_amount": 매입금액,
                        "loan_amount": 대출금액,
                        "loan_date": 대출일자,
                        "current_price": 현재가,
                        "evaluation_amount": 평가금액,
                        "profit_loss": 평가손익,
                        "profit_loss_ratio": 수익률,
                        "holding_ratio": 보유비중,
                        "fee": 수수료,
                        "tax": 제세금,
                        "interest": 신용이자,
                        "today": {
                            "buy_amount": 당일매수금액,
                            "buy_price": 당일매수단가,
                            "sell_amount": 당일매도금액,
                            "sell_price": 당일매도단가
                        },
                        "yesterday": {
                            "buy_amount": 전일매수금액,
                            "buy_price": 전일매수단가,
                            "sell_amount": 전일매도금액,
                            "sell_price": 전일매도단가
                        }
                    }
                ]
            }
        """
        try:
            balance_info = self.account_api.get_account_balance()
            
            if "error_code" in balance_info:
                self.logger.error(f"잔고 조회 실패: {balance_info['error_message']}")
                return balance_info
                
            self._print_account_balance(balance_info)
            return balance_info
            
        except Exception as e:
            self.logger.error(f"계좌 잔고 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            } 