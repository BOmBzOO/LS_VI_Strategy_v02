"""계좌 잔고 조회 메인 스크립트"""

from services.service_account import AccountService

def main():
    """메인 함수"""
    try:
        # 계좌 서비스 생성 (법인 계정인 경우 is_corporate=True로 설정)
        account_service = AccountService(is_corporate=False)  # 개인 계정
        # account_service = AccountService(is_corporate=True)   # 법인 계정
        
        # 계좌 요약 정보 조회
        account_service.get_account_balance()
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        
if __name__ == "__main__":
    main() 