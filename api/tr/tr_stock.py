"""주식 시세/종목 정보 TR API"""

from typing import Dict, Any, List, Optional
from api.tr.tr_base import BaseAPI
from api.constants import TRCode
from config.logging_config import setup_logger

class StockTRAPI(BaseAPI):
    """주식 시세/종목 정보 TR API"""

    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """종목 기본 정보 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "종목코드": stock_code
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.STOCK_INFO,
                input_data=input_data
            )

            # 응답 처리
            result = {
                "stock_code": response.get("종목코드"),
                "stock_name": response.get("종목명"),
                "market_type": response.get("시장구분"),
                "sector": response.get("업종"),
                "par_value": response.get("액면가", 0),
                "listing_date": response.get("상장일자"),
                "capital": response.get("자본금", 0),
                "shares": response.get("상장주식수", 0)
            }

            return result

        except Exception as e:
            self.logger.error(f"종목 정보 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_stock_price(self, stock_code: str) -> Dict[str, Any]:
        """종목 현재가 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "t1102InBlock": {
                    "shcode": stock_code
                }
            }
            
            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.STOCK_PRICE,
                tr_type=2,  # 조회 TR
                input_data=input_data,
                is_continuous=False
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"현재가 조회 중 오류 발생: {str(e)}")
            return {
                "rsp_cd": "99999",
                "rsp_msg": str(e),
                "t1102OutBlock": {}
            }

    def get_stock_orderbook(self, stock_code: str) -> Dict[str, Any]:
        """종목 호가 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "t1105InBlock": {
                    "shcode": stock_code
                }
            }
            
            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.STOCK_ORDERBOOK,
                tr_type=2,  # 조회 TR
                input_data=input_data,
                is_continuous=False
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"호가 조회 중 오류 발생: {str(e)}")
            return {
                "rsp_cd": "99999",
                "rsp_msg": str(e),
                "t1105OutBlock": {}
            }

    def get_stock_chart(self,
                       stock_code: str,
                       interval: str,
                       count: Optional[int] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> Dict[str, Any]:
        """종목 차트 데이터 조회
        
        Args:
            stock_code: 종목코드
            interval: 차트 주기 (1일, 1주, 1월, 1분, 5분, ...)
            count: 요청 개수
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD)
        """
        try:
            # TR 입력값 설정
            input_data = {
                "t8410InBlock": {
                    "shcode": stock_code,
                    "gubun": "2",  # 0:틱, 1:분, 2:일, 3:주, 4:월
                    "qrycnt": count,  # 요청건수
                    "sdate": start_date,  # 시작일자
                    "edate": end_date,  # 종료일자
                    "cts_date": "",  # 연속일자
                    "comp_yn": "N",  # 압축여부
                    "sujung": "Y"  # 수정주가여부
                }
            }
            
            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.STOCK_CHART,
                tr_type=2,  # 조회 TR
                input_data=input_data,
                is_continuous=False
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"차트 데이터 조회 중 오류 발생: {str(e)}")
            return {
                "rsp_cd": "99999",
                "rsp_msg": str(e),
                "t8410OutBlock": {},
                "t8410OutBlock1": []
            } 