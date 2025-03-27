"""VI 모니터링 전략

토큰 발급, 주식 리스트 조회, VI 모니터링을 순차적으로 수행하는 전략 클래스를 제공합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import sys
import os
import logging

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import setup_logger
from services.token_service import TokenService
from services.market_service import MarketService
from services.vi_monitor_service import VIMonitorService
from api.constants import MarketType

class VIStrategy:
    """VI 모니터링 전략 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        self.token_service = TokenService()
        self.market_service = MarketService()
        self.vi_monitor: Optional[VIMonitorService] = None
        self.is_running = False
        
    async def initialize(self) -> bool:
        """초기화 및 토큰 발급
        
        Returns:
            bool: 초기화 성공 여부
        """
        try:
            # 토큰 체크 및 갱신
            if not self.token_service.check_and_refresh_token():
                self.logger.error("토큰 발급 실패")
                return False
                
            # 토큰 정보 조회
            token_info = self.token_service.get_token_info()
            if not token_info["is_valid"]:
                self.logger.error("토큰이 유효하지 않습니다.")
                return False
                
            self.logger.info("토큰 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"초기화 중 오류 발생: {str(e)}")
            return False
            
    async def load_market_data(self) -> bool:
        """시장 데이터 로드
        
        Returns:
            bool: 데이터 로드 성공 여부
        """
        try:
            # 코스피 종목 리스트 조회
            kospi_stocks = self.market_service.get_market_stocks(MarketType.KOSPI)
            if not kospi_stocks:
                self.logger.error("코스피 종목 리스트 조회 실패")
                return False
                
            # 코스닥 종목 리스트 조회
            kosdaq_stocks = self.market_service.get_market_stocks(MarketType.KOSDAQ)
            if not kosdaq_stocks:
                self.logger.error("코스닥 종목 리스트 조회 실패")
                return False
                
            self.logger.info(f"시장 데이터 로드 완료 (코스피: {len(kospi_stocks['t8430OutBlock'])}, 코스닥: {len(kosdaq_stocks['t8430OutBlock'])})")
            return True
            
        except Exception as e:
            self.logger.error(f"시장 데이터 로드 중 오류 발생: {str(e)}")
            return False
            
    async def start_vi_monitoring(self) -> bool:
        """VI 모니터링 시작
        
        Returns:
            bool: 모니터링 시작 성공 여부
        """
        try:
            # 토큰 조회
            token = self.token_service.get_token()
            if not token:
                self.logger.error("토큰을 찾을 수 없습니다.")
                return False
                
            # VI 모니터링 서비스 초기화
            self.vi_monitor = VIMonitorService(token)
            
            # VI 데이터 처리 콜백 등록
            self.vi_monitor.add_callback(self._handle_vi_data)
            
            # 모니터링 시작
            await self.vi_monitor.start()
            
            self.logger.info("VI 모니터링이 시작되었습니다.")
            return True
            
        except Exception as e:
            self.logger.error(f"VI 모니터링 시작 중 오류 발생: {str(e)}")
            return False
            
    async def _handle_vi_data(self, data: Dict[str, Any]) -> None:
        """VI 데이터 처리
        
        Args:
            data (Dict[str, Any]): VI 데이터
        """
        try:
            # VI 발동/해제 정보 로깅
            self.logger.info(
                f"VI 상태 변경 - 종목: {data['shcode']}, "
                f"상태: {data['status']}, "
                f"VI유형: {data['vi_type']}, "
                f"발동가: {data['vi_trgprice']}"
            )
            
            # VI 발동 시 추가 처리
            if data["status"] == "발동":
                await self._handle_vi_activation(data)
            # VI 해제 시 추가 처리
            else:
                await self._handle_vi_release(data)
                
        except Exception as e:
            self.logger.error(f"VI 데이터 처리 중 오류 발생: {str(e)}")
            
    async def _handle_vi_activation(self, data: Dict[str, Any]) -> None:
        """VI 발동 처리
        
        Args:
            data (Dict[str, Any]): VI 데이터
        """
        try:
            # 현재가 조회
            price_info = self.market_service.get_stock_price(data["shcode"])
            if not price_info:
                return
                
            # VI 발동 시 추가 로직 구현
            self.logger.info(
                f"VI 발동 감지 - 종목: {data['shcode']}, "
                f"현재가: {price_info.get('price', 'N/A')}, "
                f"VI유형: {data['vi_type']}"
            )
            
        except Exception as e:
            self.logger.error(f"VI 발동 처리 중 오류 발생: {str(e)}")
            
    async def _handle_vi_release(self, data: Dict[str, Any]) -> None:
        """VI 해제 처리
        
        Args:
            data (Dict[str, Any]): VI 데이터
        """
        try:
            # VI 해제 시 추가 로직 구현
            self.logger.info(
                f"VI 해제 감지 - 종목: {data['shcode']}, "
                f"지속시간: {data.get('duration', 'N/A')}초"
            )
            
        except Exception as e:
            self.logger.error(f"VI 해제 처리 중 오류 발생: {str(e)}")
            
    async def run(self) -> None:
        """전략 실행"""
        try:
            self.is_running = True
            
            # 1. 초기화 및 토큰 발급
            if not await self.initialize():
                return
                
            # 2. 시장 데이터 로드
            if not await self.load_market_data():
                return
                
            # 3. VI 모니터링 시작
            if not await self.start_vi_monitoring():
                return
                
            # 4. 모니터링 유지
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"전략 실행 중 오류 발생: {str(e)}")
        finally:
            await self.stop()
            
    async def stop(self) -> None:
        """전략 중지"""
        try:
            self.is_running = False
            
            if self.vi_monitor:
                await self.vi_monitor.stop()
                self.vi_monitor = None
                
            self.logger.info("전략이 중지되었습니다.")
            
        except Exception as e:
            self.logger.error(f"전략 중지 중 오류 발생: {str(e)}")
            
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보 반환
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        return {
            "is_running": self.is_running,
            "token_status": self.token_service.get_token_info(),
            "market_status": self.market_service.get_status(),
            "vi_active_stocks": self.vi_monitor.get_active_stocks() if self.vi_monitor else {}
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