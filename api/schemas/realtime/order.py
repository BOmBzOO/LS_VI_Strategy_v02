"""실시간 주문 메시지 스키마"""

from typing import Optional
from pydantic import BaseModel, Field

class OrderAcceptedMessage(BaseModel):
    """주문 접수 메시지"""
    order_no: str = Field(..., description="주문번호")
    stock_code: str = Field(..., description="종목코드")
    order_type: str = Field(..., description="주문구분")
    order_price: Optional[int] = Field(None, description="주문가격")
    order_quantity: int = Field(..., description="주문수량")
    order_time: str = Field(..., description="주문시각")
    message: Optional[str] = Field(None, description="메시지")

class OrderFilledMessage(BaseModel):
    """주문 체결 메시지"""
    order_no: str = Field(..., description="주문번호")
    stock_code: str = Field(..., description="종목코드")
    filled_price: int = Field(..., description="체결가격")
    filled_quantity: int = Field(..., description="체결수량")
    remaining_quantity: int = Field(..., description="미체결수량")
    filled_time: str = Field(..., description="체결시각")
    trade_no: str = Field(..., description="체결번호")

class OrderCancelledMessage(BaseModel):
    """주문 취소 메시지"""
    order_no: str = Field(..., description="주문번호")
    stock_code: str = Field(..., description="종목코드")
    cancelled_quantity: int = Field(..., description="취소수량")
    cancel_time: str = Field(..., description="취소시각")
    message: Optional[str] = Field(None, description="메시지")

class OrderRejectedMessage(BaseModel):
    """주문 거부 메시지"""
    order_no: str = Field(..., description="주문번호")
    stock_code: str = Field(..., description="종목코드")
    reject_reason: str = Field(..., description="거부사유")
    reject_time: str = Field(..., description="거부시각")
    message: Optional[str] = Field(None, description="메시지") 