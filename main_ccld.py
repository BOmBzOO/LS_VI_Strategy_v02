"""실시간 체결 모니터링

특정 종목의 실시간 체결 데이터를 모니터링하는 예제를 제공합니다.
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
from services.ccld_monitor_service import CCLDMonitorService
from api.constants import MarketType

def print_ccld_data(data: Dict[str, Any]) -> None:
    """체결 데이터 출력"""
    body = data.get("body", {})
    if not body:
        return
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"현재가: {body.get('price', '')}, "
          f"체결량: {body.get('volume', '')}, "
          f"거래대금: {body.get('value', '')}")

async def main():
    """메인 함수"""
    logger = setup_logger(__name__)
    
    # 모니터링할 종목 설정
    # stock_code = "005930"  # 삼성전자
    # market_type = MarketType.KOSPI

    stock_code = "020180"  # 삼성전자
    market_type = MarketType.KOSDAQ
    
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
            
        # 체결 모니터링 서비스 초기화
        ccld_monitor = CCLDMonitorService(
            token=token,
            stock_code=stock_code,
            market_type=market_type
        )
        
        # 콜백 함수 등록
        ccld_monitor.add_callback(print_ccld_data)
        
        # 모니터링 시작
        await ccld_monitor.start()
        
        # 프로그램 종료 대기
        try:
            while True:
                await asyncio.sleep(1)
                
                # 현재 데이터 확인
                current_data = ccld_monitor.get_current_data()
                if current_data:
                    logger.debug(f"현재 데이터: {current_data}")
                    
        except KeyboardInterrupt:
            logger.info("프로그램 종료 요청")
            
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
    finally:
        if 'ccld_monitor' in locals():
            await ccld_monitor.stop()

if __name__ == "__main__":
    asyncio.run(main()) 