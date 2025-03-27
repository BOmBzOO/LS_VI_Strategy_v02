"""실시간 지수 메시지 스키마"""

from typing import Optional
from pydantic import BaseModel, Field

class IndexMessage(BaseModel):
    """실시간 지수 메시지"""
    market_type: str = Field(..., description="시장구분")
    index_name: str = Field(..., description="지수명")
    current_index: float = Field(0.0, description="현재지수")
    index_change: float = Field(0.0, description="전일대비")
    change_ratio: float = Field(0.0, description="등락률")
    trading_volume: int = Field(0, description="거래량")
    trading_value: int = Field(0, description="거래대금")
    market_status: str = Field(..., description="시장상태")
    time: str = Field(..., description="시간")

class IndexSubscribeRequest(BaseModel):
    """지수 구독 요청 데이터"""
    market_type: str = Field(..., description="시장구분")

class IndexUnsubscribeRequest(BaseModel):
    """지수 구독 해제 요청 데이터"""
    market_type: str = Field(..., description="시장구분")

class IndexSubscriptionInfo(BaseModel):
    """지수 구독 정보"""
    market_type: str = Field(..., description="시장구분")
    subscribe_time: str = Field(..., description="구독 시작 시간")
    last_index: float = Field(0.0, description="마지막 지수")
    last_status: Optional[str] = Field(None, description="마지막 시장상태") 