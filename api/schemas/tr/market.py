"""시장 전체 정보 TR API 스키마"""

from typing import List, Optional
from pydantic import BaseModel, Field

class MarketIndexRequest(BaseModel):
    """시장 지수 조회 요청 데이터"""
    market_type: str = Field(..., description="시장구분")

class MarketIndexResponse(BaseModel):
    """시장 지수 조회 응답 데이터"""
    market_type: str = Field(..., description="시장구분")
    index_name: str = Field(..., description="지수명")
    current_index: float = Field(0.0, description="현재지수")
    index_change: float = Field(0.0, description="전일대비")
    change_ratio: float = Field(0.0, description="등락률")
    trading_volume: int = Field(0, description="거래량")
    trading_value: int = Field(0, description="거래대금")
    market_status: str = Field(..., description="시장상태")

class MarketStocksRequest(BaseModel):
    """시장별 종목 리스트 조회 요청 데이터"""
    market_type: str = Field(..., description="시장구분")
    include_suspended: bool = Field(False, description="거래정지종목 포함 여부")

class MarketStockItem(BaseModel):
    """시장별 종목 정보"""
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    market_type: str = Field(..., description="시장구분")
    sector: str = Field(..., description="업종")
    is_suspended: bool = Field(False, description="거래정지여부")

class MarketStocksResponse(BaseModel):
    """시장별 종목 리스트 조회 응답 데이터"""
    market_type: str = Field(..., description="시장구분")
    total_count: int = Field(0, description="전체 종목 수")
    stocks: List[MarketStockItem] = Field(default_factory=list, description="종목 목록")

class MarketSectorsRequest(BaseModel):
    """시장별 업종 정보 조회 요청 데이터"""
    market_type: str = Field(..., description="시장구분")

class MarketSectorItem(BaseModel):
    """시장별 업종 정보"""
    sector_code: str = Field(..., description="업종코드")
    sector_name: str = Field(..., description="업종명")
    current_index: float = Field(0.0, description="현재지수")
    index_change: float = Field(0.0, description="전일대비")
    change_ratio: float = Field(0.0, description="등락률")
    trading_volume: int = Field(0, description="거래량")
    trading_value: int = Field(0, description="거래대금")

class MarketSectorsResponse(BaseModel):
    """시장별 업종 정보 조회 응답 데이터"""
    market_type: str = Field(..., description="시장구분")
    total_count: int = Field(0, description="전체 업종 수")
    sectors: List[MarketSectorItem] = Field(default_factory=list, description="업종 목록")

class MarketTradingInfoRequest(BaseModel):
    """시장별 매매 동향 조회 요청 데이터"""
    market_type: str = Field(..., description="시장구분")
    investor_type: Optional[str] = Field(None, description="투자자구분")

class MarketInvestorItem(BaseModel):
    """투자자별 매매 정보"""
    investor_type: str = Field(..., description="투자자구분")
    buy_volume: int = Field(0, description="매수수량")
    sell_volume: int = Field(0, description="매도수량")
    net_volume: int = Field(0, description="순매수수량")
    buy_value: int = Field(0, description="매수금액")
    sell_value: int = Field(0, description="매도금액")
    net_value: int = Field(0, description="순매수금액")

class MarketTradingInfoResponse(BaseModel):
    """시장별 매매 동향 조회 응답 데이터"""
    market_type: str = Field(..., description="시장구분")
    trading_date: str = Field(..., description="매매일자")
    investors: List[MarketInvestorItem] = Field(default_factory=list, description="투자자별 매매 목록") 