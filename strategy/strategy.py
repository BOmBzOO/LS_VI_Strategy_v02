"""VI 모니터링 전략

토큰 발급, 주식 리스트 조회, VI 모니터링을 순차적으로 수행하는 전략 클래스를 제공합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import sys
import os
import signal
from contextlib import asynccontextmanager

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import setup_logger
from services.token_service import TokenService
from services.market_service import MarketService
from services.vi_monitor_service import VIMonitorService, VIData
from api.constants import MarketType, VIStatus, TRCode
from api.realtime.websocket.websocket_base import WebSocketState

class VIStrategy:
    """VI 모니터링 전략 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.token_service = TokenService()
        self.market_service = MarketService()
        self.vi_monitor: Optional[VIMonitorService] = None
        self.state = {
            "is_running": False,
            "is_initialized": False,
            "market_data_loaded": False,
            "monitoring_active": False,
            "last_error": None,
            "start_time": None,
            "active_vi_count": 0
        }
        
    @asynccontextmanager
    async def strategy_session(self):
        """전략 세션 관리"""
        try:
            # 시그널 핸들러 설정
            self._setup_signal_handlers()
            
            # 상태 초기화
            self.state["is_running"] = True
            self.state["start_time"] = datetime.now()
            
            yield
            
        finally:
            # 종료 처리
            await self._cleanup()
            
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.stop()))
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self.stop()))
        
    async def initialize(self) -> bool:
        """초기화 및 토큰 발급"""
        try:
            self.logger.info("전략 초기화 시작...")
            
            # 토큰 체크 및 갱신
            if not self.token_service.check_and_refresh_token():
                self.state["last_error"] = "토큰 발급 실패"
                return False
                
            # 토큰 정보 조회
            token_info = self.token_service.get_token_info()
            if not token_info["is_valid"]:
                self.state["last_error"] = "토큰이 유효하지 않습니다"
                return False
                
            self.state["is_initialized"] = True
            self.logger.info("전략 초기화 완료")
            return True
            
        except Exception as e:
            self.state["last_error"] = str(e)
            self.logger.error(f"초기화 중 오류 발생: {str(e)}")
            return False
            
    async def load_market_data(self) -> bool:
        """시장 데이터 로드"""
        try:
            self.logger.info("시장 데이터 로드 시작...")
            
            # 코스피 종목 리스트 조회
            kospi_stocks = self.market_service.get_market_stocks(MarketType.KOSPI)
            if not kospi_stocks:
                self.state["last_error"] = "코스피 종목 리스트 조회 실패"
                return False
                
            # 코스닥 종목 리스트 조회
            kosdaq_stocks = self.market_service.get_market_stocks(MarketType.KOSDAQ)
            if not kosdaq_stocks:
                self.state["last_error"] = "코스닥 종목 리스트 조회 실패"
                return False
                
            self.state["market_data_loaded"] = True
            self.logger.info(
                f"시장 데이터 로드 완료 (코스피: {len(kospi_stocks['t8430OutBlock'])}, "
                f"코스닥: {len(kosdaq_stocks['t8430OutBlock'])})"
            )
            return True
            
        except Exception as e:
            self.state["last_error"] = str(e)
            self.logger.error(f"시장 데이터 로드 중 오류 발생: {str(e)}")
            return False
            
    async def start_vi_monitoring(self) -> bool:
        """VI 모니터링 시작"""
        try:
            self.logger.info("VI 모니터링 시작 중...")
            
            # 토큰 조회
            token = self.token_service.get_token()
            if not token:
                self.state["last_error"] = "토큰을 찾을 수 없습니다"
                return False
                
            # VI 모니터링 서비스 초기화
            self.vi_monitor = VIMonitorService(token)
            
            # VI 데이터 처리 콜백 등록
            self.vi_monitor.add_callback(self._handle_vi_data)
            
            # 모니터링 시작
            await self.vi_monitor.start()
            
            if self.vi_monitor.state != WebSocketState.CONNECTED:
                self.state["last_error"] = "VI 모니터링 연결 실패"
                return False
                
            self.state["monitoring_active"] = True
            self.logger.info("VI 모니터링이 시작되었습니다")
            return True
            
        except Exception as e:
            self.state["last_error"] = str(e)
            self.logger.error(f"VI 모니터링 시작 중 오류 발생: {str(e)}")
            return False
            
    async def _handle_vi_data(self, data: Dict[str, Any]) -> None:
        """VI 데이터 처리"""
        try:
            # 콜백이 없는 경우 메시지 처리 및 로깅
            header = data.get("header", {})
            body = data.get("body", {})
            
            # 응답 메시지 처리
            if "rsp_cd" in header:
                rsp_msg = header.get("rsp_msg", "알 수 없는 메시지")
                if header["rsp_cd"] == "00000":
                    self.logger.info(f"VI 응답: {rsp_msg}")
                else:
                    self.logger.error(f"VI 구독 오류: {rsp_msg}")
                return
                
            # VI 메시지가 아닌 경우 무시
            if header.get("tr_cd") != TRCode.VI_OCCUR:
                return
                
            # body가 None인 경우 무시
            if not body or not isinstance(body, dict):
                return
            
            # VI 데이터 생성
            vi_data = VIData(body)
            
            # VI 발동 시 추가 처리
            if vi_data.vi_gubun in ["1", "2", "3"]:
                self.state["active_vi_count"] += 1
                await self._handle_vi_activation(vi_data)
            # VI 해제 시 추가 처리
            elif vi_data.vi_gubun == "0":
                self.state["active_vi_count"] -= 1
                await self._handle_vi_release(vi_data)
                
        except Exception as e:
            self.logger.error(f"VI 데이터 처리 중 오류 발생: {str(e)}")
            
    async def _handle_vi_activation(self, vi_data: VIData) -> None:
        """VI 발동 처리"""
        try:
            # # 현재가 조회
            # price_info = self.market_service.get_stock_price(vi_data.shcode)
            # if not price_info:
            #     return
                
            # VI 발동 시 추가 로직 구현
            self.logger.info(f"VI 발동 감지 - 종목: {vi_data.ref_shcode}, 현재가: {vi_data.get('price', 'N/A')}, VI유형: {vi_data.vi_type}")
            
            # 여기에 VI 발동에 대한 추가 전략 로직 구현
            
        except Exception as e:
            self.logger.error(f"VI 발동 처리 중 오류 발생: {str(e)}")
            
    async def _handle_vi_release(self, vi_data: VIData) -> None:
        """VI 해제 처리"""
        try:
            # VI 해제 시 추가 로직 구현
            self.logger.info(f"VI 해제 감지 - 종목: {vi_data.ref_shcode}, 정적기준가: {vi_data.svi_recprice}, 동적기준가: {vi_data.dvi_recprice}, 발동가: {vi_data.vi_trgprice}")
            
            # 여기에 VI 해제에 대한 추가 전략 로직 구현
            
        except Exception as e:
            self.logger.error(f"VI 해제 처리 중 오류 발생: {str(e)}")
            
    async def run(self) -> None:
        """전략 실행"""
        async with self.strategy_session():
            try:
                # 1. 초기화 및 토큰 발급
                if not await self.initialize():
                    self.logger.error(f"초기화 실패: {self.state['last_error']}")
                    return
                    
                # 2. 시장 데이터 로드
                if not await self.load_market_data():
                    self.logger.error(f"시장 데이터 로드 실패: {self.state['last_error']}")
                    return
                    
                # 3. VI 모니터링 시작
                if not await self.start_vi_monitoring():
                    self.logger.error(f"VI 모니터링 시작 실패: {self.state['last_error']}")
                    return
                    
                # 4. 모니터링 유지
                while self.state["is_running"]:
                    if self.vi_monitor and self.vi_monitor.state == WebSocketState.ERROR:
                        self.logger.error("VI 모니터링 오류 발생")
                        await self.stop()
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.state["last_error"] = str(e)
                self.logger.error(f"전략 실행 중 오류 발생: {str(e)}")
                
    async def _cleanup(self) -> None:
        """자원 정리"""
        try:
            if self.vi_monitor:
                await self.vi_monitor.stop()
                self.vi_monitor = None
                
            self.state["is_running"] = False
            self.state["monitoring_active"] = False
            
            self.logger.info("전략이 정상적으로 종료되었습니다")
            
        except Exception as e:
            self.logger.error(f"종료 처리 중 오류 발생: {str(e)}")
            
    async def stop(self) -> None:
        """전략 중지"""
        self.state["is_running"] = False
            
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보 반환"""
        return {
            **self.state,
            "token_status": self.token_service.get_token_info(),
            "market_status": self.market_service.get_status(),
            "vi_monitor_state": self.vi_monitor.state.name if self.vi_monitor else "NOT_INITIALIZED",
            "vi_active_stocks": self.vi_monitor.get_active_stocks() if self.vi_monitor else {},
            "uptime": (datetime.now() - self.state["start_time"]).total_seconds() if self.state["start_time"] else 0
        }

async def main():
    """메인 함수"""
    strategy = VIStrategy()
    
    try:
        await strategy.run()
    except KeyboardInterrupt:
        await strategy.stop()
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        await strategy.stop()

if __name__ == "__main__":
    asyncio.run(main()) 