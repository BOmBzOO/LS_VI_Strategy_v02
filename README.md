# LS증권 트레이딩 플랫폼

## 프로젝트 소개
이 프로젝트는 한국거래소(KRX)의 Volatility Indicator(VI) 기반 트레이딩 전략을 구현한 플랫폼입니다. VI 발동/해제 시점을 실시간으로 모니터링하고, 이를 기반으로 자동 매매 전략을 실행합니다.

### 주요 기능
- **VI 모니터링**
  - 실시간 VI 발동/해제 감지
  - VI 발동 시 자동 알림
  - VI 상태 실시간 추적

- **거래 데이터 수집**
  - 실시간 시세 데이터 수집
  - 거래량 데이터 분석
  - 시장 상태 모니터링

- **자동 매매 실행**
  - VI 발동/해제 기반 매매 신호 생성
  - 자동 주문 실행
  - 포지션 관리

- **리스크 관리**
  - 손절/익절 자동화
  - 포지션 리밸런싱
  - 리스크 한도 설정

## 시스템 요구사항
- Python 3.8 이상
- Windows 10/11 또는 Linux/Unix 환경
- 한국투자증권 API 접근 권한
- 최소 8GB RAM
- 안정적인 인터넷 연결

## 설치 방법
1. 저장소 클론
```bash
git clone [repository-url]
cd LS_VIstrategy_v01_2025_03_28
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Unix
venv\Scripts\activate     # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

## 설정
1. API 설정
   - `config/config.yaml` 파일에서 API 설정을 구성합니다.
   - API 키와 시크릿을 설정합니다.
   - 필요한 경우 프록시 설정을 추가합니다.

2. 로깅 설정
   - `config/logging_config.py`에서 로깅 레벨과 포맷을 설정합니다.
   - 로그 파일은 `logs/` 디렉토리에 저장됩니다.

3. 전략 설정
   - `strategy/` 디렉토리에서 매매 전략을 설정합니다.
   - VI 발동/해제 조건을 조정합니다.
   - 매매 규칙을 설정합니다.

## 실행 방법
1. VI 모니터링 전략 실행
```bash
python main_vi.py
```

2. VI + CCLD 모니터링 전략 실행
```bash
python main_vi_ccld.py
```

## 프로젝트 구조
```
LS_VIstrategy_v01_2025_03_28/
├── api/                    # API 관련 모듈
│   ├── constants.py       # 상수 정의
│   ├── realtime/         # 실시간 데이터 처리
│   └── rest/             # REST API 처리
├── config/                # 설정 파일
│   ├── config.yaml       # 기본 설정
│   └── logging_config.py # 로깅 설정
├── services/             # 서비스 모듈
│   ├── auth_token_service.py
│   ├── market_data_service.py
│   ├── vi_monitor_service.py
│   └── vi_ccld_monitor_service.py
├── strategy/             # 전략 구현
│   ├── base_strategy.py
│   └── VI_strategy.py
├── utils/                # 유틸리티 함수
├── logs/                 # 로그 파일
├── main_vi.py           # VI 전략 실행
└── main_vi_ccld.py      # VI + CCLD 전략 실행
```

## 로깅
- 로그 파일은 `logs/trading_YYYYMMDD.log` 형식으로 저장됩니다.
- 기본 로그 레벨: INFO
- 로그 포맷: 시간, 로거 이름, 레벨, 메시지
- 로그 로테이션: 10MB 단위로 자동 분할

## 오류 처리
- API 연결 오류 자동 재시도
- VI 모니터링 연결 끊김 감지 및 복구
- 예외 상황 로깅 및 알림

## 성능 모니터링
- VI 발동/해제 통계
- 거래 실행 시간 측정
- 메모리 사용량 모니터링
- API 응답 시간 추적

## 라이선스
이 프로젝트는 MIT 라이선스를 따릅니다.

## 주의사항
- 실제 거래에 사용하기 전에 충분한 테스트가 필요합니다.
- API 사용량 제한을 고려하여 운영해야 합니다.
- 시장 상황에 따라 전략을 적절히 조정해야 합니다. 