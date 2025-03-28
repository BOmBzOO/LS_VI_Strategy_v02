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
from services.auth_token_service import TokenService
from services.ccld_monitor_service import CCLDMonitorService
from api.constants import MarketType

def print_ccld_data(data: Dict[str, Any]) -> None:
    """체결 데이터 출력"""
    body = data.get("body", {})
    if not body:
        return
        
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] "
        f"현재가: {body.get('price', '')}, "
        f"체결량: {body.get('volume', '')}, "
        f"거래대금: {body.get('value', '')}"
    )

async def main():
    """메인 함수"""
    logger = setup_logger(__name__)
    
    # 모니터링할 종목 설정
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
        monitor_service = CCLDMonitorService(
            token=token,
            stock_code=stock_code,
            market_type=market_type
        )
        
        # 콜백 함수 등록
        monitor_service.add_callback(print_ccld_data)
        
        # 모니터링 시작
        await monitor_service.start()
        logger.info(f"체결 모니터링 시작 - 종목: {stock_code}")
        
        # 프로그램 종료 대기
        try:
            while True:
                await asyncio.sleep(1)
                
                # 현재 데이터 확인
                current_data = monitor_service.get_current_data()
                if current_data:
                    logger.debug(f"현재 데이터: {current_data}")
                    
        except KeyboardInterrupt:
            logger.info("프로그램 종료 요청")
            
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
    finally:
        if 'monitor_service' in locals():
            await monitor_service.stop()
            logger.info(f"체결 모니터링 종료 - 종목: {stock_code}")

if __name__ == "__main__":
    # 프로세스 종료 시그널 핸들러 등록
    def signal_handler(signum, frame):
        print("\n프로그램 종료 중...")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 메인 함수 실행
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 종료되었습니다.")
    except Exception as e:
        print(f"\n프로그램 실행 중 오류 발생: {str(e)}")
    finally:
        print("\n프로그램이 종료되었습니다.") 