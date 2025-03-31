"""실시간 지수 API"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from api.tr.tr_base import BaseAPI
from api.constants import TRCode, MarketType
from config.logging_config import setup_logger

class IndexHandler:
    """실시간 지수 메시지 핸들러"""

    def __init__(self):
        self.logger = setup_logger(__name__)

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """실시간 지수 메시지 처리"""
        try:
            # 메시지 파싱
            result = {
                "market_type": message.get("시장구분"),
                "index_name": message.get("지수명"),
                "current_index": float(message.get("현재지수", 0.0)),
                "index_change": float(message.get("전일대비", 0.0)),
                "change_ratio": float(message.get("등락률", 0.0)),
                "trading_volume": int(message.get("거래량", 0)),
                "trading_value": int(message.get("거래대금", 0)),
                "market_status": message.get("시장상태"),
                "time": message.get("시간")
            }

            return result

        except Exception as e:
            self.logger.error(f"실시간 지수 메시지 처리 중 오류 발생: {str(e)}")
            return None

    def handle_error(self, error: Dict[str, Any]) -> None:
        """에러 메시지 처리"""
        self.logger.error(f"실시간 지수 에러 발생: {error}")

class IndexManager:
    """실시간 지수 관리"""

    def __init__(self, websocket_manager):
        self.ws_manager = websocket_manager
        self.index_handler = IndexHandler()
        self.logger = setup_logger(__name__)
        
        # 구독 중인 지수 관리
        self.subscribed_indices: Dict[str, Dict[str, Any]] = {}  # 시장구분: 구독정보
        self.monitoring_callbacks: Dict[str, List[Callable]] = {
            'index_change': [],     # 지수 변동 콜백
            'market_status': [],    # 시장 상태 변경 콜백
            'every_tick': []        # 모든 틱 콜백
        }

    def subscribe_index(self, 
                       market_type: MarketType,
                       index_change_callback: Optional[Callable] = None,
                       market_status_callback: Optional[Callable] = None,
                       tick_callback: Optional[Callable] = None) -> None:
        """지수 구독"""
        # 이미 구독 중인 경우 콜백만 추가
        if market_type.value in self.subscribed_indices:
            self._add_callbacks(market_type.value, index_change_callback, 
                              market_status_callback, tick_callback)
            return

        # 구독 정보 저장
        self.subscribed_indices[market_type.value] = {
            'market_type': market_type.value,
            'subscribe_time': datetime.now(),
            'last_index': 0.0,
            'last_status': None
        }

        # 콜백 등록
        self._add_callbacks(market_type.value, index_change_callback, 
                          market_status_callback, tick_callback)

        # 구독 시작
        self.ws_manager.subscribe(
            tr_code=TRCode.INDEX_REAL,
            tr_key=market_type.value,
            callback=self._handle_index_message
        )
        self.logger.info(f"지수 구독 시작: {market_type.value}")

    def unsubscribe_index(self, market_type: MarketType) -> None:
        """지수 구독 해제"""
        if market_type.value not in self.subscribed_indices:
            return

        self.ws_manager.unsubscribe(
            tr_code=TRCode.INDEX_REAL,
            tr_key=market_type.value
        )
        
        del self.subscribed_indices[market_type.value]
        self.logger.info(f"지수 구독 해제: {market_type.value}")

    def _handle_index_message(self, message: Dict[str, Any]) -> None:
        """지수 메시지 처리"""
        index_data = self.index_handler.handle_message(message)
        if not index_data:
            return

        market_type = index_data["market_type"]
        if market_type not in self.subscribed_indices:
            return

        # 지수 변동 확인 및 콜백 실행
        current_index = index_data["current_index"]
        last_index = self.subscribed_indices[market_type]["last_index"]
        if current_index != last_index:
            self._execute_callbacks('index_change', index_data)
            self.subscribed_indices[market_type]["last_index"] = current_index

        # 시장 상태 변경 확인 및 콜백 실행
        current_status = index_data["market_status"]
        last_status = self.subscribed_indices[market_type]["last_status"]
        if current_status != last_status:
            self._execute_callbacks('market_status', index_data)
            self.subscribed_indices[market_type]["last_status"] = current_status

        # 모든 틱 콜백 실행
        self._execute_callbacks('every_tick', index_data)

    def _add_callbacks(self, market_type: str,
                      index_change_callback: Optional[Callable] = None,
                      market_status_callback: Optional[Callable] = None,
                      tick_callback: Optional[Callable] = None) -> None:
        """콜백 함수 추가"""
        if index_change_callback:
            if index_change_callback not in self.monitoring_callbacks['index_change']:
                self.monitoring_callbacks['index_change'].append(index_change_callback)
        
        if market_status_callback:
            if market_status_callback not in self.monitoring_callbacks['market_status']:
                self.monitoring_callbacks['market_status'].append(market_status_callback)
        
        if tick_callback:
            if tick_callback not in self.monitoring_callbacks['every_tick']:
                self.monitoring_callbacks['every_tick'].append(tick_callback)

    def _execute_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """콜백 실행"""
        for callback in self.monitoring_callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"콜백 실행 중 오류 발생: {str(e)}")

    def get_subscribed_indices(self) -> Dict[str, Dict[str, Any]]:
        """구독 중인 지수 목록 반환"""
        return self.subscribed_indices.copy()

    def clear_all_subscriptions(self) -> None:
        """모든 구독 해제"""
        for market_type in list(self.subscribed_indices.keys()):
            self.unsubscribe_index(MarketType(market_type))
        self.monitoring_callbacks = {
            'index_change': [],
            'market_status': [],
            'every_tick': []
        } 