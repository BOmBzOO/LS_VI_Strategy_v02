"""시장 전체 정보 TR API"""

from typing import Dict, Any, List, Optional
from api.tr.base import BaseAPI
from api.constants import TRCode, MarketType
from config.logging_config import setup_logger

class MarketTRAPI(BaseAPI):
    """시장 전체 정보 TR API"""

    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)

    def get_market_index(self, market_type: MarketType) -> Dict[str, Any]:
        """시장 지수 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "시장구분": market_type.value
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.MARKET_INDEX,
                input_data=input_data
            )

            # 응답 처리
            result = {
                "market_type": market_type.value,
                "index_name": response.get("지수명"),
                "current_index": response.get("현재지수", 0.0),
                "index_change": response.get("전일대비", 0.0),
                "change_ratio": response.get("등락률", 0.0),
                "trading_volume": response.get("거래량", 0),
                "trading_value": response.get("거래대금", 0),
                "market_status": response.get("시장상태")
            }

            return result

        except Exception as e:
            self.logger.error(f"시장 지수 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_market_stocks(self, market_type: MarketType) -> Dict[str, Any]:
        """시장 종목 리스트 조회 (t8430)

        Args:
            market_type (MarketType): 시장 구분 (MarketType.ALL: 전체, MarketType.KOSPI: 코스피, MarketType.KOSDAQ: 코스닥)

        Returns:
            Dict[str, Any]: 종목 리스트 응답
                - rsp_cd (str): 응답 코드 (00000: 정상)
                - rsp_msg (str): 응답 메시지
                - t8430OutBlock (List[Dict[str, Any]]): 종목 정보 리스트
                    - hname (str): 종목명
                    - shcode (str): 단축코드
                    - expcode (str): 확장코드
                    - etfgubun (str): ETF구분(1:ETF)
                    - uplmtprice (int): 상한가
                    - dnlmtprice (int): 하한가
                    - jnilclose (int): 전일가
                    - memedan (str): 주문수량단위
                    - recprice (int): 기준가
                    - gubun (str): 구분(1:코스피2:코스닥)
        """
        try:
            # 요청 데이터 구성
            input_data = {
                "t8430InBlock": {
                    "gubun": market_type.value
                }
            }
            
            # TR 요청
            response = self.request_tr(
                tr_code="t8430",
                tr_type=2,
                input_data=input_data,
                is_continuous=False
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"종목 리스트 조회 중 오류 발생: {str(e)}")
            return {
                "rsp_cd": "99999",
                "rsp_msg": str(e),
                "t8430OutBlock": []
            }

    def get_market_sectors(self, market_type: MarketType) -> Dict[str, Any]:
        """시장별 업종 정보 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "시장구분": market_type.value
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.MARKET_SECTORS,
                input_data=input_data
            )

            # 응답 처리
            sectors = []
            for sector in response.get("업종리스트", []):
                sectors.append({
                    "sector_code": sector.get("업종코드"),
                    "sector_name": sector.get("업종명"),
                    "current_index": sector.get("현재지수", 0.0),
                    "index_change": sector.get("전일대비", 0.0),
                    "change_ratio": sector.get("등락률", 0.0),
                    "trading_volume": sector.get("거래량", 0),
                    "trading_value": sector.get("거래대금", 0)
                })

            result = {
                "market_type": market_type.value,
                "total_count": len(sectors),
                "sectors": sectors
            }

            return result

        except Exception as e:
            self.logger.error(f"시장별 업종 정보 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_market_trading_info(self, 
                              market_type: MarketType,
                              investor_type: Optional[str] = None) -> Dict[str, Any]:
        """시장별 매매 동향 조회"""
        try:
            # TR 입력값 설정
            input_data = {
                "시장구분": market_type.value
            }

            if investor_type:
                input_data["투자자구분"] = investor_type

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.MARKET_TRADING_INFO,
                input_data=input_data
            )

            # 응답 처리
            investors = []
            for investor in response.get("투자자별매매", []):
                investors.append({
                    "investor_type": investor.get("투자자구분"),
                    "buy_volume": investor.get("매수수량", 0),
                    "sell_volume": investor.get("매도수량", 0),
                    "net_volume": investor.get("순매수수량", 0),
                    "buy_value": investor.get("매수금액", 0),
                    "sell_value": investor.get("매도금액", 0),
                    "net_value": investor.get("순매수금액", 0)
                })

            result = {
                "market_type": market_type.value,
                "trading_date": response.get("매매일자"),
                "investors": investors
            }

            return result

        except Exception as e:
            self.logger.error(f"시장별 매매 동향 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    