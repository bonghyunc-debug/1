# 증여세 신고서 작성 프로그램 (프로토타입)

> Flask 기반의 최소 실행 뼈대입니다. 법령 테이블을 직접 채워 넣어야 실제 세액 계산이 가능합니다.

## ⚠️ 중요 고지

**1) 이 리포는 학습/프로토타입용입니다. 실제 신고 전 반드시 최신 법령 검증이 필요합니다.**  
**2) `gift_tax/law_tables/kor_2025.yaml`을 최신 법령에 맞게 채워야 세액 계산이 가능합니다.**  
**3) 테스트 및 배포에 대한 책임은 사용자에게 있습니다.**

## 요구 사항

- Python 3.12
- Flask, Pydantic, PyYAML, python-dateutil (see [`requirements.txt`](requirements.txt))

## 로컬 실행 방법

1. 가상환경을 생성하고 활성화합니다.
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. 필수 패키지를 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```
3. 개발 서버를 실행합니다.
   ```bash
   flask --app app run --debug
   ```
4. 브라우저에서 <http://127.0.0.1:5000>으로 접속하여 폼을 제출합니다.

## 법규 테이블 채우는 법

- [`gift_tax/law_tables/kor_2025.yaml`](gift_tax/law_tables/kor_2025.yaml) 파일은 현재 `PLACEHOLDER` 값으로 채워져 있습니다.
- 최신 증여세 공제액과 세율표를 확인한 후, 각 구간별 공제액(`basic_allowances`)과 누진세율(`progressive_rates`)을 실제 값으로 대체해야 합니다.
- 파일을 업데이트하면 서버 재시작 없이도 자동으로 반영되지만, 정확한 세액 계산 로직을 추가 구현해야 합니다.

## 계산 로직 골격

- `gift_tax/calculator.py`의 `GiftInput` 모델이 폼 입력값을 구조화합니다.
- `load_law_table` 함수가 법령 테이블을 읽고, `PLACEHOLDER`가 남아 있으면 `LawContext.configured`가 `False`가 됩니다.
- `compute_tax` 함수는 과세표준까지만 계산하며, 법규가 설정되지 않은 경우 세액(`tax_due`)은 `None`으로 둡니다.
- 추후 실제 세율표에 맞춘 세액 계산 로직을 추가할 수 있도록 `notes` 필드에 안내 메시지를 남깁니다.

## 주의 사항

- 본 프로그램은 공제액, 세율 계산 로직이 미구현된 학습용 예시입니다.
- 실제 신고에 사용하기 전 반드시 세무 전문가 검토와 테스트를 거치십시오.
