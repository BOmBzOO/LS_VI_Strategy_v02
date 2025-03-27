"""체결 모니터링 관리"""

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from api.realtime.websocket.websocket_manager import WebSocketManager
from api.realtime.ccld.ccld_handler import CCLDHandler
from api.constants import MarketType
from config.logging_config import setup_logger

class CCLDManager:
    """체결 모니터링 관리"""

    def __init__(self, websocket_manager: WebSocketManager, stock_info: Dict[str, Dict]):
        self.ws_manager = websocket_manager
        self.stock_info = stock_info
        self.ccld_handler = CCLDHandler()
        self.logger = setup_logger(__name__)
        
        # 구독 중인 종목 관리
        self.subscribed_stocks: Dict[str, Dict[str, Any]] = {}  # 종목코드: 구독정보
        self.monitoring_callbacks: Dict[str, List[Callable]] = {
            'price_change': [],  # 가격 변동 콜백
            'volume_change': [], # 거래량 변동 콜백
            'every_trade': []    # 모든 체결 콜백
        }

    def subscribe_stock(self, stock_code: str, 
                       price_change_callback: Optional[Callable] = None,
                       volume_change_callback: Optional[Callable] = None,
                       trade_callback: Optional[Callable] = None) -> None:
        """종목 체결 정보 구독"""
        # 이미 구독 중인 경우 콜백만 추가
        if stock_code in self.subscribed_stocks:
            self._add_callbacks(stock_code, price_change_callback, 
                              volume_change_callback, trade_callback)
            return

        # 종목 정보 확인
        stock_info = self.stock_info.get(stock_code)
        if not stock_info:
            self.logger.error(f"종목 정보를 찾을 수 없습니다: {stock_code}")
            return

        # 시장 구분에 따른 TR 코드 설정
        market_type = stock_info.get('market')
        tr_code = MarketType.KOSPI_REAL if market_type == 'KOSPI' else MarketType.KOSDAQ_REAL

        # 구독 정보 저장
        self.subscribed_stocks[stock_code] = {
            'market_type': market_type,
            'tr_code': tr_code,
            'subscribe_time': datetime.now(self.ccld_handler.kst),
            'last_price': 0,
            'last_volume': 0
        }

        # 콜백 등록
        self._add_callbacks(stock_code, price_change_callback, 
                          volume_change_callback, trade_callback)

        # 구독 시작
        self.ws_manager.subscribe(
            tr_code=tr_code,
            tr_key=stock_code,
            callback=self._handle_trade_message
        )
        self.logger.info(f"체결 정보 구독 시작: {market_type} {stock_code}")

    def unsubscribe_stock(self, stock_code: str) -> None:
        """종목 체결 정보 구독 해제"""
        if stock_code not in self.subscribed_stocks:
            return

        stock_info = self.subscribed_stocks[stock_code]
        self.ws_manager.unsubscribe(
            tr_code=stock_info['tr_code'],
            tr_key=stock_code
        )
        
        del self.subscribed_stocks[stock_code]
        self.logger.info(f"체결 정보 구독 해제: {stock_info['market_type']} {stock_code}")

    def _handle_trade_message(self, message: Dict[str, Any]) -> None:
        """체결 메시지 처리"""
        trade_data = self.ccld_handler.handle_message(message)
        if not trade_data:
            return

        stock_code = trade_data["stock_code"]
        if stock_code not in self.subscribed_stocks:
            return

        # 가격 변동 확인 및 콜백 실행
        current_price = trade_data["price"]
        last_price = self.subscribed_stocks[stock_code]["last_price"]
        if current_price != last_price:
            self._execute_callbacks('price_change', trade_data)
            self.subscribed_stocks[stock_code]["last_price"] = current_price

        # 거래량 변동 확인 및 콜백 실행
        current_volume = trade_data["total_volume"]
        last_volume = self.subscribed_stocks[stock_code]["last_volume"]
        if current_volume != last_volume:
            self._execute_callbacks('volume_change', trade_data)
            self.subscribed_stocks[stock_code]["last_volume"] = current_volume

        # 모든 체결에 대한 콜백 실행
        self._execute_callbacks('every_trade', trade_data)

    def _add_callbacks(self, stock_code: str,
                      price_change_callback: Optional[Callable] = None,
                      volume_change_callback: Optional[Callable] = None,
                      trade_callback: Optional[Callable] = None) -> None:
        """콜백 함수 추가"""
        if price_change_callback:
            if price_change_callback not in self.monitoring_callbacks['price_change']:
                self.monitoring_callbacks['price_change'].append(price_change_callback)
        
        if volume_change_callback:
            if volume_change_callback not in self.monitoring_callbacks['volume_change']:
                self.monitoring_callbacks['volume_change'].append(volume_change_callback)
        
        if trade_callback:
            if trade_callback not in self.monitoring_callbacks['every_trade']:
                self.monitoring_callbacks['every_trade'].append(trade_callback)

    def _execute_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """콜백 실행"""
        for callback in self.monitoring_callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"콜백 실행 중 오류 발생: {str(e)}")

    def get_subscribed_stocks(self) -> Dict[str, Dict[str, Any]]:
        """구독 중인 종목 목록 반환"""
        return self.subscribed_stocks.copy()

    def clear_all_subscriptions(self) -> None:
        """모든 구독 해제"""
        for stock_code in list(self.subscribed_stocks.keys()):
            self.unsubscribe_stock(stock_code)
        self.monitoring_callbacks = {
            'price_change': [],
            'volume_change': [],
            'every_trade': []
        } 