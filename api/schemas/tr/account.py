"""계좌 TR API 스키마"""

from typing import List, Optional
from pydantic import BaseModel, Field

class AccountInfoRequest(BaseModel):
    """계좌 정보 조회 요청 데이터"""
    account_no: str = Field(..., description="계좌번호")

class AccountInfoResponse(BaseModel):
    """계좌 정보 조회 응답 데이터"""
    account_no: str = Field(..., description="계좌번호")
    account_name: str = Field(..., description="계좌명")
    account_type: str = Field(..., description="계좌구분")
    deposit: int = Field(0, description="예수금")
    available_amount: int = Field(0, description="주문가능금액")
    total_balance: int = Field(0, description="잔고평가금액")
    total_profit_loss: int = Field(0, description="평가손익금액")
    profit_loss_ratio: float = Field(0.0, description="수익률")

class BalanceRequest(BaseModel):
    """잔고 조회 요청 데이터"""
    account_no: str = Field(..., description="계좌번호")

class BalanceStockItem(BaseModel):
    """보유 종목 정보"""
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    quantity: int = Field(0, description="보유수량")
    average_price: int = Field(0, description="평균단가")
    current_price: int = Field(0, description="현재가")
    total_amount: int = Field(0, description="평가금액")
    profit_loss: int = Field(0, description="평가손익")
    profit_loss_ratio: float = Field(0.0, description="수익률")
    available_quantity: int = Field(0, description="매도가능수량")

class BalanceResponse(BaseModel):
    """잔고 조회 응답 데이터"""
    account_no: str = Field(..., description="계좌번호")
    total_balance: int = Field(0, description="잔고평가금액")
    total_profit_loss: int = Field(0, description="평가손익금액")
    profit_loss_ratio: float = Field(0.0, description="수익률")
    stocks: List[BalanceStockItem] = Field(default_factory=list, description="보유종목 목록")

class DepositRequest(BaseModel):
    """예수금 조회 요청 데이터"""
    account_no: str = Field(..., description="계좌번호")

class DepositResponse(BaseModel):
    """예수금 조회 응답 데이터"""
    account_no: str = Field(..., description="계좌번호")
    deposit: int = Field(0, description="예수금")
    d1: int = Field(0, description="D+1예수금")
    d2: int = Field(0, description="D+2예수금")
    available_amount: int = Field(0, description="주문가능금액")
    withdraw_available: int = Field(0, description="출금가능금액")
    loan_amount: int = Field(0, description="대출금액")

class TradingHistoryRequest(BaseModel):
    """매매 이력 조회 요청 데이터"""
    account_no: str = Field(..., description="계좌번호")
    start_date: Optional[str] = Field(None, description="조회 시작일자 (YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="조회 종료일자 (YYYYMMDD)")

class TradingHistoryItem(BaseModel):
    """매매 이력 아이템"""
    trade_date: str = Field(..., description="매매일자")
    stock_code: str = Field(..., description="종목코드")
    stock_name: str = Field(..., description="종목명")
    trade_type: str = Field(..., description="매매구분")
    quantity: int = Field(0, description="매매수량")
    price: int = Field(0, description="매매단가")
    amount: int = Field(0, description="매매금액")
    fee: int = Field(0, description="수수료")
    tax: int = Field(0, description="세금")
    profit_loss: int = Field(0, description="손익금액")

class TradingHistoryResponse(BaseModel):
    """매매 이력 조회 응답 데이터"""
    trades: List[TradingHistoryItem] = Field(default_factory=list, description="매매 이력 목록")
    total_count: int = Field(0, description="전체 거래 수")
    total_profit_loss: int = Field(0, description="총 손익금액") 