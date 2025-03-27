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
        logging.Logger: 설정된 로거
    """
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 이미 핸들러가 있다면 추가하지 않음
    if logger.handlers:
        return logger
        
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 설정 (colorama 사용하지 않음)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # 파일 핸들러 설정
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, f"{name}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger 