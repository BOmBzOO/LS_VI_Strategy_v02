# LS Trading Platform

VI(Volatility Interruption) 전략을 구현한 자동 매매 플랫폼입니다.

## 기능

- VI 발동/해제 모니터링
- 실시간 시세 처리
- 자동 매매 실행
- 포지션 관리
- 리스크 관리

## 설치 방법

1. Python 3.8 이상 설치
2. 의존성 패키지 설치:
```bash
pip install -r requirements.txt
```
3. `.env.example` 파일을 `.env`로 복사하고 필요한 설정 입력

## 실행 방법

```bash
python main.py
```

## 설정

- `config/settings.py`: 기본 설정
- `config/logging_config.py`: 로깅 설정
- `.env`: 환경변수 설정

## 디렉토리 구조

- `api/`: API 관련 모듈
- `core/`: 핵심 기능 모듈
- `data/`: 데이터 처리 모듈
- `services/`: 서비스 모듈
- `strategies/`: 매매 전략 모듈
- `logs/`: 로그 파일

## 라이선스

MIT License 