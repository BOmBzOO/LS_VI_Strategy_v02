"""VI 체결 모니터링 전략

VI 발동 종목의 체결 정보를 실시간으로 모니터링하는 전략 클래스를 제공합니다.
"""

from typing import Dict, Any, Optional, Set
from datetime import datetime
import asyncio
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import setup_logger
from api.constants import MarketType
from services.auth_token_service import TokenService
from services.market_data_service import MarketService
from strategy.base_strategy import BaseStrategy
from services.vi_ccld_monitor_service import VICCLDMonitorService

class VICCLDStrategy(BaseStrategy):
    """VI 체결 모니터링 전략 클래스"""
    
    def __init__(self):
        """초기화"""
        super().__init__("VI_CCLD_Monitoring")
        self.token_service = TokenService()
        self.market_service = MarketService()
        self.monitor_service: Optional[VICCLDMonitorService] = None
        self._market_stocks: Dict[str, str] = {}  # 종목코드: 시장구분 매핑
        self._active_vi_stocks: Set[str] = set()  # 현재 VI 발동 중인 종목 코드
        
        self.state.update({
            "monitoring_active": False,
            "active_vi_count": 0,
            "ccld_monitoring_count": 0,
            "market_data_loaded": False,
            "last_vi_event_time": None,
            "last_ccld_event_time": None,
            "total_vi_events": 0,
            "total_ccld_events": 0,
            "error_count": 0
        })

    async def initialize(self) -> bool:
        """초기화 및 토큰 발급"""
        try:
            self.logger.info("전략 초기화 시작...")
            
            if not self.token_service.check_and_refresh_token():
                self.state["last_error"] = "토큰 발급 실패"
                return False
                
            token = self.token_service.get_token()
            if not token:
                self.state["last_error"] = "토큰이 없습니다"
                return False
                
            # 시장 종목 정보 초기화
            if not await self._initialize_market_stocks():
                return False
                
            # VI 체결 모니터링 서비스 초기화
            self.monitor_service = VICCLDMonitorService(token)
            self.monitor_service.add_vi_callback(self._handle_vi_data)
            self.monitor_service.add_ccld_callback(self._handle_ccld_data)
            
            self.state["is_initialized"] = True
            self.state["error_count"] = 0
            self.logger.info("전략 초기화 완료")
            return True
            
        except Exception as e:
            self.state["last_error"] = str(e)
            self.state["error_count"] += 1
            self.logger.error(f"초기화 중 오류 발생: {str(e)}")
            return False

    async def _initialize_market_stocks(self) -> bool:
        """시장 종목 정보 초기화"""
        try:
            # 코스피 종목 정보 조회
            kospi_stocks = self.market_service.get_market_stocks(MarketType.KOSPI)
            if not kospi_stocks:
                self.state["last_error"] = "코스피 종목 리스트 조회 실패"
                return False
                
            # 코스닥 종목 정보 조회
            kosdaq_stocks = self.market_service.get_market_stocks(MarketType.KOSDAQ)
            if not kosdaq_stocks:
                self.state["last_error"] = "코스닥 종목 리스트 조회 실패"
                return False
                
            # 종목 정보 저장
            self._market_stocks.clear()
            for stock in kospi_stocks.get("t8430OutBlock", []):
                self._market_stocks[stock["shcode"]] = MarketType.KOSPI
                
            for stock in kosdaq_stocks.get("t8430OutBlock", []):
                self._market_stocks[stock["shcode"]] = MarketType.KOSDAQ
                
            self.state["market_data_loaded"] = True
            self.logger.info(f"시장 종목 정보 초기화 완료 (총 {len(self._market_stocks)}개 종목)")
            return True
            
        except Exception as e:
            self.state["last_error"] = f"시장 종목 정보 초기화 중 오류: {str(e)}"
            self.state["error_count"] += 1
            self.logger.error(self.state["last_error"])
            return False

    async def _handle_vi_data(self, data: Dict[str, Any]) -> None:
        print(f"VI 데이터 처리: {data}")
        """VI 데이터 처리"""
        try:
            header = data.get("header", {})
            body = data.get("body", {})
            
            # 응답 메시지 처리
            if "rsp_cd" in header:
                rsp_msg = header.get("rsp_msg", "알 수 없는 메시지")
                if header["rsp_cd"] == "00000":
                    self.logger.info(f"VI 응답: {rsp_msg}")
                else:
                    self.logger.error(f"VI 구독 오류: {rsp_msg}")
                    self.state["error_count"] += 1
                return
                
            if not body:
                return
                
            stock_code = body.get("ref_shcode", "")
            vi_gubun = body.get("vi_gubun", "")
            
            if not stock_code or stock_code == "000000":
                self.logger.debug(f"유효하지 않은 종목 코드 무시: {stock_code}")
                return
                
            if stock_code not in self._market_stocks:
                self.logger.warning(f"알 수 없는 종목코드: {stock_code}")
                return
                
            self.state["last_vi_event_time"] = datetime.now()
            self.state["total_vi_events"] += 1
            
            if vi_gubun in ["1", "2", "3"]:  # VI 발동
                if stock_code not in self._active_vi_stocks:
                    self._active_vi_stocks.add(stock_code)
                    self.state["active_vi_count"] = len(self._active_vi_stocks)
                    self.state["ccld_monitoring_count"] = len(self._active_vi_stocks)
                
                self.logger.info(
                    f"VI 발동 - "
                    f"종목: {stock_code} ({self._market_stocks[stock_code]}), "
                    f"유형: {self._get_vi_type(vi_gubun)}, "
                    f"VI가격: {body.get('vi_trgprice', '')}, "
                    f"정적기준가: {body.get('svi_recprice', '')}, "
                    f"동적기준가: {body.get('dvi_recprice', '')}"
                )
            elif vi_gubun == "0":  # VI 해제
                if stock_code in self._active_vi_stocks:
                    self._active_vi_stocks.remove(stock_code)
                    self.state["active_vi_count"] = len(self._active_vi_stocks)
                    self.state["ccld_monitoring_count"] = len(self._active_vi_stocks)
                
                self.logger.info(
                    f"VI 해제 - "
                    f"종목: {stock_code} ({self._market_stocks[stock_code]})"
                )
            
        except Exception as e:
            self.state["last_error"] = str(e)
            self.state["error_count"] += 1
            self.logger.error(f"VI 데이터 처리 중 오류 발생: {str(e)}")

    async def _handle_ccld_data(self, data: Dict[str, Any]) -> None:
        print(f"체결 데이터 처리: {data}")
        """체결 데이터 처리"""
        try:
            body = data.get("body", {})
            if not body:
                return
                
            stock_code = body.get("shcode", "")
            if not stock_code or stock_code not in self._active_vi_stocks:
                return
                
            self.state["last_ccld_event_time"] = datetime.now()
            self.state["total_ccld_events"] += 1
            
            # 체결 정보 출력
            sign = body.get('sign', '')
            change = body.get('change', '')
            sign_symbol = "+" if sign in ["2", "3", "4", "5"] else "-" if sign in ["6", "7", "8", "9"] else ""
            
            self.logger.info(
                f"[체결] {stock_code}({self._market_stocks[stock_code]}) | "
                f"{body.get('chetime', '')} | "
                f"{body.get('price', '')}원({sign_symbol}{change}, {body.get('drate', '')}%) | "
                f"체결량:{body.get('cvolume', '')} | "
                f"체결강도:{body.get('cpower', '')}%"
            )
            
        except Exception as e:
            self.state["last_error"] = str(e)
            self.state["error_count"] += 1
            self.logger.error(f"체결 데이터 처리 중 오류 발생: {str(e)}")

    def _get_vi_type(self, vi_status: str) -> str:
        """VI 유형 반환"""
        vi_types = {
            "1": "정적발동",
            "2": "동적발동",
            "3": "정적&동적"
        }
        return vi_types.get(vi_status, "알 수 없음")

    async def start(self) -> bool:
        """전략 시작"""
        if self.state["monitoring_active"]:
            self.logger.warning("이미 전략이 실행 중입니다.")
            return False
            
        try:
            await self.monitor_service.start()
            
            self.is_running = True
            self.state["monitoring_active"] = True
            self.start_time = datetime.now()
            self.logger.info(f"{self.name} 전략 시작")
            return True
            
        except Exception as e:
            self.state["last_error"] = str(e)
            self.state["error_count"] += 1
            self.logger.error(f"전략 실행 중 오류 발생: {str(e)}")
            return False

    async def stop(self) -> None:
        """전략 중지"""
        if not self.state["monitoring_active"]:
            return
            
        try:
            if self.monitor_service:
                await self.monitor_service.stop()
                self.monitor_service = None
                
            self.is_running = False
            self.state["monitoring_active"] = False
            self._active_vi_stocks.clear()
            self.state["active_vi_count"] = 0
            self.state["ccld_monitoring_count"] = 0
            
            await super().stop()
            
            self.logger.info("VI 체결 모니터링 전략이 중지되었습니다")
            
        except Exception as e:
            self.state["last_error"] = str(e)
            self.state["error_count"] += 1
            self.logger.error(f"전략 중지 중 오류 발생: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보 반환"""
        status = super().get_status()
        
        monitoring_stocks = []
        if self.monitor_service:
            monitoring_stocks = self.monitor_service.get_monitoring_stocks()
            
        status.update({
            "monitoring_active": self.state["monitoring_active"],
            "active_vi_count": self.state["active_vi_count"],
            "ccld_monitoring_count": self.state["ccld_monitoring_count"],
            "market_data_loaded": self.state["market_data_loaded"],
            "monitoring_stocks": monitoring_stocks,
            "total_vi_events": self.state["total_vi_events"],
            "total_ccld_events": self.state["total_ccld_events"],
            "last_vi_event_time": self.state["last_vi_event_time"].isoformat() if self.state["last_vi_event_time"] else None,
            "last_ccld_event_time": self.state["last_ccld_event_time"].isoformat() if self.state["last_ccld_event_time"] else None,
            "error_count": self.state["error_count"]
        })
        return status

    def print_status(self) -> None:
        """전략 상태 출력"""
        status = self.get_status()
        
        log_msg = [
            "\n=== VI 체결 모니터링 상태 ===",
            f"실행 상태: {'실행 중' if status['is_running'] else '중지'}",
            f"모니터링 상태: {'활성화' if status['monitoring_active'] else '비활성화'}",
            f"시장 데이터 로드: {'완료' if status['market_data_loaded'] else '미완료'}",
            f"VI 발동 종목 수: {status['active_vi_count']}",
            f"체결 모니터링 종목 수: {status['ccld_monitoring_count']}",
            f"총 VI 이벤트 수: {status['total_vi_events']}",
            f"총 체결 이벤트 수: {status['total_ccld_events']}"
        ]
        
        if status['last_vi_event_time']:
            log_msg.append(f"마지막 VI 이벤트: {status['last_vi_event_time']}")
            
        if status['last_ccld_event_time']:
            log_msg.append(f"마지막 체결 이벤트: {status['last_ccld_event_time']}")
            
        if status['running_time'] is not None:
            hours = int(status['running_time'] // 3600)
            minutes = int((status['running_time'] % 3600) // 60)
            seconds = int(status['running_time'] % 60)
            log_msg.append(f"실행 시간: {hours:02d}:{minutes:02d}:{seconds:02d}")
        
        monitoring_stocks = status.get('monitoring_stocks', [])
        if monitoring_stocks:
            log_msg.append("\n현재 모니터링 중인 종목:")
            for stock_code in monitoring_stocks:
                stock_data = self.monitor_service.get_stock_data(stock_code)
                if stock_data:
                    log_msg.append(
                        f"  - {stock_code}: "
                        f"현재가={stock_data.get('price', '')}, "
                        f"등락률={stock_data.get('drate', '')}%, "
                        f"체결강도={stock_data.get('cpower', '')}%"
                    )
                else:
                    log_msg.append(f"  - {stock_code}: 체결 데이터 없음")
        else:
            log_msg.append("\n현재 모니터링 중인 종목: 없음")
            
        if status['error_count'] > 0:
            log_msg.append(f"\n누적 오류 횟수: {status['error_count']}")
            if status['last_error']:
                log_msg.append(f"마지막 오류: {status['last_error']}")
                
        log_msg.append("===========================\n")
        
        # 콘솔과 로그 파일에 모두 출력
        log_text = "\n".join(log_msg)
        print(log_text)
        self.logger.info(log_text)

    async def start_status_monitor(self, interval: int = 60) -> asyncio.Task:
        """상태 모니터링 태스크 시작
        
        Args:
            interval (int): 상태 출력 간격 (초)
            
        Returns:
            asyncio.Task: 상태 모니터링 태스크
        """
        async def _monitor():
            try:
                while self.state["monitoring_active"]:
                    self.print_status()
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                self.logger.info("상태 모니터링 태스크가 취소되었습니다.")
            except Exception as e:
                self.logger.error(f"상태 모니터링 중 오류 발생: {str(e)}")
                
        return asyncio.create_task(_monitor())

    async def run(self) -> None:
        """전략 실행"""
        async with self.strategy_session():
            try:
                self.logger.info("전략 실행 시작...")
                
                if not await self.initialize():
                    self.logger.error(f"초기화 실패: {self.state['last_error']}")
                    return
                    
                if not await self.start():
                    self.logger.error(f"전략 시작 실패: {self.state['last_error']}")
                    return
                    
                # 상태 모니터링 태스크 시작
                status_task = await self.start_status_monitor()
                
                try:
                    while self.state["monitoring_active"]:
                        await asyncio.sleep(1)
                finally:
                    if not status_task.done():
                        status_task.cancel()
                        try:
                            await status_task
                        except asyncio.CancelledError:
                            pass
                    
            except Exception as e:
                self.state["last_error"] = str(e)
                self.state["error_count"] += 1
                self.logger.error(f"전략 실행 중 오류 발생: {str(e)}", exc_info=True)
                await self.stop()
            finally:
                self.logger.info("전략 실행 종료")

async def main():
    """메인 함수"""
    strategy = VICCLDStrategy()
    
    try:
        await strategy.run()
    except KeyboardInterrupt:
        await strategy.stop()
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        await strategy.stop()

if __name__ == "__main__":
    asyncio.run(main())