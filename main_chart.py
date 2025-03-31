"""차트 조회 메인 스크립트"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import argparse
from services.service_chart import ChartService
import asyncio

def create_parser() -> argparse.ArgumentParser:
    """명령행 인자 파서 생성
    
    Returns:
        argparse.ArgumentParser: 인자 파서
    """
    parser = argparse.ArgumentParser(description="주식 차트 조회 스크립트")
    
    # 필수 인자
    parser.add_argument("--stock-code", required=True, help="종목코드 (예: 078020)")
    parser.add_argument("--chart-type", required=True, choices=["minute", "tick"], help="차트 타입 (minute: 분봉, tick: 틱)")
    
    # 선택 인자
    parser.add_argument("--unit", type=int, default=1, help="N분/N틱 단위 (기본값: 1)")
    parser.add_argument("--count", type=int, default=100, help="요청 건수 (기본값: 100)")
    parser.add_argument("--end-date", default="99999999", help="종료일자 (YYYYMMDD, 기본값: 99999999)")
    parser.add_argument("--start-date", default="", help="시작일자 (YYYYMMDD, 기본값: '')")
    parser.add_argument("--compressed", action="store_true", help="압축 여부")
    parser.add_argument("--continuous", action="store_true", help="연속 조회 여부")
    parser.add_argument("--cts-date", default="", help="연속 일자")
    parser.add_argument("--cts-time", default="", help="연속 시간")
    parser.add_argument("--no-print", action="store_true", help="결과 출력 안 함")
    parser.add_argument("--no-plot", action="store_true", help="차트 플로팅 안 함")
    
    return parser

async def test_minute_chart(chart_service: ChartService) -> None:
    """분봉 차트 테스트
    
    Args:
        chart_service (ChartService): 차트 서비스 인스턴스
    """
    # 테스트 케이스 정의
    test_cases = [
        {
            "name": "1분봉 테스트",
            "params": {
                "stock_code": "078020",  # 이글벳
                "minute_unit": 1,
                "request_count": 100,
                "end_date": datetime.now().strftime("%Y%m%d"),  # 오늘 날짜
                "start_date": "",
                "is_compressed": False,  # 압축 해제
                "is_continuous": False,
                "cts_date": "",
                "cts_time": "",
                "print_output": True,
                "plot_chart": True
            }
        },
        {
            "name": "3분봉 테스트",
            "params": {
                "stock_code": "005930",  # 삼성전자
                "minute_unit": 3,
                "request_count": 100,  # 요청 건수 줄임
                "end_date": datetime.now().strftime("%Y%m%d"),  # 오늘 날짜
                "start_date": "",
                "is_compressed": False,  # 압축 해제
                "is_continuous": False,
                "cts_date": "",
                "cts_time": "",
                "print_output": True,
                "plot_chart": True
            }
        },
        {
            "name": "5분봉 테스트",
            "params": {
                "stock_code": "035720",  # 카카오
                "minute_unit": 5,
                "request_count": 100,  # 요청 건수 줄임
                "end_date": datetime.now().strftime("%Y%m%d"),  # 오늘 날짜
                "start_date": "",
                "is_compressed": False,  # 압축 해제
                "is_continuous": False,
                "cts_date": "",
                "cts_time": "",
                "print_output": True,
                "plot_chart": True
            }
        }
    ]
    
    # 테스트 실행
    for test_case in test_cases:
        try:
            print(f"\n=== {test_case['name']} 시작 ===")
            print(f"종목코드: {test_case['params']['stock_code']}")
            print(f"분봉단위: {test_case['params']['minute_unit']}")
            print(f"요청건수: {test_case['params']['request_count']}")
            print(f"종료일자: {test_case['params']['end_date']}")
            print(f"압축여부: {test_case['params']['is_compressed']}")
            
            # 차트 조회
            chart_data = chart_service.get_minute_chart(**test_case['params'])
            
            # 결과 확인
            if chart_data and not "error_code" in chart_data:
                print("테스트 성공")
                print(f"데이터 건수: {len(chart_data) if isinstance(chart_data, list) else 0}")
                
                # 데이터 유효성 검사
                if isinstance(chart_data, list) and len(chart_data) > 0:
                    first_data = chart_data[0]
                    print("\n첫 번째 데이터 샘플:")
                    print(f"시간: {first_data.get('time', 'N/A')}")
                    print(f"시가: {first_data.get('open', 'N/A')}")
                    print(f"고가: {first_data.get('high', 'N/A')}")
                    print(f"저가: {first_data.get('low', 'N/A')}")
                    print(f"종가: {first_data.get('close', 'N/A')}")
                    print(f"거래량: {first_data.get('volume', 'N/A')}")
            else:
                error_msg = chart_data.get('error_message', '알 수 없는 오류')
                print(f"테스트 실패: {error_msg}")
                if "rsp_cd" in error_msg:
                    print("응답 코드 확인 필요: 데이터 형식이나 요청 파라미터를 확인하세요.")
                    if "IGW40014" in error_msg:
                        print("데이터 형식 오류: 숫자가 아닌 문자가 포함되어 있습니다.")
                
            print(f"=== {test_case['name']} 종료 ===\n")
            
            # 테스트 간 딜레이
            await asyncio.sleep(2)  # 딜레이 증가
            
        except Exception as e:
            print(f"테스트 중 오류 발생: {str(e)}")
            print("스택 트레이스:")
            import traceback
            print(traceback.format_exc())
            
        finally:
            # 테스트 케이스 종료 후 정리
            await asyncio.sleep(1)

async def test_tick_chart(chart_service: ChartService) -> None:
    """틱 차트 테스트
    
    Args:
        chart_service (ChartService): 차트 서비스 인스턴스
    """
    # 테스트 케이스 정의
    test_cases = [
        {
            "name": "1틱 테스트",
            "params": {
                "stock_code": "078020",  # 이글벳
                "tick_unit": 1,
                "request_count": 100,
                "end_date": datetime.now().strftime("%Y%m%d"),  # 오늘 날짜
                "start_date": "",
                "is_compressed": False,
                "is_continuous": False,
                "cts_date": "",
                "cts_time": "",
                "print_output": True,
                "plot_chart": True
            }
        },
        {
            "name": "3틱 테스트",
            "params": {
                "stock_code": "005930",  # 삼성전자
                "tick_unit": 3,
                "request_count": 100,  # 요청 건수 줄임
                "end_date": datetime.now().strftime("%Y%m%d"),  # 오늘 날짜
                "start_date": "",
                "is_compressed": False,  # 압축 해제
                "is_continuous": False,
                "cts_date": "",
                "cts_time": "",
                "print_output": True,
                "plot_chart": True
            }
        },
        {
            "name": "5틱 테스트",
            "params": {
                "stock_code": "035720",  # 카카오
                "tick_unit": 5,
                "request_count": 100,  # 요청 건수 줄임
                "end_date": datetime.now().strftime("%Y%m%d"),  # 오늘 날짜
                "start_date": "",
                "is_compressed": False,  # 압축 해제
                "is_continuous": False,
                "cts_date": "",
                "cts_time": "",
                "print_output": True,
                "plot_chart": True
            }
        }
    ]
    
    # 테스트 실행
    for test_case in test_cases:
        try:
            print(f"\n=== {test_case['name']} 시작 ===")
            print(f"종목코드: {test_case['params']['stock_code']}")
            print(f"틱단위: {test_case['params']['tick_unit']}")
            print(f"요청건수: {test_case['params']['request_count']}")
            print(f"종료일자: {test_case['params']['end_date']}")
            print(f"압축여부: {test_case['params']['is_compressed']}")
            
            # 차트 조회
            chart_data = chart_service.get_tick_chart(**test_case['params'])
            
            # 결과 확인
            if chart_data and not "error_code" in chart_data:
                print("테스트 성공")
                print(f"데이터 건수: {len(chart_data) if isinstance(chart_data, list) else 0}")
            else:
                error_msg = chart_data.get('error_message', '알 수 없는 오류')
                print(f"테스트 실패: {error_msg}")
                if "rsp_cd" in error_msg:
                    print("응답 코드 확인 필요: 데이터 형식이나 요청 파라미터를 확인하세요.")
                
            print(f"=== {test_case['name']} 종료 ===\n")
            
            # 테스트 간 딜레이
            await asyncio.sleep(2)  # 딜레이 증가
            
        except Exception as e:
            print(f"테스트 중 오류 발생: {str(e)}")
            print("스택 트레이스:")
            import traceback
            print(traceback.format_exc())
            
        finally:
            # 테스트 케이스 종료 후 정리
            await asyncio.sleep(1)

async def main():
    """메인 함수"""
    try:
        # 차트 서비스 생성
        chart_service = ChartService()
        
        # 분봉 테스트
        print("\n=== 분봉 차트 테스트 시작 ===")
        await test_minute_chart(chart_service)
        
        # 틱 테스트
        print("\n=== 틱 차트 테스트 시작 ===")
        await test_tick_chart(chart_service)
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        
if __name__ == "__main__":
    asyncio.run(main()) 