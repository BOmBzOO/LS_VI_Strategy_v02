# LS VI 전략 트레이딩 플랫폼

## 프로젝트 소개
이 프로젝트는 한국거래소(KRX)의 Volatility Indicator(VI) 기반 트레이딩 전략을 구현한 플랫폼입니다.

### 주요 기능
- VI 모니터링 및 알림
- 실시간 거래 데이터 수집
- VI 발동/해제 시 자동 거래 실행
- 시장 데이터 분석 및 전략 구현

## 시스템 요구사항
- Python 3.8 이상
- Windows 10/11 또는 Linux/Unix 환경
- 한국투자증권 API 접근 권한

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
1. `config/config.yaml` 파일에서 API 설정을 구성합니다.
2. 필요한 경우 로깅 설정을 `config/logging_config.py`에서 수정합니다.

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
├── config/                 # 설정 파일
├── services/              # 서비스 모듈
├── strategy/              # 전략 구현
├── utils/                 # 유틸리티 함수
├── main_vi.py            # VI 전략 실행
└── main_vi_ccld.py       # VI + CCLD 전략 실행
```

## 로깅
- 로그 파일은 `logs/` 디렉토리에 저장됩니다.
- 기본 로그 레벨: INFO
- 로그 포맷: 시간, 레벨, 모듈, 메시지

## 라이선스
이 프로젝트는 MIT 라이선스를 따릅니다.

## 기여 방법
1. Fork the Project
2. Create your Feature Branch
3. Commit your Changes
4. Push to the Branch
5. Open a Pull Request 