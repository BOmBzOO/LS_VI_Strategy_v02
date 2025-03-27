"""실시간 체결 처리 핸들러"""

from typing import Dict, Any, Callable, List
from config.logging_config import setup_logger

class CCLDHandler:
    """체결 데이터 처리 핸들러"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.callbacks: Dict[str, List[Callable]] = {}
        
    def add_callback(self, event_type: str, callback: Callable) -> None:
        """콜백 함수 등록
        
        Args:
            event_type (str): 이벤트 타입
            callback (Callable): 콜백 함수
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
        
    def handle_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """이벤트 처리
        
        Args:
            event_type (str): 이벤트 타입
            data (Dict[str, Any]): 이벤트 데이터
        """
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"콜백 실행 중 오류 발생: {str(e)}")
                    
    def remove_callback(self, event_type: str, callback: Callable) -> None:
        """콜백 함수 제거
        
        Args:
            event_type (str): 이벤트 타입
            callback (Callable): 콜백 함수
        """
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)

    def handle_message(self, message: Dict[str, Any]) -> None:
        """체결 메시지 처리"""
        try:
            parsed_data = self.parse_ccld_data(message)
            formatted_message = self.format_message(parsed_data)
            self.logger.info(formatted_message)
            return parsed_data
        except Exception as e:
            self.handle_error(e)
            return None

    def handle_error(self, error: Exception) -> None:
        """체결 에러 처리"""
        self.logger.error(f"체결 메시지 처리 중 오류 발생: {str(error)}")

    def parse_ccld_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """체결 데이터 파싱"""
        body = message.get("body", {})
        return {
            "stock_code": body.get("shcode"),
            "price": int(body.get("price", 0)),
            "volume": int(body.get("cvolume", 0)),
            "total_volume": int(body.get("volume", 0)),
            "change_price": int(body.get("change", 0)),
            "change_rate": float(body.get("diff", 0)),
            "trade_time": body.get("time"),
            "received_time": self.get_current_time(),
            "market_type": message.get("header", {}).get("tr_cd", "")
        }

    def format_message(self, data: Dict[str, Any]) -> str:
        """체결 메시지 포맷팅"""
        timestamp = self.get_timestamp()
        
        # 가격 변동 표시
        change_price = data["change_price"]
        change_mark = "▲" if change_price > 0 else "▼" if change_price < 0 else "-"
        change_price_abs = abs(change_price)
        
        return (f"[{timestamp}] 체결 | "
                f"{data['market_type']} {data['stock_code']} | "
                f"가격: {data['price']:,}원 ({change_mark}{change_price_abs:,}) | "
                f"수량: {data['volume']:,}주 | "
                f"변동률: {data['change_rate']:+.2f}%")

    def is_price_up(self, data: Dict[str, Any]) -> bool:
        """가격 상승 여부 확인"""
        return data.get("change_price", 0) > 0

    def is_price_down(self, data: Dict[str, Any]) -> bool:
        """가격 하락 여부 확인"""
        return data.get("change_price", 0) < 0

    def get_price_change_rate(self, data: Dict[str, Any]) -> float:
        """가격 변동률 반환"""
        return data.get("change_rate", 0.0) 