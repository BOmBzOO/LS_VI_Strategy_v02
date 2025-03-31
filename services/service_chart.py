"""차트 서비스 클래스"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from api.tr.tr_chart import ChartTRAPI
from config.logging_config import setup_logger

class ChartService:
    """차트 서비스 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.chart_api = ChartTRAPI()
        self._setup_matplotlib_font()
        
    def _setup_matplotlib_font(self) -> None:
        """matplotlib 한글 폰트 설정"""
        try:
            # 나눔고딕 폰트 경로 (Windows)
            font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
            font_prop = fm.FontProperties(fname=font_path)
            
            # 폰트 설정
            plt.rcParams['font.family'] = font_prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
            
            self.logger.info("matplotlib 한글 폰트 설정 완료")
            
        except Exception as e:
            self.logger.warning(f"matplotlib 한글 폰트 설정 실패: {str(e)}")
            self.logger.warning("기본 폰트를 사용합니다.")
        
    def _print_minute_chart(self, chart_data: dict) -> None:
        """분봉 차트 데이터 출력
        
        Args:
            chart_data (dict): 차트 데이터
        """
        try:
            print("\n" + "="*120)
            print(f"[{chart_data['chart_summary']['stock_code']} 분봉 차트] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*120)
            
            # 전일 정보 출력
            print("\n[전일 정보]")
            print(f"시가: {chart_data['chart_summary']['yesterday']['open']:,}")
            print(f"고가: {chart_data['chart_summary']['yesterday']['high']:,}")
            print(f"저가: {chart_data['chart_summary']['yesterday']['low']:,}")
            print(f"종가: {chart_data['chart_summary']['yesterday']['close']:,}")
            print(f"거래량: {chart_data['chart_summary']['yesterday']['volume']:,}")
            
            # 당일 정보 출력
            print("\n[당일 정보]")
            print(f"시가: {chart_data['chart_summary']['today']['open']:,}")
            print(f"고가: {chart_data['chart_summary']['today']['high']:,}")
            print(f"저가: {chart_data['chart_summary']['today']['low']:,}")
            print(f"종가: {chart_data['chart_summary']['today']['close']:,}")
            
            # 가격제한 정보 출력
            print("\n[가격제한]")
            print(f"상한가: {chart_data['chart_summary']['price_limit']['upper']:,}")
            print(f"하한가: {chart_data['chart_summary']['price_limit']['lower']:,}")
            
            # 거래시간 정보 출력
            print("\n[거래시간]")
            print(f"장시작: {chart_data['chart_summary']['trading_time']['start']}")
            print(f"장종료: {chart_data['chart_summary']['trading_time']['end']}")
            print(f"동시호가: {chart_data['chart_summary']['trading_time']['simultaneous']}분")
            
            # 차트 데이터 출력
            if chart_data['charts']:
                print("\n[차트 데이터]")
                print("-"*120)
                print(f"{'일자':10} {'시간':10} {'시가':>10} {'고가':>10} {'저가':>10} {'종가':>10} "
                      f"{'거래량':>12} {'거래대금':>15} {'수정구분':>8} {'수정비율':>8} {'등락구분':>6}")
                print("-"*120)
                
                for chart in chart_data['charts']:
                    print(f"{chart['date']:10} {chart['time']:10} {chart['open']:>10,} {chart['high']:>10,} "
                          f"{chart['low']:>10,} {chart['close']:>10,} {chart['volume']:>12,} {chart['value']:>15,} "
                          f"{chart['modification']['type']:>8} {chart['modification']['rate']:>8} {chart['sign']:>6}")
            else:
                print("\n차트 데이터가 없습니다.")
                
            print("\n" + "="*120)
            
        except Exception as e:
            self.logger.error(f"차트 데이터 출력 중 오류 발생: {str(e)}")
            
    def _prepare_plot_data(self, chart_data: dict) -> Tuple[List[datetime], List[float], List[int]]:
        """차트 데이터를 플로팅용 데이터로 변환
        
        Args:
            chart_data (dict): 차트 데이터
            
        Returns:
            Tuple[List[datetime], List[float], List[int]]: 날짜, 가격, 거래량 리스트
        """
        dates = []
        prices = []
        volumes = []
        
        for chart in chart_data['charts']:
            # 날짜와 시간 결합
            date_str = f"{chart['date']} {chart['time']}"
            date = datetime.strptime(date_str, "%Y%m%d %H%M%S")
            # KST로 변환 (UTC+9)
            date = date + timedelta(hours=9)
            dates.append(date)
            
            # 가격과 거래량
            prices.append(chart['close'])
            volumes.append(chart['volume'])
            
        return dates, prices, volumes
        
    def plot_chart(self, chart_data: dict) -> None:
        """차트 데이터 시각화
        
        Args:
            chart_data (dict): 차트 데이터
        """
        try:
            # 데이터 준비
            dates, prices, volumes = self._prepare_plot_data(chart_data)
            
            if not dates:
                self.logger.warning("플로팅할 데이터가 없습니다.")
                return
            
            # 그래프 설정
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[3, 1])
            fig.suptitle(f"{chart_data['chart_summary']['stock_code']} 분봉 차트 - {dates[-1].strftime('%Y-%m-%d')} (KST)", 
                        fontsize=16, y=0.95)
            
            # 가격 차트 (위)
            ax1.plot(dates, prices, 'b-', label='종가')
            ax1.grid(True)
            ax1.set_ylabel('가격 (원)', fontsize=12)
            ax1.legend(fontsize=10)
            
            # 가격 차트 Y축 범위 설정
            price_margin = (max(prices) - min(prices)) * 0.1
            ax1.set_ylim(min(prices) - price_margin, max(prices) + price_margin)
            
            # X축 날짜 포맷 설정
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            
            # 거래량 차트 (아래)
            ax2.bar(dates, volumes, color='gray', alpha=0.5, label='거래량')
            ax2.grid(True)
            ax2.set_ylabel('거래량 (주)', fontsize=12)
            ax2.legend(fontsize=10)
            
            # 거래량 차트 Y축 범위 설정
            volume_margin = max(volumes) * 0.1
            ax2.set_ylim(0, max(volumes) + volume_margin)
            
            # X축 날짜 포맷 설정
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax2.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            
            # 레이아웃 조정
            plt.tight_layout()
            
            # 차트 표시
            plt.show()
            
        except Exception as e:
            self.logger.error(f"차트 플로팅 중 오류 발생: {str(e)}")
            
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
        cts_time: str = "",
        print_output: bool = True,
        plot_chart: bool = True
    ) -> Dict[str, Any]:
        """분봉 차트 조회
        
        Args:
            stock_code (str): 종목코드
            minute_unit (int, optional): N분 단위. Defaults to 1.
            request_count (int, optional): 요청건수. Defaults to 500.
            end_date (str, optional): 종료일자. Defaults to "99999999".
            start_date (str, optional): 시작일자. Defaults to "".
            is_compressed (bool, optional): 압축여부. Defaults to False.
            is_continuous (bool, optional): 연속조회 여부. Defaults to False.
            cts_date (str, optional): 연속일자. Defaults to "".
            cts_time (str, optional): 연속시간. Defaults to "".
            print_output (bool, optional): 결과 출력 여부. Defaults to True.
            plot_chart (bool, optional): 차트 플로팅 여부. Defaults to True.
            
        Returns:
            Dict[str, Any]: 분봉 차트 데이터
        """
        try:
            # 차트 데이터 조회
            chart_data = self.chart_api.get_minute_chart(
                stock_code=stock_code,
                minute_unit=minute_unit,
                request_count=request_count,
                end_date=end_date,
                start_date=start_date,
                is_compressed=is_compressed,
                is_continuous=is_continuous,
                cts_date=cts_date,
                cts_time=cts_time
            )
            
            if "error_code" in chart_data:
                self.logger.error(f"차트 조회 실패: {chart_data['error_message']}")
                return chart_data
            
            # 결과 출력
            if print_output:
                self._print_minute_chart(chart_data)
                
            # 차트 플로팅
            if plot_chart:
                self.plot_chart(chart_data)
                
            return chart_data
            
        except Exception as e:
            self.logger.error(f"분봉 차트 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            }

    def _print_tick_chart(self, chart_data: dict) -> None:
        """틱 차트 데이터 출력
        
        Args:
            chart_data (dict): 차트 데이터
        """
        try:
            print("\n" + "="*120)
            print(f"[{chart_data['chart_summary']['stock_code']} 틱 차트] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*120)
            
            # 전일 정보 출력
            print("\n[전일 정보]")
            print(f"시가: {chart_data['chart_summary']['yesterday']['open']:,}")
            print(f"고가: {chart_data['chart_summary']['yesterday']['high']:,}")
            print(f"저가: {chart_data['chart_summary']['yesterday']['low']:,}")
            print(f"종가: {chart_data['chart_summary']['yesterday']['close']:,}")
            print(f"거래량: {chart_data['chart_summary']['yesterday']['volume']:,}")
            
            # 당일 정보 출력
            print("\n[당일 정보]")
            print(f"시가: {chart_data['chart_summary']['today']['open']:,}")
            print(f"고가: {chart_data['chart_summary']['today']['high']:,}")
            print(f"저가: {chart_data['chart_summary']['today']['low']:,}")
            print(f"종가: {chart_data['chart_summary']['today']['close']:,}")
            
            # 가격제한 정보 출력
            print("\n[가격제한]")
            print(f"상한가: {chart_data['chart_summary']['price_limit']['upper']:,}")
            print(f"하한가: {chart_data['chart_summary']['price_limit']['lower']:,}")
            
            # 거래시간 정보 출력
            print("\n[거래시간]")
            print(f"장시작: {chart_data['chart_summary']['trading_time']['start']}")
            print(f"장종료: {chart_data['chart_summary']['trading_time']['end']}")
            print(f"동시호가: {chart_data['chart_summary']['trading_time']['simultaneous']}분")
            
            # 차트 데이터 출력
            if chart_data['charts']:
                print("\n[차트 데이터]")
                print("-"*120)
                print(f"{'일자':10} {'시간':10} {'시가':>10} {'고가':>10} {'저가':>10} {'종가':>10} "
                      f"{'거래량':>12} {'수정구분':>8} {'수정비율':>8} {'수정주가반영항목':>12}")
                print("-"*120)
                
                for chart in chart_data['charts']:
                    print(f"{chart['date']:10} {chart['time']:10} {chart['open']:>10,} {chart['high']:>10,} "
                          f"{chart['low']:>10,} {chart['close']:>10,} {chart['volume']:>12,} "
                          f"{chart['modification']['type']:>8} {chart['modification']['rate']:>8} "
                          f"{chart['modification']['price_type']:>12}")
            else:
                print("\n차트 데이터가 없습니다.")
                
            print("\n" + "="*120)
            
        except Exception as e:
            self.logger.error(f"차트 데이터 출력 중 오류 발생: {str(e)}")

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
        cts_time: str = "",
        print_output: bool = True,
        plot_chart: bool = True
    ) -> Dict[str, Any]:
        """틱 차트 조회
        
        Args:
            stock_code (str): 종목코드
            tick_unit (int, optional): N틱 단위. Defaults to 1.
            request_count (int, optional): 요청건수. Defaults to 500.
            end_date (str, optional): 종료일자. Defaults to "99999999".
            start_date (str, optional): 시작일자. Defaults to "".
            is_compressed (bool, optional): 압축여부. Defaults to False.
            is_continuous (bool, optional): 연속조회 여부. Defaults to False.
            cts_date (str, optional): 연속일자. Defaults to "".
            cts_time (str, optional): 연속시간. Defaults to "".
            print_output (bool, optional): 결과 출력 여부. Defaults to True.
            plot_chart (bool, optional): 차트 플로팅 여부. Defaults to True.
            
        Returns:
            Dict[str, Any]: 틱 차트 데이터
        """
        try:
            # 차트 데이터 조회
            chart_data = self.chart_api.get_tick_chart(
                stock_code=stock_code,
                tick_unit=tick_unit,
                request_count=request_count,
                end_date=end_date,
                start_date=start_date,
                is_compressed=is_compressed,
                is_continuous=is_continuous,
                cts_date=cts_date,
                cts_time=cts_time
            )
            
            if "error_code" in chart_data:
                self.logger.error(f"차트 조회 실패: {chart_data['error_message']}")
                return chart_data
            
            # 결과 출력
            if print_output:
                self._print_tick_chart(chart_data)
                
            # 차트 플로팅
            if plot_chart:
                self.plot_chart(chart_data)
                
            return chart_data
            
        except Exception as e:
            self.logger.error(f"틱 차트 조회 중 오류 발생: {str(e)}")
            return {
                "error_code": "9999",
                "error_message": str(e)
            } 