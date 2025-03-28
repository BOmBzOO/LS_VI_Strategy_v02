"""VI 발동 종목 체결 모니터링

VI가 발동된 종목들의 실시간 체결 데이터를 모니터링하는 예제를 제공합니다.
"""

from typing import Dict, Any
import asyncio
import sys
import os
import signal
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import setup_logger
from services.token_service import TokenService
from services.vi_ccld_monitor_service import VICCLDMonitorService

def print_vi_ccld_data(data: Dict[str, Any]) -> None:
    """VI 발동 종목 체결 데이터 출력"""
    body = data.get("body", {})
    if not body:
        return
        
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] "
        f"종목: {body.get('shcode', '')}, "
        f"현재가: {body.get('price', '')} ({body.get('sign', '')}{body.get('change', '')}, {body.get('drate', '')}%), "
        f"체결량: {body.get('cvolume', '')} ({body.get('cgubun', '')}), "
        f"체결강도: {body.get('cpower', '')}%"
    )

async def main():
    """메인 함수"""
    logger = setup_logger(__name__)
    
    try:
        # 토큰 서비스 초기화 및 토큰 발급
        token_service = TokenService()
        if not token_service.check_and_refresh_token():
            logger.error("토큰 발급 실패")
            return
            
        token = token_service.get_token()
        if not token:
            logger.error("토큰이 없습니다.")
            return
            
        # VI 발동 종목 체결 모니터링 서비스 초기화
        monitor_service = VICCLDMonitorService(token=token)
        
        # 모니터링 시작
        await monitor_service.start()
        logger.info("VI 발동 종목 체결 모니터링이 시작되었습니다.")
        
        # 프로그램 종료 대기
        try:
            while True:
                await asyncio.sleep(1)
                
                # 현재 모니터링 중인 종목 확인
                monitoring_stocks = monitor_service.get_monitoring_stocks()
                if monitoring_stocks:
                    logger.info(f"현재 모니터링 중인 VI 발동 종목: {monitoring_stocks}")
                    
                    # 각 종목의 최신 체결 데이터 확인
                    for stock_code in monitoring_stocks:
                        stock_data = monitor_service.get_stock_data(stock_code)
                        if stock_data:
                            logger.debug(f"종목 {stock_code} 체결 데이터: {stock_data}")
                            
        except KeyboardInterrupt:
            logger.info("프로그램 종료 요청")
            
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
    finally:
        if 'monitor_service' in locals():
            await monitor_service.stop()
            logger.info("VI 발동 종목 체결 모니터링이 종료되었습니다.")

if __name__ == "__main__":
    # 프로세스 종료 시그널 핸들러 등록
    def signal_handler(signum, frame):
        print("\n프로그램 종료 중...")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 메인 함수 실행
    asyncio.run(main()) 