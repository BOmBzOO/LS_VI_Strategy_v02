"""기본 API 클래스"""

from typing import Dict, Any, Optional
import requests
import json
from datetime import datetime
import uuid
import os
from config.logging_config import setup_logger
from config.settings import LS_BASE_URL, LS_APP_ACCESS_TOKEN, LS_MAC_ADDRESS
from api.constants import URLPath

class BaseAPI:
    """기본 API 클래스"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.base_url = LS_BASE_URL
        self.access_token = LS_APP_ACCESS_TOKEN
        self.mac_address = LS_MAC_ADDRESS
        
    def request_tr(
        self,
        tr_code: str,
        input_data: Dict[str, Any],
        tr_type: int = 2,  # 기본값 2 (조회성 TR)
        is_continuous: bool = False,
        tr_cont_key: str = ""
    ) -> Dict[str, Any]:
        """TR 요청

        Args:
            tr_code (str): TR 코드
            input_data (Dict[str, Any]): 입력 데이터
            tr_type (int, optional): TR 타입 (1: 일반, 2: 조회, 3: 실시간). Defaults to 2.
            is_continuous (bool, optional): 연속 조회 여부. Defaults to False.
            tr_cont_key (str, optional): 연속 조회 키. Defaults to "".

        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        try:
            # URL 설정
            url = self.get_tr_url(tr_code)
            
            # 헤더 설정
            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {os.getenv('LS_ACCESS_TOKEN')}",
                "tr_cd": tr_code,
                "tr_cont": "Y" if is_continuous else "N",
                "tr_cont_key": tr_cont_key,
                "mac_address": os.getenv('LS_MAC_ADDRESS', '')
            }
            
            # 요청
            response = requests.post(url, headers=headers, json=input_data)
            
            # 응답 확인
            if response.status_code != 200:
                self.logger.error(f"TR 요청 실패: {response.text}")
                return {
                    "rsp_cd": str(response.status_code),
                    "rsp_msg": response.text
                }
            
            # 응답 데이터 반환
            result = response.json()
            return result
            
        except Exception as e:
            self.logger.error(f"TR 요청 중 오류 발생: {str(e)}")
            return {
                "rsp_cd": "99999",
                "rsp_msg": str(e)
            }

    def get_tr_url(self, tr_code: str) -> str:
        # This method should be implemented to return the correct URL based on the tr_code
        # For now, we'll use the existing base_url
        return f"{self.base_url}{URLPath.TR_URLS.get(tr_code, URLPath.STOCK_ETC)}" 