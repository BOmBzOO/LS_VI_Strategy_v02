import asyncio
import signal
import sys
from datetime import datetime
import pytz
from strategy.vi_strategy import VIStrategy
from config.logging_config import setup_logger
from config.settings import TIMEZONE, LOG_LEVEL
from services.token_service import TokenService

# 로거 설정
logger = setup_logger(__name__)

class TradingSystem:
    def __init__(self):

        # 전략 초기화
        self.strategy = None
        self.is_running = True
        self.kst = pytz.timezone(TIMEZONE)

    def setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        def signal_handler(_, __):
            logger.info("프로그램 종료 신호를 받았습니다.")
            self.is_running = False
            asyncio.create_task(self.cleanup())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def cleanup(self):
        """종료 처리"""
        logger.info("프로그램 종료 중...")
        await self.strategy.stop()
        # 이벤트 루프 종료
        loop = asyncio.get_event_loop()
        loop.stop()

    async def start(self):
        """트레이딩 시스템 시작"""
        try:
            current_time = datetime.now(self.kst)
            logger.info(f"트레이딩 시스템을 시작합니다. (시작 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')})")
            
            # 시그널 핸들러 설정
            self.setup_signal_handlers()
            
            # 전략 시작
            self.strategy = VIStrategy()
            await self.strategy.start()
            
            # 프로그램이 종료되지 않도록 대기
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"시스템 실행 중 오류 발생: {e}")
            await self.cleanup()
        finally:
            logger.info("트레이딩 시스템이 종료되었습니다.")

async def main():
    """메인 함수"""
    trading_system = TradingSystem()
    await trading_system.start()

if __name__ == "__main__":
    try:
        # 이벤트 루프 생성 및 실행
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트로 프로그램이 종료되었습니다.")
    except Exception as e:
        logger.error(f"예기치 않은 오류 발생: {e}")
    finally:
        # 이벤트 루프 종료
        loop.close()
        sys.exit(0) 