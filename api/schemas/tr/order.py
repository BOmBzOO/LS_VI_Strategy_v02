"""주문 TR API 스키마"""

from typing import List, Optional
from pydantic import BaseModel, Field

class OrderRequest(BaseModel):
    """주문 요청 데이터"""
    account_no: str = Field(..., description="계좌번호")
    stock_code: str = Field(..., description="종목코드")
    order_type: str = Field(..., description="주문유형 (1: 매도, 2: 매수, 3: 취소, 4: 정정)")
    price_type: str = Field(..., description="가격유형 (00: 지정가, 03: 시장가, 05: 조건부지정가)")
    quantity: int = Field(..., description="주문수량", gt=0)
    price: Optional[int] = Field(None, description="주문가격 (지정가 주문 시)")
    original_order_no: Optional[str] = Field(None, description="원주문번호 (취소/정정 주문 시)")

class OrderResponse(BaseModel):
    """주문 응답 데이터"""
    order_no: Optional[str] = Field(None, description="주문번호")
    status: Optional[str] = Field(None, description="주문상태")
    message: Optional[str] = Field(None, description="응답메시지")
    error_code: Optional[str] = Field(None, description="에러코드")
    error_message: Optional[str] = Field(None, description="에러메시지")

class OrderStatusRequest(BaseModel):
    """주문 상태 조회 요청 데이터"""
    order_no: str = Field(..., description="주문번호")

class OrderStatusResponse(BaseModel):
    """주문 상태 조회 응답 데이터"""
    order_no: str = Field(..., description="주문번호")
    stock_code: str = Field(..., description="종목코드")
    order_type: str = Field(..., description="주문구분")
    order_price: Optional[int] = Field(None, description="주문가격")
    order_quantity: int = Field(..., description="주문수량")
    filled_quantity: int = Field(0, description="체결수량")
    remaining_quantity: int = Field(..., description="미체결수량")
    order_status: str = Field(..., description="주문상태")
    order_time: str = Field(..., description="주문시각")
    filled_time: Optional[str] = Field(None, description="체결시각")

class OrderHistoryRequest(BaseModel):
    """주문 내역 조회 요청 데이터"""
    account_no: str = Field(..., description="계좌번호")
    start_date: Optional[str] = Field(None, description="조회 시작일자 (YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="조회 종료일자 (YYYYMMDD)")

class OrderHistoryItem(BaseModel):
    """주문 내역 아이템"""
    order_no: str = Field(..., description="주문번호")
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    order_type: str = Field(..., description="주문구분")
    order_price: Optional[int] = Field(None, description="주문가격")
    order_quantity: int = Field(..., description="주문수량")
    filled_quantity: int = Field(0, description="체결수량")
    remaining_quantity: int = Field(..., description="미체결수량")
    order_status: str = Field(..., description="주문상태")
    order_time: str = Field(..., description="주문시각")
    filled_time: Optional[str] = Field(None, description="체결시각")

class OrderHistoryResponse(BaseModel):
    """주문 내역 조회 응답 데이터"""
    orders: List[OrderHistoryItem] = Field(default_factory=list, description="주문 내역 목록")
    total_count: int = Field(0, description="전체 주문 수") 