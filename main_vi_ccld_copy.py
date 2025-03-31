"""VI 발동 종목 체결 모니터링

VI가 발동된 종목들의 실시간 체결 데이터를 모니터링하는 예제를 제공합니다.
"""

import asyncio
import sys
import os
import signal
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import setup_logger
from strategy.VI_CCLD_strategy import VICCLDStrategy

async def main():
    """메인 함수"""
    logger = setup_logger(__name__)
    strategy = VICCLDStrategy()
    
    try:
        # 전략 실행
        await strategy.run()
        logger.info("VI 발동 종목 체결 모니터링이 시작되었습니다.")
        
        # 프로그램 종료 대기
        while True:
            await asyncio.sleep(1)
            
            # 현재 상태 확인
            status = strategy.get_status()
            if status["active_vi_count"] > 0:
                logger.info(
                    f"현재 VI 발동 종목 수: {status['active_vi_count']}, "
                    f"모니터링 중인 종목 수: {status['ccld_monitoring_count']}"
                )
                
                # 활성 VI 종목 정보 출력
                active_stocks = status.get("active_stocks", {})
                for code, data in active_stocks.items():
                    logger.info(
                        f"종목 {code} - "
                        f"상태: {data['status']}, "
                        f"VI유형: {data['vi_type']}, "
                        f"발동가: {data['vi_trgprice']}"
                    )
                    
    except KeyboardInterrupt:
        logger.info("프로그램 종료 요청")
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
    finally:
        await strategy.stop()
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