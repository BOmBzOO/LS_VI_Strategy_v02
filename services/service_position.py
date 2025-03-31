"""포지션 관리 서비스 클래스"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
import sqlite3
import json
from pathlib import Path
from config.logging_config import setup_logger
from services.service_account import AccountService
from services.service_market_data import MarketService
from services.service_order import OrderService
from services.service_monitor_account import AccountMonitorService, AccountOrderData

@dataclass
class Position:
    """포지션 정보"""
    stock_code: str              # 종목코드
    stock_name: str             # 종목명
    quantity: int               # 보유수량
    average_price: Decimal      # 평균단가
    current_price: Decimal      # 현재가
    purchase_amount: Decimal    # 매입금액
    evaluation_amount: Decimal  # 평가금액
    evaluation_profit: Decimal  # 평가손익
    profit_rate: Decimal       # 수익률
    realized_profit: Decimal   # 실현손익
    entry_date: datetime       # 진입일시
    last_update: datetime      # 최종 업데이트 일시
    stop_loss: Optional[Decimal] = None  # 손절가
    take_profit: Optional[Decimal] = None  # 익절가
    today_trading: Dict[str, Any] = None  # 당일 매매 정보
    yesterday_trading: Dict[str, Any] = None  # 전일 매매 정보

class PositionService:
    """포지션 관리 서비스 클래스"""
    
    def __init__(self, use_db: bool = False, db_path: str = "data/positions.db"):
        """초기화
        
        Args:
            use_db (bool, optional): DB 사용 여부. Defaults to False.
            db_path (str, optional): DB 파일 경로. Defaults to "data/positions.db".
        """
        self.logger = setup_logger(__name__)
        self.account_service = AccountService()
        self.market_data_service = MarketService()
        self.order_service = OrderService()
        self.positions: Dict[str, Position] = {}  # 종목코드: Position
        self.position_history: List[Dict[str, Any]] = []  # 포지션 히스토리
        self.monitor_service: Optional[AccountMonitorService] = None
        self.position_callbacks: List[Callable[[Dict[str, Any]], None]] = []  # 포지션 변경 콜백
        
        # DB 설정
        self.use_db = use_db
        if use_db:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_database()
            self._load_positions()  # DB에서 포지션 로드
        
    def _init_database(self) -> None:
        """데이터베이스 초기화"""
        if not self.use_db:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 포지션 테이블 생성
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    stock_code TEXT PRIMARY KEY,
                    stock_name TEXT,
                    quantity INTEGER,
                    average_price REAL,
                    current_price REAL,
                    purchase_amount REAL,
                    evaluation_amount REAL,
                    evaluation_profit REAL,
                    profit_rate REAL,
                    realized_profit REAL,
                    entry_date TEXT,
                    last_update TEXT,
                    stop_loss REAL,
                    take_profit REAL,
                    today_trading TEXT,
                    yesterday_trading TEXT
                )
                """)
                
                # 포지션 히스토리 테이블 생성
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT,
                    stock_name TEXT,
                    entry_date TEXT,
                    exit_date TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    quantity INTEGER,
                    realized_profit REAL,
                    profit_rate REAL
                )
                """)
                
                conn.commit()
                self.logger.info("데이터베이스 초기화 완료")
                
        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 중 오류 발생: {str(e)}")
            raise

    async def _save_position(self, position: Position) -> None:
        """포지션 데이터베이스 저장"""
        if not self.use_db:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                INSERT OR REPLACE INTO positions (
                    stock_code, stock_name, quantity, average_price, current_price,
                    purchase_amount, evaluation_amount, evaluation_profit, profit_rate,
                    realized_profit, entry_date, last_update, stop_loss, take_profit,
                    today_trading, yesterday_trading
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    position.stock_code,
                    position.stock_name,
                    position.quantity,
                    float(position.average_price),
                    float(position.current_price),
                    float(position.purchase_amount),
                    float(position.evaluation_amount),
                    float(position.evaluation_profit),
                    float(position.profit_rate),
                    float(position.realized_profit),
                    position.entry_date.isoformat(),
                    position.last_update.isoformat(),
                    float(position.stop_loss) if position.stop_loss else None,
                    float(position.take_profit) if position.take_profit else None,
                    json.dumps(position.today_trading) if position.today_trading else None,
                    json.dumps(position.yesterday_trading) if position.yesterday_trading else None
                ))
                
                conn.commit()
                self.logger.debug(f"포지션 저장 완료: {position.stock_code}")
                
        except Exception as e:
            self.logger.error(f"포지션 저장 중 오류 발생: {str(e)}")

    async def _save_position_history(self, history: Dict[str, Any]) -> None:
        """포지션 히스토리 데이터베이스 저장"""
        if not self.use_db:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                INSERT INTO position_history (
                    stock_code, stock_name, entry_date, exit_date,
                    entry_price, exit_price, quantity, realized_profit, profit_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    history['stock_code'],
                    history.get('stock_name', ''),
                    history['entry_date'].isoformat(),
                    history['exit_date'].isoformat(),
                    float(history['entry_price']),
                    float(history['exit_price']),
                    history['quantity'],
                    float(history['realized_profit']),
                    float(history['profit_rate'])
                ))
                
                conn.commit()
                self.logger.debug(f"포지션 히스토리 저장 완료: {history['stock_code']}")
                
        except Exception as e:
            self.logger.error(f"포지션 히스토리 저장 중 오류 발생: {str(e)}")

    def _load_positions(self) -> None:
        """데이터베이스에서 포지션 로드"""
        if not self.use_db:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM positions")
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    position = Position(
                        stock_code=row_dict['stock_code'],
                        stock_name=row_dict['stock_name'],
                        quantity=row_dict['quantity'],
                        average_price=Decimal(str(row_dict['average_price'])),
                        current_price=Decimal(str(row_dict['current_price'])),
                        purchase_amount=Decimal(str(row_dict['purchase_amount'])),
                        evaluation_amount=Decimal(str(row_dict['evaluation_amount'])),
                        evaluation_profit=Decimal(str(row_dict['evaluation_profit'])),
                        profit_rate=Decimal(str(row_dict['profit_rate'])),
                        realized_profit=Decimal(str(row_dict['realized_profit'])),
                        entry_date=datetime.fromisoformat(row_dict['entry_date']),
                        last_update=datetime.fromisoformat(row_dict['last_update']),
                        stop_loss=Decimal(str(row_dict['stop_loss'])) if row_dict['stop_loss'] else None,
                        take_profit=Decimal(str(row_dict['take_profit'])) if row_dict['take_profit'] else None,
                        today_trading=json.loads(row_dict['today_trading']) if row_dict['today_trading'] else None,
                        yesterday_trading=json.loads(row_dict['yesterday_trading']) if row_dict['yesterday_trading'] else None
                    )
                    self.positions[position.stock_code] = position
                    
                self.logger.info(f"포지션 로드 완료: {len(self.positions)}개")
                
        except Exception as e:
            self.logger.error(f"포지션 로드 중 오류 발생: {str(e)}")

    async def start_monitoring(self) -> None:
        """실시간 모니터링 시작"""
        try:
            # 계좌 잔고에서 포지션 초기화
            await self.initialize_positions()
            
            # 모니터링 서비스 시작
            if not self.monitor_service:
                self.monitor_service = AccountMonitorService(
                    token=self.account_service.access_token,
                    account_no=self.account_service.account_no
                )
                # 주문 체결 콜백 등록
                self.monitor_service.add_callback(self._handle_order_execution)
                await self.monitor_service.start()
                
            self.logger.info("실시간 포지션 모니터링 시작")
            
        except Exception as e:
            self.logger.error(f"실시간 모니터링 시작 중 오류 발생: {str(e)}")
            raise
            
    async def stop_monitoring(self) -> None:
        """실시간 모니터링 중지"""
        try:
            if self.monitor_service:
                await self.monitor_service.stop()
                self.monitor_service = None
            self.logger.info("실시간 포지션 모니터링 중지")
            
        except Exception as e:
            self.logger.error(f"실시간 모니터링 중지 중 오류 발생: {str(e)}")
            
    async def initialize_positions(self) -> None:
        """계좌 잔고에서 포지션 초기화"""
        try:
            # 계좌 잔고 조회
            balance = self.account_service.get_account_balance()
            if "error_code" in balance:
                raise Exception(f"잔고 조회 실패: {balance['error_message']}")
            
            # 포지션 초기화
            for stock in balance['stocks']:
                position = Position(
                    stock_code=stock['stock_code'],
                    stock_name=stock['stock_name'],
                    quantity=stock['quantity'],
                    average_price=Decimal(str(stock['average_price'])),
                    current_price=Decimal(str(stock['current_price'])),
                    purchase_amount=Decimal(str(stock['purchase_amount'])),
                    evaluation_amount=Decimal(str(stock['evaluation_amount'])),
                    evaluation_profit=Decimal(str(stock['profit_loss'])),
                    profit_rate=Decimal(str(stock['profit_loss_ratio'])),
                    realized_profit=Decimal('0'),
                    entry_date=datetime.now(),
                    last_update=datetime.now(),
                    today_trading=stock['today'],
                    yesterday_trading=stock['yesterday']
                )
                self.positions[stock['stock_code']] = position
                
            self.logger.info(f"포지션 초기화 완료: {len(self.positions)}개")
            
        except Exception as e:
            self.logger.error(f"포지션 초기화 중 오류 발생: {str(e)}")
            raise
            
    async def _handle_order_execution(self, message: Dict[str, Any]) -> None:
        """주문 체결 처리
        
        Args:
            message (Dict[str, Any]): 체결 메시지
        """
        try:
            order_data = AccountOrderData(message.get('body', {}))
            
            # 체결된 경우에만 처리
            if order_data.order_status != "11":  # 체결
                return
                
            stock_code = order_data.shcode
            exec_qty = int(order_data.exec_qty)
            exec_price = Decimal(order_data.exec_price)
            position_type = "buy" if order_data.trade_type in ["02", "04", "06"] else "sell"
            
            # 포지션 업데이트
            await self.update_position(
                stock_code=stock_code,
                quantity=exec_qty,
                price=exec_price,
                position_type=position_type,
                order_time=datetime.strptime(order_data.exec_time, "%H%M%S")
            )
            
            # 콜백 실행
            await self._notify_position_change(stock_code)
            
        except Exception as e:
            self.logger.error(f"주문 체결 처리 중 오류 발생: {str(e)}")
            
    async def update_position(self, stock_code: str, quantity: int, price: Decimal,
                            position_type: str, order_time: datetime) -> None:
        """포지션 업데이트
        
        Args:
            stock_code (str): 종목코드
            quantity (int): 수량
            price (Decimal): 가격
            position_type (str): 포지션 타입 (buy/sell)
            order_time (datetime): 주문시간
        """
        try:
            current_position = self.positions.get(stock_code)
            
            if position_type == "buy":
                if current_position:
                    # 기존 포지션에 추가
                    total_quantity = current_position.quantity + quantity
                    total_amount = (current_position.average_price * current_position.quantity) + (price * quantity)
                    new_average_price = total_amount / total_quantity
                    
                    current_position.quantity = total_quantity
                    current_position.average_price = new_average_price
                    current_position.purchase_amount = total_amount
                    current_position.evaluation_amount = total_amount
                    current_position.last_update = datetime.now()
                    
                    # 당일 매매 정보 업데이트
                    if not current_position.today_trading:
                        current_position.today_trading = {"buy_amount": 0, "buy_price": 0, "sell_amount": 0, "sell_price": 0}
                    current_position.today_trading["buy_amount"] += price * quantity
                    current_position.today_trading["buy_price"] = float(price)
                    await self._save_position(current_position)
                else:
                    # 새로운 포지션 생성
                    self.positions[stock_code] = Position(
                        stock_code=stock_code,
                        stock_name=await self._get_stock_name(stock_code),
                        quantity=quantity,
                        average_price=price,
                        current_price=price,
                        purchase_amount=price * quantity,
                        evaluation_amount=price * quantity,
                        evaluation_profit=Decimal('0'),
                        profit_rate=Decimal('0'),
                        realized_profit=Decimal('0'),
                        entry_date=order_time,
                        last_update=datetime.now(),
                        today_trading={"buy_amount": float(price * quantity), "buy_price": float(price), 
                                     "sell_amount": 0, "sell_price": 0},
                        yesterday_trading={"buy_amount": 0, "buy_price": 0, "sell_amount": 0, "sell_price": 0}
                    )
                    await self._save_position(self.positions[stock_code])
            
            elif position_type == "sell":
                if current_position:
                    # 실현손익 계산
                    realized_profit = (price - current_position.average_price) * quantity
                    current_position.realized_profit += realized_profit
                    
                    # 수량 감소
                    current_position.quantity -= quantity
                    current_position.purchase_amount = current_position.average_price * current_position.quantity
                    current_position.evaluation_amount = current_position.current_price * current_position.quantity
                    current_position.last_update = datetime.now()
                    
                    # 당일 매매 정보 업데이트
                    if not current_position.today_trading:
                        current_position.today_trading = {"buy_amount": 0, "buy_price": 0, "sell_amount": 0, "sell_price": 0}
                    current_position.today_trading["sell_amount"] += price * quantity
                    current_position.today_trading["sell_price"] = float(price)
                    
                    # 포지션 종료 시 히스토리 저장
                    if current_position.quantity <= 0:
                        history = await self._add_to_history(current_position, price, order_time)
                        await self._save_position_history(history)
                        del self.positions[stock_code]
                    else:
                        await self._save_position(current_position)
                
            self.logger.info(f"포지션 업데이트 완료: {stock_code}")
            
        except Exception as e:
            self.logger.error(f"포지션 업데이트 중 오류 발생: {str(e)}")
            
    async def _get_stock_name(self, stock_code: str) -> str:
        """종목명 조회"""
        try:
            stock_info = await self.market_data_service.get_stock_info(stock_code)
            return stock_info.get('stock_name', stock_code)
        except:
            return stock_code
            
    def add_position_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """포지션 변경 콜백 등록"""
        if callback not in self.position_callbacks:
            self.position_callbacks.append(callback)
            
    def remove_position_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """포지션 변경 콜백 제거"""
        if callback in self.position_callbacks:
            self.position_callbacks.remove(callback)
            
    async def _notify_position_change(self, stock_code: str) -> None:
        """포지션 변경 알림"""
        try:
            position = self.positions.get(stock_code)
            if position:
                position_data = {
                    "stock_code": position.stock_code,
                    "stock_name": position.stock_name,
                    "quantity": position.quantity,
                    "average_price": float(position.average_price),
                    "current_price": float(position.current_price),
                    "evaluation_profit": float(position.evaluation_profit),
                    "profit_rate": float(position.profit_rate),
                    "realized_profit": float(position.realized_profit),
                    "stop_loss": float(position.stop_loss) if position.stop_loss else None,
                    "take_profit": float(position.take_profit) if position.take_profit else None,
                    "today_trading": position.today_trading,
                    "yesterday_trading": position.yesterday_trading,
                    "last_update": position.last_update.isoformat()
                }
                
                for callback in self.position_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(position_data)
                        else:
                            callback(position_data)
                    except Exception as e:
                        self.logger.error(f"포지션 변경 콜백 실행 중 오류: {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"포지션 변경 알림 중 오류 발생: {str(e)}")
            
    def update_current_prices(self) -> None:
        """현재가 업데이트"""
        try:
            for stock_code in self.positions:
                price_info = self.market_data_service.get_price(stock_code)
                position = self.positions[stock_code]
                
                position.current_price = Decimal(str(price_info['close']))
                position.evaluation_amount = position.current_price * position.quantity
                position.evaluation_profit = position.evaluation_amount - position.purchase_amount
                position.profit_rate = (position.evaluation_profit / position.purchase_amount) * 100
                position.last_update = datetime.now()
                
                # 손절/익절 체크
                self._check_stop_conditions(position)
                
            self.logger.debug("현재가 업데이트 완료")
            
        except Exception as e:
            self.logger.error(f"현재가 업데이트 중 오류 발생: {str(e)}")
            
    def set_stop_conditions(self, stock_code: str, stop_loss: Optional[Decimal] = None, 
                          take_profit: Optional[Decimal] = None) -> None:
        """손절/익절 조건 설정
        
        Args:
            stock_code (str): 종목코드
            stop_loss (Optional[Decimal], optional): 손절가. Defaults to None.
            take_profit (Optional[Decimal], optional): 익절가. Defaults to None.
        """
        try:
            if stock_code in self.positions:
                position = self.positions[stock_code]
                position.stop_loss = stop_loss
                position.take_profit = take_profit
                self.logger.info(f"손절/익절 조건 설정: {stock_code} (손절가: {stop_loss}, 익절가: {take_profit})")
            
        except Exception as e:
            self.logger.error(f"손절/익절 조건 설정 중 오류 발생: {str(e)}")
            
    def _check_stop_conditions(self, position: Position) -> None:
        """손절/익절 조건 체크
        
        Args:
            position (Position): 포지션 정보
        """
        try:
            if position.stop_loss and position.current_price <= position.stop_loss:
                self.logger.warning(f"손절가 도달: {position.stock_code} (현재가: {position.current_price}, 손절가: {position.stop_loss})")
                # 시장가 매도 주문
                self.order_service.order_market(
                    stock_code=position.stock_code,
                    quantity=position.quantity,
                    price=0,
                    order_type="sell"
                )
                
            elif position.take_profit and position.current_price >= position.take_profit:
                self.logger.info(f"익절가 도달: {position.stock_code} (현재가: {position.current_price}, 익절가: {position.take_profit})")
                # 시장가 매도 주문
                self.order_service.order_market(
                    stock_code=position.stock_code,
                    quantity=position.quantity,
                    price=0,
                    order_type="sell"
                )
                
        except Exception as e:
            self.logger.error(f"손절/익절 조건 체크 중 오류 발생: {str(e)}")
            
    async def _add_to_history(self, position: Position, exit_price: Decimal, exit_time: datetime) -> Dict[str, Any]:
        """포지션 히스토리 추가"""
        try:
            history = {
                "stock_code": position.stock_code,
                "stock_name": position.stock_name,
                "entry_date": position.entry_date,
                "exit_date": exit_time,
                "entry_price": position.average_price,
                "exit_price": exit_price,
                "quantity": position.quantity,
                "realized_profit": position.realized_profit,
                "profit_rate": ((exit_price - position.average_price) / position.average_price) * 100
            }
            self.position_history.append(history)
            await self._save_position_history(history)
            self.logger.info(f"포지션 히스토리 추가: {position.stock_code}")
            return history
            
        except Exception as e:
            self.logger.error(f"포지션 히스토리 추가 중 오류 발생: {str(e)}")
            return {}
            
    def get_position_summary(self) -> Dict[str, Any]:
        """포지션 요약 정보 조회
        
        Returns:
            Dict[str, Any]: 포지션 요약 정보
        """
        try:
            total_purchase = sum(p.purchase_amount for p in self.positions.values())
            total_evaluation = sum(p.evaluation_amount for p in self.positions.values())
            total_profit = sum(p.evaluation_profit for p in self.positions.values())
            total_realized = sum(p.realized_profit for p in self.positions.values())
            
            return {
                "position_count": len(self.positions),
                "total_purchase": total_purchase,
                "total_evaluation": total_evaluation,
                "total_profit": total_profit,
                "total_realized": total_realized,
                "total_profit_rate": (total_profit / total_purchase * 100) if total_purchase else Decimal('0')
            }
            
        except Exception as e:
            self.logger.error(f"포지션 요약 정보 조회 중 오류 발생: {str(e)}")
            return {}
            
    def get_position_history_summary(self) -> Dict[str, Any]:
        """포지션 히스토리 요약 정보 조회
        
        Returns:
            Dict[str, Any]: 포지션 히스토리 요약 정보
        """
        try:
            if not self.position_history:
                return {}
                
            total_trades = len(self.position_history)
            winning_trades = sum(1 for h in self.position_history if h['realized_profit'] > 0)
            total_profit = sum(h['realized_profit'] for h in self.position_history)
            
            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": (winning_trades / total_trades * 100) if total_trades else 0,
                "total_profit": total_profit,
                "average_profit": total_profit / total_trades if total_trades else 0
            }
            
        except Exception as e:
            self.logger.error(f"포지션 히스토리 요약 정보 조회 중 오류 발생: {str(e)}")
            return {} 