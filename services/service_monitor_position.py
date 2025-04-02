"""계좌 포지션 모니터링 서비스

계좌의 포지션 상태를 실시간으로 모니터링하는 서비스를 제공합니다.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import asyncio
from config.logging_config import setup_logger
from services.service_monitor_account import AccountMonitorService
from services.service_account import AccountService

class PositionData:
    """포지션 데이터 클래스"""
    
    def __init__(self, data: Dict[str, Any]):
        """초기화"""
        self.stock_code = data.get("stock_code", "")  # 종목코드
        self.stock_name = data.get("stock_name", "")  # 종목명
        self.quantity = data.get("quantity", "0")  # 잔고수량
        self.available_quantity = data.get("available_quantity", "0")  # 매도가능수량
        self.average_price = data.get("average_price", "0")  # 평균단가
        self.current_price = data.get("current_price", "0")  # 현재가
        self.evaluation_amount = data.get("evaluation_amount", "0")  # 평가금액
        self.profit_loss = data.get("profit_loss", "0")  # 평가손익
        self.profit_loss_rate = data.get("profit_loss_rate", "0")  # 수익률
        self.holding_ratio = data.get("holding_ratio", "0")  # 보유비중
        self.fee = data.get("fee", "0")  # 수수료
        self.tax = data.get("tax", "0")  # 제세금
        self.interest = data.get("interest", "0")  # 신용이자
        
        # 당일/전일 매매 정보
        self.today = data.get("today", {})
        self.yesterday = data.get("yesterday", {})
        
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "quantity": self.quantity,
            "available_quantity": self.available_quantity,
            "average_price": self.average_price,
            "current_price": self.current_price,
            "evaluation_amount": self.evaluation_amount,
            "profit_loss": self.profit_loss,
            "profit_loss_rate": self.profit_loss_rate,
            "holding_ratio": self.holding_ratio,
            "fee": self.fee,
            "tax": self.tax,
            "interest": self.interest,
            "today": self.today,
            "yesterday": self.yesterday,
            "timestamp": self.timestamp
        }

class PositionMonitorService:
    """계좌 포지션 모니터링 서비스 클래스"""

    def __init__(self, token: str, account_no: str):
        """초기화
        
        Args:
            token (str): 인증 토큰
            account_no (str): 계좌번호
        """
        self.logger = setup_logger(__name__)
        self.token = token
        self.account_no = account_no
        
        # 서비스 초기화
        self.account_service = AccountService()
        self.account_monitor = AccountMonitorService(token, account_no)
        
        # 포지션 데이터 저장소
        self.positions: Dict[str, PositionData] = {}  # 종목코드: 포지션데이터
        self.position_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # 모니터링 상태
        self.is_monitoring = False
        self.update_interval = 60  # 포지션 업데이트 주기 (초)
        
    async def start(self) -> None:
        """모니터링 시작"""
        try:
            if self.is_monitoring:
                return
                
            self.is_monitoring = True
            self.logger.info(f"계좌 포지션 모니터링 시작 - 계좌: {self.account_no}")
            
            # 계좌 모니터링 시작
            await self.account_monitor.start()
            
            # 주문 체결 콜백 등록
            self.account_monitor.add_callback(self._handle_order_message)
            
            # 포지션 업데이트 태스크 시작
            asyncio.create_task(self._position_update_task())
            
        except Exception as e:
            self.is_monitoring = False
            self.logger.error(f"계좌 포지션 모니터링 시작 중 오류 발생: {str(e)}")
            await self.stop()
            raise
            
    async def stop(self) -> None:
        """모니터링 중지"""
        try:
            if not self.is_monitoring:
                return
                
            self.is_monitoring = False
            self.logger.info(f"계좌 포지션 모니터링 중지 - 계좌: {self.account_no}")
            
            # 계좌 모니터링 중지
            await self.account_monitor.stop()
            
            # 콜백 제거
            self.position_callbacks.clear()
            
            # 포지션 데이터 초기화
            self.positions.clear()
            
        except Exception as e:
            self.logger.error(f"계좌 포지션 모니터링 중지 중 오류 발생: {str(e)}")
            raise
            
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 등록"""
        if callback not in self.position_callbacks:
            self.position_callbacks.append(callback)
            
    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """콜백 함수 제거"""
        if callback in self.position_callbacks:
            self.position_callbacks.remove(callback)
            
    async def _position_update_task(self) -> None:
        """포지션 업데이트 태스크"""
        while self.is_monitoring:
            try:
                # 계좌 잔고 조회
                balance_info = self.account_service.get_account_balance()
                
                if "error_code" in balance_info:
                    self.logger.error(f"잔고 조회 실패: {balance_info['error_message']}")
                    await asyncio.sleep(self.update_interval)
                    continue
                    
                # 포지션 데이터 업데이트
                for stock in balance_info.get("stocks", []):
                    position = PositionData(stock)
                    self.positions[position.stock_code] = position
                    
                    # 콜백 호출
                    for callback in self.position_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(position.to_dict())
                            else:
                                callback(position.to_dict())
                        except Exception as e:
                            self.logger.error(f"포지션 콜백 실행 중 오류: {str(e)}")
                            
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"포지션 업데이트 중 오류 발생: {str(e)}")
                await asyncio.sleep(self.update_interval)
                
    async def _handle_order_message(self, message: Dict[str, Any]) -> None:
        """주문 메시지 처리"""
        try:
            # 주문 체결 메시지인 경우에만 포지션 업데이트
            header = message.get("header", {})
            body = message.get("body", {})
            
            tr_cd = header.get("tr_cd", "") or body.get("tr_cd", "")
            if tr_cd != "SC1":  # 주문 체결 메시지가 아닌 경우 무시
                return
                
            # 해당 계좌의 주문인 경우에만 처리
            if body.get("accno1") != self.account_no:
                return
                
            # 포지션 업데이트
            await self._update_position(body)
            
        except Exception as e:
            self.logger.error(f"주문 메시지 처리 중 오류: {str(e)}")
            
    async def _update_position(self, order_data: Dict[str, Any]) -> None:
        """주문 체결에 따른 포지션 업데이트"""
        try:
            stock_code = order_data.get("shtnIsuno", "")
            if not stock_code:
                return
                
            # 계좌 잔고 조회
            balance_info = self.account_service.get_account_balance()
            if "error_code" in balance_info:
                return
                
            # 해당 종목의 포지션 정보 찾기
            for stock in balance_info.get("stocks", []):
                if stock.get("stock_code") == stock_code:
                    position = PositionData(stock)
                    self.positions[stock_code] = position
                    
                    # 콜백 호출
                    for callback in self.position_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(position.to_dict())
                            else:
                                callback(position.to_dict())
                        except Exception as e:
                            self.logger.error(f"포지션 콜백 실행 중 오류: {str(e)}")
                    break
                    
        except Exception as e:
            self.logger.error(f"포지션 업데이트 중 오류: {str(e)}")
            
    def get_position(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """특정 종목의 포지션 정보 조회"""
        position = self.positions.get(stock_code)
        return position.to_dict() if position else None
        
    def get_positions(self) -> List[Dict[str, Any]]:
        """전체 포지션 목록 조회"""
        return [position.to_dict() for position in self.positions.values()] 