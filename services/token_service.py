"""토큰 관리 서비스

토큰 발급, 갱신, 유효성 검사 등 토큰 관리를 위한 서비스 클래스를 제공합니다.
"""

import os
import requests
from typing import Dict, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key, find_dotenv
from config.logging_config import setup_logger
from config.settings import LS_BASE_URL, TOKEN_REFRESH_MARGIN

class TokenService:
    """토큰 관리 서비스 클래스"""

    def __init__(self):
        """초기화"""
        self.logger = setup_logger(__name__)
        load_dotenv()

    def check_token_validity(self) -> bool:
        """토큰 유효성 검사

        Returns:
            bool: 토큰이 유효한지 여부
        """
        token = os.getenv('LS_ACCESS_TOKEN')
        expires_at = os.getenv('LS_TOKEN_EXPIRES_AT')
        
        if not token or not expires_at:
            return False
        
        try:
            # 만료 시간 파싱
            expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            current_dt = datetime.now()
            
            # 만료 시간 여유를 두고 체크
            margin = timedelta(seconds=TOKEN_REFRESH_MARGIN)
            return current_dt < (expires_dt - margin)
        except Exception as e:
            self.logger.error(f"토큰 유효성 검사 중 오류 발생: {str(e)}")
            return False

    def save_token_to_env(self, token: str, expires_at: str) -> None:
        """토큰을 .env 파일에 저장

        Args:
            token (str): 액세스 토큰
            expires_at (str): 만료 시간 (YYYY-MM-DD HH:MM:SS 형식)
        """
        try:
            env_path = find_dotenv()
            if not env_path:
                env_path = '.env'
                
            # .env 파일에 토큰 정보 저장
            set_key(env_path, 'LS_ACCESS_TOKEN', token)
            set_key(env_path, 'LS_TOKEN_EXPIRES_AT', expires_at)
            
            # 환경변수 업데이트
            os.environ['LS_ACCESS_TOKEN'] = token
            os.environ['LS_TOKEN_EXPIRES_AT'] = expires_at
            
            self.logger.info("토큰이 .env 파일에 저장되었습니다.")
        except Exception as e:
            self.logger.error(f"토큰 저장 중 오류 발생: {str(e)}")

    def get_new_token(self) -> Tuple[bool, str]:
        """새로운 토큰 발급

        Returns:
            Tuple[bool, str]: (성공 여부, 오류 메시지)
        """
        try:
            app_key = os.getenv('LS_APP_KEY')
            secret_key = os.getenv('LS_SECRET_KEY')
            
            if not app_key or not secret_key:
                return False, "API 키가 설정되지 않았습니다."
            
            # 토큰 발급 요청
            url = f"{LS_BASE_URL}/oauth2/token"
            headers = {
                "content-type": "application/x-www-form-urlencoded"
            }
            data = {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "appsecretkey": secret_key,
                "scope": "oob"
            }
            
            response = requests.post(url, headers=headers, data=data)
            if response.status_code != 200:
                return False, f"토큰 발급 실패: {response.text}"
            
            result = response.json()
            
            # 토큰 정보 저장
            access_token = result.get('access_token')
            expires_in = int(result.get('expires_in', 86400))  # 기본값 24시간
            
            if not access_token:
                return False, "토큰 정보가 없습니다."
            
            # 만료 시간 계산
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
            
            # 토큰 저장
            self.save_token_to_env(access_token, expires_at_str)
            
            self.logger.info("새로운 토큰이 발급되었습니다.")
            return True, ""
            
        except Exception as e:
            return False, f"토큰 발급 중 오류 발생: {str(e)}"

    def check_and_refresh_token(self) -> bool:
        """토큰 체크 및 갱신

        Returns:
            bool: 토큰이 유효한지 여부
        """
        if self.check_token_validity():
            self.logger.info("토큰이 유효합니다.")
            return True
        
        self.logger.info("토큰이 만료되었거나 없습니다. 새로운 토큰을 발급합니다.")
        success, error = self.get_new_token()
        
        if not success:
            self.logger.error(f"토큰 갱신 실패: {error}")
            return False
            
        return True

    def get_token_info(self) -> Dict[str, str]:
        """현재 토큰 정보 조회

        Returns:
            Dict[str, str]: 토큰 정보
        """
        return {
            "access_token": os.getenv('LS_ACCESS_TOKEN', ''),
            "expires_at": os.getenv('LS_TOKEN_EXPIRES_AT', ''),
            "is_valid": self.check_token_validity()
        }

    def get_token(self) -> str:
        """현재 토큰 조회

        Returns:
            str: 액세스 토큰
        """
        return os.getenv('LS_ACCESS_TOKEN', '') 