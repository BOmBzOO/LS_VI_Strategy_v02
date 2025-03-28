"""로깅 설정

로깅 설정을 제공하는 모듈입니다.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler

class StructuredLogger:
    """구조화된 로깅 클래스"""
    
    def __init__(self, name: str):
        """초기화
        
        Args:
            name (str): 로거 이름
        """
        self.logger = setup_logger(name)
        self.context: Dict[str, Any] = {}
        
    def bind(self, **kwargs) -> 'StructuredLogger':
        """컨텍스트 바인딩
        
        Args:
            **kwargs: 바인딩할 컨텍스트
            
        Returns:
            StructuredLogger: 현재 인스턴스
        """
        self.context.update(kwargs)
        return self
        
    def log(self, level: str, message: str, **kwargs) -> None:
        """로그 기록
        
        Args:
            level (str): 로그 레벨
            message (str): 로그 메시지
            **kwargs: 추가 컨텍스트
        """
        context = {**self.context, **kwargs}
        getattr(self.logger, level)(message, **context)
        
    def info(self, message: str, **kwargs) -> None:
        """정보 로그 기록"""
        self.log("info", message, **kwargs)
        
    def error(self, message: str, **kwargs) -> None:
        """에러 로그 기록"""
        self.log("error", message, **kwargs)
        
    def warning(self, message: str, **kwargs) -> None:
        """경고 로그 기록"""
        self.log("warning", message, **kwargs)
        
    def debug(self, message: str, **kwargs) -> None:
        """디버그 로그 기록"""
        self.log("debug", message, **kwargs)

def setup_logger(name: str) -> logging.Logger:
    """로거 설정
    
    Args:
        name (str): 로거 이름
        
    Returns:
        logging.Logger: 설정된 로거 객체
    """
    # 로그 디렉토리 생성
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 이미 핸들러가 있다면 추가하지 않음
    if logger.handlers:
        return logger
        
    # 포맷터 생성
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 설정 (날짜 포함)
    current_date = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'trading_{current_date}.log')
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 