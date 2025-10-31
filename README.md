# 증여세 신고서 작성 프로그램 (프로토타입)

> Flask 기반의 최소 실행 뼈대입니다. 법령 테이블을 직접 채워 넣어야 실제 세액 계산이 가능합니다.

## ⚠️ 중요 고지

**1) 이 리포는 학습/프로토타입용입니다. 실제 신고 전 반드시 최신 법령 검증이 필요합니다.**  
**2) `gift_tax/law_tables/kor_2025.yaml`을 최신 법령에 맞게 유지해야 세액 계산이 가능합니다.**
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

## 법규 테이블 업데이트 방법

- [`gift_tax/law_tables/kor_2025.yaml`](gift_tax/law_tables/kor_2025.yaml) 파일에 2025년 1월 1일 기준 공제·세율 정보가 기본 제공됩니다.
- 새로운 법령이 공포되면 `metadata.version`, `metadata.reference`를 최신 근거로 수정하고, `basic_deduction` 및 `progressive_rates` 값을 최신 수치로 교체해 주세요.
- YAML 구조는 거주자 구분(resident/non_resident)과 관계별 기본공제, 과세표준 구간별 세율 및 누진공제로 구성되어 있습니다.
- 파일을 업데이트한 뒤 서버를 재시작하면 변경 사항이 즉시 반영됩니다.

## 계산 로직 개요

- `gift_tax/calculator.py`의 `GiftInput` 모델이 폼 입력값을 구조화합니다.
- `load_law_table` 함수가 법령 테이블을 읽고 구성 여부를 확인합니다.
- `compute_tax` 함수는 순증여재산에서 기본공제를 차감하고, 10년 내 증여분을 반영한 후 누진세율·누진공제를 적용해 산출세액을 계산합니다.
- 계산 과정과 적용 세율은 `GiftBreakdown.notes`에 기록되어 결과 화면에서 확인할 수 있습니다.

## 근거와 기준일

- `gift_tax/law_tables/kor_2025.yaml`의 기본공제 및 세율은 **상속세및증여세법 제53조·제55조, 시행령 제53조 (2024.1.1 시행)**을 기준으로 작성되었습니다.
- 국세청 증여세 안내(2024년 1월 1일 기준) 문서를 참고하여 공제액과 누진공제를 검증했습니다.
- 법령 개정 시 반드시 해당 YAML 파일과 README를 함께 업데이트해 주십시오.

## 주의 사항

- 본 프로그램은 학습용 프로토타입으로 제공되며, 계산 로직의 정확성 검증 책임은 사용자에게 있습니다.
- 실제 신고 전에 최신 법령 반영 여부와 입력값을 반드시 세무 전문가와 함께 검토하십시오.
