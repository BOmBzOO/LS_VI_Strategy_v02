"""VI 모니터링 전략

토큰 발급, 주식 리스트 조회, VI 모니터링을 순차적으로 수행하는 전략 클래스를 제공합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import sys
import os
import signal
from contextlib import asynccontextmanager

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import setup_logger
from services.token_service import TokenService
from services.market_service import MarketService
from services.vi_monitor_service import VIMonitorService, VIData
from api.constants import MarketType, VIStatus, TRCode
from api.realtime.websocket.websocket_base import WebSocketState

from strategy.vi_strategy.VI_strategy import VIStrategy

async def main():
    """메인 함수"""
    strategy = VIStrategy()
    
    try:
        await strategy.run()
    except KeyboardInterrupt:
        await strategy.stop()
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        await strategy.stop()

if __name__ == "__main__":
    asyncio.run(main()) 