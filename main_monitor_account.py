"""계좌 주문 체결 모니터링 메인 스크립트

실시간으로 계좌의 주문 체결 정보를 모니터링하는 메인 스크립트입니다.
"""

import asyncio
import sys
from config.settings import LS_APP_ACCESS_TOKEN
from services.service_monitor_account import AccountMonitorService
from config.logging_config import setup_logger

logger = setup_logger(__name__)

async def main():
    """메인 함수"""
    try:
        # 계좌 모니터링 서비스 초기화
        monitor_service = AccountMonitorService(
            token=LS_APP_ACCESS_TOKEN,
            account_no=""  # 계좌번호 없이 빈 문자열로 설정
        )
        
        # 모니터링 시작
        logger.info("계좌 체결 모니터링 시작")
        await monitor_service.start()
        
        # 프로그램 종료 방지
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("프로그램 종료 요청이 감지되었습니다.")
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {str(e)}")
    finally:
        # 모니터링 중지
        if 'monitor_service' in locals():
            await monitor_service.stop()
            logger.info("계좌 체결 모니터링이 중지되었습니다.")

if __name__ == "__main__":
    # Windows 환경에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 이벤트 루프 실행
    asyncio.run(main()) 