"""인증 관련 유틸리티

API 인증 및 토큰 관리를 위한 유틸리티 함수들을 제공합니다.
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
from config.logging_config import setup_logger

logger = setup_logger(__name__)

def load_credentials() -> Dict[str, str]:
    """환경 변수에서 인증 정보 로드

    Returns:
        Dict[str, str]: 인증 정보
    """
    required_keys = ['API_KEY', 'API_SECRET', 'ACCOUNT_NUMBER']
    credentials = {}

    for key in required_keys:
        value = os.getenv(key)
        if not value:
            logger.error(f"필수 환경 변수가 없습니다: {key}")
            raise ValueError(f"필수 환경 변수가 없습니다: {key}")
        credentials[key] = value

    return credentials

def save_token(token: str, expires_in: int) -> None:
    """토큰 저장

    Args:
        token (str): 액세스 토큰
        expires_in (int): 만료 시간 (초)
    """
    token_info = {
        "token": token,
        "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat()
    }

    try:
        with open("token.json", "w") as f:
            json.dump(token_info, f)
        logger.debug("토큰 저장 완료")
    except Exception as e:
        logger.error(f"토큰 저장 중 오류 발생: {str(e)}")

def load_token() -> Optional[str]:
    """저장된 토큰 로드

    Returns:
        Optional[str]: 유효한 토큰 또는 None
    """
    try:
        if not os.path.exists("token.json"):
            return None

        with open("token.json", "r") as f:
            token_info = json.load(f)

        expires_at = datetime.fromisoformat(token_info["expires_at"])
        if datetime.now() >= expires_at:
            logger.debug("토큰이 만료되었습니다.")
            return None

        return token_info["token"]
    except Exception as e:
        logger.error(f"토큰 로드 중 오류 발생: {str(e)}")
        return None

def is_token_valid(token: str) -> bool:
    """토큰 유효성 검사

    Args:
        token (str): 검사할 토큰

    Returns:
        bool: 토큰 유효 여부
    """
    try:
        if not os.path.exists("token.json"):
            return False

        with open("token.json", "r") as f:
            token_info = json.load(f)

        if token_info["token"] != token:
            return False

        expires_at = datetime.fromisoformat(token_info["expires_at"])
        return datetime.now() < expires_at
    except Exception as e:
        logger.error(f"토큰 유효성 검사 중 오류 발생: {str(e)}")
        return False

def clear_token() -> None:
    """토큰 삭제"""
    try:
        if os.path.exists("token.json"):
            os.remove("token.json")
            logger.debug("토큰 삭제 완료")
    except Exception as e:
        logger.error(f"토큰 삭제 중 오류 발생: {str(e)}")

def get_headers(token: Optional[str] = None) -> Dict[str, str]:
    """API 요청 헤더 생성

    Args:
        token (Optional[str]): 액세스 토큰

    Returns:
        Dict[str, str]: API 요청 헤더
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "LS-Trading-Platform/1.0"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers 