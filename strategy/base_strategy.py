"""기본 전략 클래스

모든 트레이딩 전략의 기본이 되는 추상 클래스입니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.base_monitor import BaseMonitor
from config.logging_config import setup_logger
from api.tr.order import OrderTRAPI
from api.tr.account import AccountTRAPI

class BaseStrategy(ABC):
    """기본 전략 클래스"""

    def __init__(self, name: str):
        """
        Args:
            name (str): 전략 이름
        """
        self.name = name
        self.logger = setup_logger(f"{__name__}.{name}")
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # API 클라이언트
        self.order_api = OrderTRAPI()
        self.account_api = AccountTRAPI()
        
        # 모니터링 객체들
        self.monitors: Dict[str, BaseMonitor] = {}
        
        # 포지션 및 주문 관리
        self.positions: Dict[str, Dict[str, Any]] = {}  # 종목코드: 포지션 정보
        self.orders: Dict[str, Dict[str, Any]] = {}     # 주문번호: 주문 정보
        
        # 성과 지표
        self.performance_metrics: Dict[str, float] = {
            "total_profit_loss": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }

    @abstractmethod
    def initialize(self) -> None:
        """전략 초기화"""
        pass

    @abstractmethod
    def start(self) -> None:
        """전략 실행"""
        if self.is_running:
            self.logger.warning("이미 전략이 실행 중입니다.")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        self.logger.info(f"{self.name} 전략 시작")

    @abstractmethod
    def stop(self) -> None:
        """전략 중지"""
        if not self.is_running:
            self.logger.warning("전략이 실행 중이 아닙니다.")
            return
        
        self.is_running = False
        self.end_time = datetime.now()
        self.logger.info(f"{self.name} 전략 중지")

    def add_monitor(self, name: str, monitor: BaseMonitor) -> None:
        """모니터 추가

        Args:
            name (str): 모니터 이름
            monitor (BaseMonitor): 모니터 객체
        """
        self.monitors[name] = monitor
        self.logger.debug(f"모니터 추가: {name}")

    def remove_monitor(self, name: str) -> None:
        """모니터 제거

        Args:
            name (str): 모니터 이름
        """
        if name in self.monitors:
            del self.monitors[name]
            self.logger.debug(f"모니터 제거: {name}")

    def get_monitor(self, name: str) -> Optional[BaseMonitor]:
        """모니터 조회

        Args:
            name (str): 모니터 이름

        Returns:
            Optional[BaseMonitor]: 모니터 객체
        """
        return self.monitors.get(name)

    def update_position(self, stock_code: str, position_info: Dict[str, Any]) -> None:
        """포지션 정보 업데이트

        Args:
            stock_code (str): 종목 코드
            position_info (Dict[str, Any]): 포지션 정보
        """
        self.positions[stock_code] = position_info
        self.logger.debug(f"포지션 업데이트: {stock_code}")

    def update_order(self, order_no: str, order_info: Dict[str, Any]) -> None:
        """주문 정보 업데이트

        Args:
            order_no (str): 주문번호
            order_info (Dict[str, Any]): 주문 정보
        """
        self.orders[order_no] = order_info
        self.logger.debug(f"주문 업데이트: {order_no}")

    def calculate_metrics(self) -> None:
        """성과 지표 계산"""
        # 구현 필요
        pass

    @property
    def running_time(self) -> Optional[float]:
        """실행 시간 (초)"""
        if not self.start_time:
            return None
        
        end = self.end_time if self.end_time else datetime.now()
        return (end - self.start_time).total_seconds()

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보 반환"""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "running_time": self.running_time,
            "monitors": list(self.monitors.keys()),
            "positions": len(self.positions),
            "orders": len(self.orders),
            "performance_metrics": self.performance_metrics
        } 