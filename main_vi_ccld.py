"""VI 체결 모니터링 실행 스크립트

VI가 발동된 종목들의 실시간 체결 데이터를 모니터링하는 프로그램을 실행합니다.
"""

from datetime import datetime
import asyncio
import sys
import os
import signal
import traceback
from config.logging_config import setup_logger
from strategy.strategy_VI_CCLD import VICCLDStrategy

async def main():
    """메인 함수"""
    logger = setup_logger(__name__)
    strategy = VICCLDStrategy()
    status_task = None
    
    def signal_handler(signum, frame):
        """시그널 핸들러"""
        logger.info("\n프로그램 종료 요청 - 시그널 수신: %s", signal.Signals(signum).name)
        if status_task:
            status_task.cancel()
        asyncio.create_task(strategy.stop())
        
    # 종료 시그널 핸들러 등록
    if sys.platform != 'win32':
        # Unix/Linux 환경
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)
            logger.info(f"시그널 핸들러 등록: {signal.Signals(sig).name}")
    else:
        # Windows 환경
        signal.signal(signal.SIGINT, signal_handler)
        logger.info("시그널 핸들러 등록: SIGINT (Windows)")
    
    try:
        logger.info("=== VI 체결 모니터링 프로그램 시작 ===")
        logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 상태 모니터링 태스크 시작
        status_task = await strategy.start_status_monitor()
        logger.info("상태 모니터링 태스크 시작")
        
        # 전략 실행
        await strategy.run()
        
    except KeyboardInterrupt:
        logger.info("\n프로그램 종료 중... (KeyboardInterrupt)")
        if status_task:
            status_task.cancel()
        await strategy.stop()
        
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {str(e)}", exc_info=True)
        if status_task:
            status_task.cancel()
        await strategy.stop()
        
    finally:
        # 최종 상태 출력
        status = strategy.get_status()
        end_time = datetime.now()
        
        logger.info("=== 프로그램 종료 정보 ===")
        logger.info(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"총 실행 시간: {status['running_time']:.2f}초")
        logger.info(f"총 VI 이벤트 수: {status['total_vi_events']}")
        logger.info(f"누적 오류 횟수: {status['error_count']}")
        if status['last_error']:
            logger.info(f"마지막 오류: {status['last_error']}")
        logger.info("=== VI 체결 모니터링 프로그램 종료 ===\n")

if __name__ == "__main__":
    # 프로그램 시작 시간 기록
    start_time = datetime.now()
    logger = setup_logger(__name__)
    logger.info(f"프로그램 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n프로그램이 사용자에 의해 종료되었습니다.")
    except Exception as e:
        logger.error(f"\n프로그램 실행 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # 프로그램 종료 시간 및 실행 시간 출력
        end_time = datetime.now()
        running_time = end_time - start_time
        logger.info(f"프로그램 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"총 실행 시간: {running_time}") 