# 오일장 폼 자동 채우기

jejuall.com (오일장) 사이트의 폼을 자동으로 채워주는 도구

## 실행

```bash
python -m src.features.oiljang_form_filler
```

## 기능

- 크롬 브라우저 자동 실행 (또는 기존 크롬에 연결)
- 폼 필드 자동 채우기 (텍스트, 셀렉트)
- 프리셋 저장/불러오기
- 여러 필드 일괄 전송

## 구조

```
oiljang_form_filler/
├── __init__.py
├── __main__.py          # 엔트리포인트 (의존성 조립)
├── README.md
├── data/
│   └── oiljang_presets.json  # 프리셋 저장 파일
├── domain/              # 도메인 레이어
│   ├── models.py        # FormPreset 데이터 클래스
│   └── value_objects.py # LocatorType, FieldMode Enum
├── app/                 # 애플리케이션 레이어
│   ├── fill_field_use_case.py
│   ├── save_presets_use_case.py
│   ├── load_presets_use_case.py
│   └── send_all_use_case.py
├── api/                 # API 레이어
│   └── gui/
│       ├── main_window.py   # 메인 윈도우
│       └── row_widget.py    # 입력 행 위젯
└── infra/               # 인프라 레이어
    ├── form_filler.py       # 폼 채우기 구현
    └── preset_repository.py # 프리셋 저장/로드
```

## 의존성

- `src/shared/browser/chrome_controller.py`: 크롬 브라우저 제어
- `src/shared/logging/app_logger.py`: 로깅

## 설정

### 크롬 디버깅 포트

기본값: `127.0.0.1:2578`

### 크롬 프로필 경로

`C:/Users/{사용자}/AppData/Local/RHelper/chrome-profile/`

모든 feature가 이 프로필을 공유함 (캐시, 로그인 정보 유지)

### 크롬 실행 경로

기본값: `C:/Program Files/Google/Chrome/Application/chrome.exe`

환경변수 `CHROME_PATH`로 오버라이드 가능

## 프리셋 파일 형식

`data/oiljang_presets.json`:

```json
[
  {
    "item": "전용면적",
    "locator_type": "id",
    "locator_value": "floor",
    "mode": "select"
  },
  {
    "item": "가격",
    "locator_type": "name",
    "locator_value": "price",
    "mode": "normal"
  }
]
```

## 변경 이력

- 2024-12: ex.py에서 버티컬 슬라이스 구조로 리팩토링
