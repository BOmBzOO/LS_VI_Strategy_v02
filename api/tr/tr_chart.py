"""차트 TR API"""

from typing import Dict, Any, Optional
from datetime import datetime
from api.tr.tr_base import BaseAPI
from api.constants import TRCode
from config.logging_config import setup_logger

class ChartTRAPI(BaseAPI):
    """차트 TR API"""

    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)

    def get_minute_chart(
        self,
        stock_code: str,
        minute_unit: int = 1,
        request_count: int = 500,
        end_date: str = "99999999",
        start_date: str = "",
        is_compressed: bool = False,
        is_continuous: bool = False,
        cts_date: str = "",
        cts_time: str = ""
    ) -> Dict[str, Any]:
        """N분봉 차트 조회 (t8412)

        Args:
            stock_code (str): 종목코드
            minute_unit (int, optional): N분 단위. Defaults to 1.
            request_count (int, optional): 요청건수(최대-압축:2000, 비압축:500). Defaults to 500.
            end_date (str, optional): 종료일자(YYYYMMDD). Defaults to "99999999".
            start_date (str, optional): 시작일자(YYYYMMDD). Defaults to "".
            is_compressed (bool, optional): 압축여부. Defaults to False.
            is_continuous (bool, optional): 연속조회 여부. Defaults to False.
            cts_date (str, optional): 연속일자. Defaults to "".
            cts_time (str, optional): 연속시간. Defaults to "".

        Returns:
            Dict[str, Any]: N분봉 차트 데이터
            {
                "chart_summary": {
                    "stock_code": 종목코드,
                    "yesterday": {
                        "open": 전일시가,
                        "high": 전일고가,
                        "low": 전일저가,
                        "close": 전일종가,
                        "volume": 전일거래량
                    },
                    "today": {
                        "open": 당일시가,
                        "high": 당일고가,
                        "low": 당일저가,
                        "close": 당일종가
                    },
                    "price_limit": {
                        "upper": 상한가,
                        "lower": 하한가
                    },
                    "trading_time": {
                        "start": 장시작시간,
                        "end": 장종료시간,
                        "simultaneous": 동시호가처리시간
                    },
                    "record_count": 레코드카운트
                },
                "charts": [
                    {
                        "date": 날짜,
                        "time": 시간,
                        "open": 시가,
                        "high": 고가,
                        "low": 저가,
                        "close": 종가,
                        "volume": 거래량,
                        "value": 거래대금,
                        "modification": {
                            "type": 수정구분,
                            "rate": 수정비율
                        },
                        "sign": 종가등락구분
                    }
                ],
                "continuous": {
                    "date": 연속일자,
                    "time": 연속시간
                }
            }
        """
        try:
            # TR 입력값 설정
            input_data = {
                "t8412InBlock": {
                    "shcode": stock_code,           # 종목코드
                    "ncnt": minute_unit,            # N분 단위
                    "qrycnt": request_count,        # 요청건수
                    "nday": "0",                    # 조회영업일수 미사용
                    "sdate": start_date,            # 시작일자
                    "stime": "",                    # 시작시간(미사용)
                    "edate": end_date,              # 종료일자
                    "etime": "",                    # 종료시간(미사용)
                    "cts_date": cts_date,           # 연속일자
                    "cts_time": cts_time,           # 연속시간
                    "comp_yn": "Y" if is_compressed else "N"  # 압축여부
                }
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.STOCK_MINUTE_CHART,
                input_data=input_data,
                is_continuous=is_continuous
            )

            # 응답 코드 확인
            if "rsp_cd" in response:
                if response["rsp_cd"] != "00000":  # 00000은 성공 코드
                    self.logger.error(f"TR 요청 실패: {response['rsp_cd']} - {response.get('rsp_msg', '')}")
                    return {
                        "error_code": response["rsp_cd"],
                        "error_message": response.get("rsp_msg", "")
                    }
            elif "error_code" in response:
                self.logger.error(f"TR 요청 실패: {response['error_code']} - {response.get('error_message', '')}")
                return response

            # 응답 데이터 변환
            try:
                result = {
                    "chart_summary": {
                        "stock_code": response["t8412OutBlock"]["shcode"],
                        "yesterday": {
                            "open": response["t8412OutBlock"]["jisiga"],
                            "high": response["t8412OutBlock"]["jihigh"],
                            "low": response["t8412OutBlock"]["jilow"],
                            "close": response["t8412OutBlock"]["jiclose"],
                            "volume": response["t8412OutBlock"]["jivolume"]
                        },
                        "today": {
                            "open": response["t8412OutBlock"]["disiga"],
                            "high": response["t8412OutBlock"]["dihigh"],
                            "low": response["t8412OutBlock"]["dilow"],
                            "close": response["t8412OutBlock"]["diclose"]
                        },
                        "price_limit": {
                            "upper": response["t8412OutBlock"]["highend"],
                            "lower": response["t8412OutBlock"]["lowend"]
                        },
                        "trading_time": {
                            "start": response["t8412OutBlock"]["s_time"],
                            "end": response["t8412OutBlock"]["e_time"],
                            "simultaneous": response["t8412OutBlock"]["dshmin"]
                        },
                        "record_count": response["t8412OutBlock"]["rec_count"]
                    },
                    "charts": [],
                    "continuous": {
                        "date": response["t8412OutBlock"]["cts_date"],
                        "time": response["t8412OutBlock"]["cts_time"]
                    }
                }

                # 차트 데이터 변환
                for chart in response.get("t8412OutBlock1", []):
                    result["charts"].append({
                        "date": chart["date"],
                        "time": chart["time"],
                        "open": chart["open"],
                        "high": chart["high"],
                        "low": chart["low"],
                        "close": chart["close"],
                        "volume": chart["jdiff_vol"],
                        "value": chart["value"],
                        "modification": {
                            "type": chart["jongchk"],
                            "rate": chart["rate"]
                        },
                        "sign": chart["sign"]
                    })

                return result

            except KeyError as e:
                self.logger.error(f"응답 데이터 처리 중 오류 발생: {str(e)}")
                return {
                    "error_code": "9999",
                    "error_message": f"응답 데이터 처리 중 오류 발생: {str(e)}"
                }

        except Exception as e:
            self.logger.error(f"N분봉 차트 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def get_tick_chart(
        self,
        stock_code: str,
        tick_unit: int = 1,
        request_count: int = 500,
        end_date: str = "99999999",
        start_date: str = "",
        is_compressed: bool = False,
        is_continuous: bool = False,
        cts_date: str = "",
        cts_time: str = ""
    ) -> Dict[str, Any]:
        """N틱 차트 조회 (t8411)

        Args:
            stock_code (str): 종목코드
            tick_unit (int, optional): N틱 단위. Defaults to 1.
            request_count (int, optional): 요청건수(최대-압축:2000, 비압축:500). Defaults to 500.
            end_date (str, optional): 종료일자(YYYYMMDD). Defaults to "99999999".
            start_date (str, optional): 시작일자(YYYYMMDD). Defaults to "".
            is_compressed (bool, optional): 압축여부. Defaults to False.
            is_continuous (bool, optional): 연속조회 여부. Defaults to False.
            cts_date (str, optional): 연속일자. Defaults to "".
            cts_time (str, optional): 연속시간. Defaults to "".

        Returns:
            Dict[str, Any]: N틱 차트 데이터
            {
                "chart_summary": {
                    "stock_code": 종목코드,
                    "yesterday": {
                        "open": 전일시가,
                        "high": 전일고가,
                        "low": 전일저가,
                        "close": 전일종가,
                        "volume": 전일거래량
                    },
                    "today": {
                        "open": 당일시가,
                        "high": 당일고가,
                        "low": 당일저가,
                        "close": 당일종가
                    },
                    "price_limit": {
                        "upper": 상한가,
                        "lower": 하한가
                    },
                    "trading_time": {
                        "start": 장시작시간,
                        "end": 장종료시간,
                        "simultaneous": 동시호가처리시간
                    },
                    "record_count": 레코드카운트
                },
                "charts": [
                    {
                        "date": 날짜,
                        "time": 시간,
                        "open": 시가,
                        "high": 고가,
                        "low": 저가,
                        "close": 종가,
                        "volume": 거래량,
                        "modification": {
                            "type": 수정구분,
                            "rate": 수정비율,
                            "price_type": 수정주가반영항목
                        }
                    }
                ],
                "continuous": {
                    "date": 연속일자,
                    "time": 연속시간
                }
            }
        """
        try:
            # TR 입력값 설정
            input_data = {
                "t8411InBlock": {
                    "shcode": stock_code,           # 종목코드
                    "ncnt": tick_unit,              # N틱 단위
                    "qrycnt": request_count,        # 요청건수
                    "nday": "0",                    # 조회영업일수 미사용
                    "sdate": start_date,            # 시작일자
                    "stime": "",                    # 시작시간(미사용)
                    "edate": end_date,              # 종료일자
                    "etime": "",                    # 종료시간(미사용)
                    "cts_date": cts_date,           # 연속일자
                    "cts_time": cts_time,           # 연속시간
                    "comp_yn": "Y" if is_compressed else "N"  # 압축여부
                }
            }

            # TR 요청
            response = self.request_tr(
                tr_code=TRCode.STOCK_TICK_CHART,
                input_data=input_data,
                is_continuous=is_continuous
            )

            # 응답 코드 확인
            if "rsp_cd" in response:
                if response["rsp_cd"] != "00000":  # 00000은 성공 코드
                    self.logger.error(f"TR 요청 실패: {response['rsp_cd']} - {response.get('rsp_msg', '')}")
                    return {
                        "error_code": response["rsp_cd"],
                        "error_message": response.get("rsp_msg", "")
                    }
            elif "error_code" in response:
                self.logger.error(f"TR 요청 실패: {response['error_code']} - {response.get('error_message', '')}")
                return response

            # 응답 데이터 변환
            try:
                result = {
                    "chart_summary": {
                        "stock_code": response["t8411OutBlock"]["shcode"],
                        "yesterday": {
                            "open": response["t8411OutBlock"]["jisiga"],
                            "high": response["t8411OutBlock"]["jihigh"],
                            "low": response["t8411OutBlock"]["jilow"],
                            "close": response["t8411OutBlock"]["jiclose"],
                            "volume": response["t8411OutBlock"]["jivolume"]
                        },
                        "today": {
                            "open": response["t8411OutBlock"]["disiga"],
                            "high": response["t8411OutBlock"]["dihigh"],
                            "low": response["t8411OutBlock"]["dilow"],
                            "close": response["t8411OutBlock"]["diclose"]
                        },
                        "price_limit": {
                            "upper": response["t8411OutBlock"]["highend"],
                            "lower": response["t8411OutBlock"]["lowend"]
                        },
                        "trading_time": {
                            "start": response["t8411OutBlock"]["s_time"],
                            "end": response["t8411OutBlock"]["e_time"],
                            "simultaneous": response["t8411OutBlock"]["dshmin"]
                        },
                        "record_count": response["t8411OutBlock"]["rec_count"]
                    },
                    "charts": [],
                    "continuous": {
                        "date": response["t8411OutBlock"]["cts_date"],
                        "time": response["t8411OutBlock"]["cts_time"]
                    }
                }

                # 차트 데이터 변환
                for chart in response.get("t8411OutBlock1", []):
                    result["charts"].append({
                        "date": chart["date"],
                        "time": chart["time"],
                        "open": chart["open"],
                        "high": chart["high"],
                        "low": chart["low"],
                        "close": chart["close"],
                        "volume": chart["jdiff_vol"],
                        "modification": {
                            "type": chart["jongchk"],
                            "rate": chart["rate"],
                            "price_type": chart["pricechk"]
                        }
                    })

                return result

            except KeyError as e:
                self.logger.error(f"응답 데이터 처리 중 오류 발생: {str(e)}")
                return {
                    "error_code": "9999",
                    "error_message": f"응답 데이터 처리 중 오류 발생: {str(e)}"
                }

        except Exception as e:
            self.logger.error(f"N틱 차트 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }
