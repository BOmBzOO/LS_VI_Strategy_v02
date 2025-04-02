"""계좌 포지션 모니터링 메인 스크립트

계좌의 포지션 상태를 실시간으로 모니터링하는 메인 스크립트입니다.
"""

import os
import asyncio
import signal
import sys
from dotenv import load_dotenv
from services.service_monitor_position import PositionMonitorService
from config.logging_config import setup_logger

async def handle_position_update(position_data: dict) -> None:
    """포지션 업데이트 처리
    
    Args:
        position_data (dict): 포지션 데이터
    """
    logger = setup_logger(__name__)
    
    try:
        # 포지션 정보 출력
        logger.info(
            f"포지션 업데이트 - "
            f"종목: {position_data['stock_name']}({position_data['stock_code']}), "
            f"수량: {int(float(position_data['quantity'])):,}주, "
            f"평균단가: {int(float(position_data['average_price'])):,}원, "
            f"현재가: {int(float(position_data['current_price'])):,}원, "
            f"평가금액: {int(float(position_data['evaluation_amount'])):,}원, "
            f"평가손익: {int(float(position_data['profit_loss'])):,}원 "
            f"({float(position_data['profit_loss_rate']):.2f}%)"
        )
        
    except Exception as e:
        logger.error(f"포지션 업데이트 처리 중 오류 발생: {str(e)}")

async def main():
    """메인 함수"""
    try:
        # 환경변수 로드
        load_dotenv()
        
        # 로거 설정
        logger = setup_logger(__name__)
        
        # 필수 환경변수 확인
        token = os.getenv('LS_ACCESS_TOKEN')
        account_no = os.getenv('LS_ACCOUNT_NO')
        
        if not token or not account_no:
            raise ValueError("필수 환경변수가 설정되지 않았습니다.")
            
        # 포지션 모니터링 서비스 초기화
        position_monitor = PositionMonitorService(token, account_no)
        
        # 포지션 업데이트 콜백 등록
        position_monitor.add_callback(handle_position_update)
        
        # 종료 이벤트 설정
        stop_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            """시그널 핸들러"""
            logger.info("종료 시그널을 받았습니다. 프로그램을 종료합니다...")
            stop_event.set()
            
        # Windows가 아닌 경우에만 시그널 핸들러 등록
        if os.name != 'nt':
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, signal_handler)
            
        # 모니터링 시작
        await position_monitor.start()
        
        logger.info("계좌 포지션 모니터링이 시작되었습니다. 종료하려면 Ctrl+C를 누르세요.")
        
        try:
            # 종료 이벤트 대기
            await stop_event.wait()
        except KeyboardInterrupt:
            logger.info("키보드 인터럽트를 받았습니다. 프로그램을 종료합니다...")
        finally:
            # 모니터링 중지
            await position_monitor.stop()
            logger.info("계좌 포지션 모니터링이 종료되었습니다.")
        
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {str(e)}")
        raise
        
if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    # 메인 함수 실행
    asyncio.run(main()) 