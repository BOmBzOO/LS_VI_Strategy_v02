"""계좌 주문 체결 모니터링 메인 스크립트

실시간으로 계좌의 주문 체결 정보를 모니터링하는 메인 스크립트입니다.
"""

import asyncio
import json
from datetime import datetime
from config.settings import LS_APP_ACCESS_TOKEN
from services.service_monitor_account import AccountMonitorService
from config.logging_config import setup_logger

logger = setup_logger(__name__)

# 상수 정의
class OrderType:
    BUY = "02"
    SELL = "01"

class MessageType:
    ORDER = "SC0"  # 주문 접수
    EXECUTION = "SC1"  # 체결
    EXECUTION_MODIFY = "SC2"  # 체결 정정
    CANCEL = "SC3"  # 주문 취소
    REJECT = "SC4"  # 주문 거부

class OrderCode:
    NEW = ["SONAT000", "SONAT003"]  # 신규주문 접수
    MODIFY = ["SONAT001"]  # 정정주문 접수
    CANCEL = ["SONAT002"]  # 취소주문 접수
    
    EXEC = ["SONAS100"]  # 체결확인

def get_order_type(body: dict) -> str:
    """주문 유형을 판단하여 매수/매도 구분을 반환합니다.
    
    Args:
        body (dict): 주문 메시지 바디
        
    Returns:
        str: "매수" 또는 "매도"
    """
    # 주문 유형 코드 확인
    ordptncode = body.get("ordptncode", "")
    if ordptncode == OrderType.BUY:
        return "매수"
    elif ordptncode == OrderType.SELL:
        return "매도"
        
    # 주문 구분 확인
    ordgb = body.get("ordgb", "")
    if ordgb == OrderType.BUY:
        return "매수"
    elif ordgb == OrderType.SELL:
        return "매도"
        
    # 주문 체결 구분 확인
    ordchegb = body.get("ordchegb", "")
    if ordchegb == OrderType.BUY:
        return "매수"
    elif ordchegb == OrderType.SELL:
        return "매도"
        
    # 매매 구분 확인
    return "매도" if body.get("gubun") == "B" else "매수"

def get_order_info(body: dict) -> tuple:
    """주문 정보를 추출합니다.
    
    Args:
        body (dict): 주문 메시지 바디
        
    Returns:
        tuple: (종목코드, 종목명, 시간, 가격, 수량, 주문유형, 주문구분, 주문체결구분, 신용구분)
    """
    shcode = body.get("shtcode", "") or body.get("shtnIsuno", "")
    hname = body.get("hname", "") or body.get("Isunm", "")
    time = body.get("ordtm", "") or body.get("exectime", "")
    price = body.get("ordprice", "0") or body.get("execprc", "0")
    qty = body.get("ordqty", "0") or body.get("execqty", "0")
    
    # 주문 관련 상세 정보
    ordptncode = body.get("ordptncode", "")  # 주문유형코드
    ordgb = body.get("ordgb", "")  # 주문구분
    ordchegb = body.get("ordchegb", "")  # 주문체결구분
    singb = body.get("singb", "")  # 신용구분
    
    return shcode, hname, time, price, qty, ordptncode, ordgb, ordchegb, singb

async def handle_order_message(message: dict) -> None:
    """주문 메시지 처리 콜백 함수
    
    Args:
        message (dict): 수신된 주문 메시지
    """
    try:
        # 메시지 헤더와 바디 분리
        header = message.get("header", {})
        body = message.get("body", {})
        
        # 메시지 타입 확인
        tr_cd = header.get("tr_cd", "")
        if not tr_cd:
            return
            
        # 주문 정보 추출
        shcode, hname, time, price, qty, ordptncode, ordgb, ordchegb, singb = get_order_info(body)
        if not all([shcode, hname, time]):
            return
            
        # 매수/매도 구분
        prefix = get_order_type(body)
        
        # 메시지 타입별 처리
        if tr_cd == MessageType.ORDER:  # 주문 접수
            trcode = body.get("trcode", "")
            if trcode in OrderCode.NEW:
                logger.info(f"[{time}] {prefix}접수: {shcode}({hname}) {price}원 x {qty}주")
            elif trcode in OrderCode.MODIFY:
                logger.info(f"[{time}] {prefix}정정접수: {shcode}({hname}) {price}원 x {qty}주")
            elif trcode in OrderCode.CANCEL:
                logger.info(f"[{time}] {prefix}취소접수: {shcode}({hname}) {qty}주")
            else:
                logger.info(f"[{time}] {prefix}접수: {shcode}({hname}) {price}원 x {qty}주 (trcode: {trcode})")
                
        elif tr_cd == MessageType.EXECUTION:  # 체결
            trcode = body.get("trcode", "")
            if trcode in OrderCode.EXEC:
                # 주문 유형에 따른 상세 정보
                order_type = ""
                if ordptncode == "01":  # 현금매도
                    order_type = "현금매도"
                elif ordptncode == "02":  # 현금매수
                    order_type = "현금매수"
                elif ordptncode == "03":  # 신용매도
                    order_type = "신용매도"
                elif ordptncode == "04":  # 신용매수
                    order_type = "신용매수"
                
                # 신용구분 정보
                credit_type = ""
                if singb == "000":  # 보통
                    credit_type = "보통"
                elif singb == "001":  # 유통융자신규
                    credit_type = "유통융자"
                elif singb == "003":  # 자기융자신규
                    credit_type = "자기융자"
                elif singb == "005":  # 유통대주신규
                    credit_type = "유통대주"
                elif singb == "007":  # 자기대주신규
                    credit_type = "자기대주"
                
                # 체결 메시지 출력
                if credit_type:
                    logger.info(f"[{time}] {prefix}체결: {shcode}({hname}) {price}원 x {qty}주 [{order_type}][{credit_type}]")
                else:
                    logger.info(f"[{time}] {prefix}체결: {shcode}({hname}) {price}원 x {qty}주 [{order_type}]")
            else:
                logger.info(f"[{time}] {prefix}체결: {shcode}({hname}) {price}원 x {qty}주 (trcode: {trcode})")
            
        elif tr_cd == MessageType.EXECUTION_MODIFY:  # 체결 정정
            logger.info(f"[{time}] {prefix}체결정정: {shcode}({hname}) {price}원 x {qty}주")
            
        elif tr_cd == MessageType.CANCEL:  # 주문 취소
            logger.info(f"[{time}] {prefix}취소: {shcode}({hname}) {qty}주")
            
        elif tr_cd == MessageType.REJECT:  # 주문 거부
            reject_reason = body.get("rsp_msg", "알 수 없는 사유")
            logger.warning(f"[{time}] {prefix}거부: {shcode}({hname}) - {reject_reason}")
            
    except Exception as e:
        logger.error(f"주문 메시지 처리 중 오류: {str(e)}")

async def main():
    """메인 함수"""
    try:
        # 계좌 모니터링 서비스 초기화
        monitor_service = AccountMonitorService(
            token=LS_APP_ACCESS_TOKEN,
            account_no=""  # 계좌번호 없이 빈 문자열로 설정
        )
        
        # 주문 메시지 처리 콜백 등록
        monitor_service.add_callback(handle_order_message)
        
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
    # 이벤트 루프 실행
    asyncio.run(main()) 