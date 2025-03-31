"""VI 모니터링 전략

토큰 발급, 주식 리스트 조회, VI 모니터링을 순차적으로 수행하는 전략 클래스를 제공합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import sys
import os
import signal
from config.logging_config import setup_logger

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.strategy_VI import VIStrategy

async def main():
    """메인 함수"""
    logger = setup_logger(__name__)
    strategy = VIStrategy()
    
    def signal_handler(signum, frame):
        """시그널 핸들러"""
        logger.info("\n프로그램 종료 요청")
        asyncio.create_task(strategy.stop())
        
    # 종료 시그널 핸들러 등록
    if sys.platform != 'win32':
        # Unix/Linux 환경
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)
    else:
        # Windows 환경
        signal.signal(signal.SIGINT, signal_handler)
    
    try:
        logger.info("VI 모니터링 전략 시작...")
        # 전략 실행
        await strategy.run()
        
    except KeyboardInterrupt:
        logger.info("\n프로그램 종료 중...")
        await strategy.stop()
        logger.info("프로그램이 종료되었습니다.")
        
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {str(e)}", exc_info=True)
        await strategy.stop()
        
    finally:
        # 상태 출력
        status = strategy.get_status()
        logger.info(f"프로그램 종료 - 실행 시간: {status['running_time']:.2f}초")
        logger.info(f"최종 상태: {status}")

if __name__ == "__main__":
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 종료되었습니다.")
    except Exception as e:
        print(f"\n프로그램 실행 중 오류 발생: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        print("\n프로그램이 종료되었습니다.") 