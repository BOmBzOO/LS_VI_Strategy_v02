"""실시간 주문 처리 핸들러"""

from typing import Dict, Any, Callable, List
from config.logging_config import setup_logger

class OrderHandler:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.callbacks: Dict[str, List[Callable]] = {}
        
    def add_callback(self, event_type: str, callback: Callable) -> None:
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
        
    def handle_event(self, event_type: str, data: Dict[str, Any]) -> None:
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                callback(data) 