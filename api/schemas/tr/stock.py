"""주식 시세/종목 정보 TR API 스키마"""

from typing import List, Optional
from pydantic import BaseModel, Field

class StockInfoRequest(BaseModel):
    """종목 정보 조회 요청 데이터"""
    stock_code: str = Field(..., description="종목코드")

class StockInfoResponse(BaseModel):
    """종목 정보 조회 응답 데이터"""
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    market_type: str = Field(..., description="시장구분")
    sector: str = Field(..., description="업종")
    par_value: int = Field(0, description="액면가")
    listing_date: str = Field(..., description="상장일자")
    capital: int = Field(0, description="자본금")
    shares: int = Field(0, description="상장주식수")

class StockPriceRequest(BaseModel):
    """현재가 조회 요청 데이터"""
    stock_code: str = Field(..., description="종목코드")

class StockPriceResponse(BaseModel):
    """현재가 조회 응답 데이터"""
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    current_price: int = Field(0, description="현재가")
    price_change: int = Field(0, description="전일대비")
    change_ratio: float = Field(0.0, description="등락률")
    open_price: int = Field(0, description="시가")
    high_price: int = Field(0, description="고가")
    low_price: int = Field(0, description="저가")
    trading_volume: int = Field(0, description="거래량")
    trading_value: int = Field(0, description="거래대금")

class OrderbookRequest(BaseModel):
    """호가 조회 요청 데이터"""
    stock_code: str = Field(..., description="종목코드")

class OrderbookItem(BaseModel):
    """호가 정보"""
    price: int = Field(0, description="호가가격")
    quantity: int = Field(0, description="잔량")
    orders: int = Field(0, description="건수")

class OrderbookResponse(BaseModel):
    """호가 조회 응답 데이터"""
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    total_ask_quantity: int = Field(0, description="총매도잔량")
    total_bid_quantity: int = Field(0, description="총매수잔량")
    asks: List[OrderbookItem] = Field(default_factory=list, description="매도호가 목록")
    bids: List[OrderbookItem] = Field(default_factory=list, description="매수호가 목록")

class ChartRequest(BaseModel):
    """차트 데이터 조회 요청 데이터"""
    stock_code: str = Field(..., description="종목코드")
    interval: str = Field(..., description="차트 주기 (1일, 1주, 1월, 1분, 5분, ...)")
    count: Optional[int] = Field(None, description="요청 개수")
    start_date: Optional[str] = Field(None, description="시작일자 (YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="종료일자 (YYYYMMDD)")

class ChartItem(BaseModel):
    """차트 데이터"""
    date: str = Field(..., description="일자")
    time: Optional[str] = Field(None, description="시간")
    open: int = Field(0, description="시가")
    high: int = Field(0, description="고가")
    low: int = Field(0, description="저가")
    close: int = Field(0, description="종가")
    volume: int = Field(0, description="거래량")
    value: int = Field(0, description="거래대금")

class ChartResponse(BaseModel):
    """차트 데이터 조회 응답 데이터"""
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    interval: str = Field(..., description="차트 주기")
    charts: List[ChartItem] = Field(default_factory=list, description="차트 데이터 목록") 