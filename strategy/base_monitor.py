"""기본 모니터링 클래스

모든 모니터링 클래스의 기본이 되는 추상 클래스입니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, time
from config.logging_config import setup_logger

class BaseMonitor(ABC):
    """기본 모니터링 클래스"""

    def __init__(self, name: str):
        """
        Args:
            name (str): 모니터 이름
        """
        self.name = name
        self.logger = setup_logger(f"{__name__}.{name}")
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.callbacks: Dict[str, List[Callable]] = {}

    @abstractmethod
    def start(self) -> None:
        """모니터링 시작"""
        if self.is_running:
            self.logger.warning("이미 모니터링이 실행 중입니다.")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        self.logger.info(f"{self.name} 모니터링 시작")

    @abstractmethod
    def stop(self) -> None:
        """모니터링 중지"""
        if not self.is_running:
            self.logger.warning("모니터링이 실행 중이 아닙니다.")
            return
        
        self.is_running = False
        self.end_time = datetime.now()
        self.logger.info(f"{self.name} 모니터링 중지")

    def add_callback(self, event_type: str, callback: Callable) -> None:
        """콜백 함수 추가

        Args:
            event_type (str): 이벤트 타입
            callback (Callable): 콜백 함수
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        
        if callback not in self.callbacks[event_type]:
            self.callbacks[event_type].append(callback)
            self.logger.debug(f"콜백 함수 추가: {event_type}")

    def remove_callback(self, event_type: str, callback: Callable) -> None:
        """콜백 함수 제거

        Args:
            event_type (str): 이벤트 타입
            callback (Callable): 콜백 함수
        """
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            self.logger.debug(f"콜백 함수 제거: {event_type}")

    def clear_callbacks(self, event_type: Optional[str] = None) -> None:
        """콜백 함수 초기화

        Args:
            event_type (Optional[str]): 이벤트 타입. None인 경우 모든 콜백 초기화
        """
        if event_type:
            if event_type in self.callbacks:
                self.callbacks[event_type] = []
                self.logger.debug(f"콜백 함수 초기화: {event_type}")
        else:
            self.callbacks = {}
            self.logger.debug("모든 콜백 함수 초기화")

    def execute_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """콜백 함수 실행

        Args:
            event_type (str): 이벤트 타입
            data (Dict[str, Any]): 콜백에 전달할 데이터
        """
        if event_type not in self.callbacks:
            return

        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"콜백 실행 중 오류 발생: {str(e)}")

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
            "callback_types": list(self.callbacks.keys())
        } 