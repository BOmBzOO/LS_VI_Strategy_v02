"""API 관련 예외 클래스 정의"""

class LSTradeError(Exception):
    """LS 트레이딩 기본 예외 클래스"""
    pass

class APIError(LSTradeError):
    """API 호출 관련 에러"""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class TokenError(APIError):
    """토큰 관련 에러"""
    pass

class WebSocketError(LSTradeError):
    """웹소켓 관련 에러"""
    pass

class ValidationError(LSTradeError):
    """데이터 검증 에러"""
    pass

class OrderError(LSTradeError):
    """주문 관련 에러"""
    pass

class ConfigError(LSTradeError):
    """설정 관련 에러"""
    pass 