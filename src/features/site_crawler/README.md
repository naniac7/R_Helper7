# site_crawler

## 개요
범용 부동산 사이트 크롤링 feature.
disco.re 같은 부동산 정보 사이트에서 주소 검색 → 건물 선택 → 상세 정보 수집 흐름을 자동화한다.

**버티컬 슬라이스 설계 원칙**에 따라 독립 실행 가능하며, 다른 feature와 의존성이 없다.

---

## 사용법

### 1. 독립 실행 (Standalone)
```bash
python -m src.features.site_crawler
```
- GUI 창이 열리고 메뉴바에서 헤드리스 모드 토글 가능
- 크롤링 결과는 `data/results/latest_crawl.json`에 자동 저장

### 2. 위젯 임베딩 (Embedded Widget)
```python
from src.features.site_crawler.gui.site_crawler_widget import SiteCrawlerWidget

# 다른 윈도우에 임베딩
widget = SiteCrawlerWidget(parent=some_parent)
layout.addWidget(widget)
```

---

## 설계 결정 (Design Decisions)

### 1. 콜백 패턴 (Callback Pattern)
크롤러(`core/site_crawler.py`)와 GUI를 완전히 분리한다.
- 크롤러는 생성자에서 콜백 함수들을 받는다:
  - `on_status`: 상태 메시지 전달 (GUI 콘솔 업데이트용)
  - `on_addresses_found`: 주소 검색 결과 전달
  - `on_buildings_found`: 건물 목록 전달
  - `on_complete`: 크롤링 완료 시 결과 전달
  - `on_error`: 에러 발생 시 전달

- GUI는 `self.console.append` 같은 메서드를 콜백으로 전달한다.
- 이로 인해 크롤러는 GUI 없이도 테스트 가능하다 (fake 콜백 주입).

### 2. JSON 통신 (Loose Coupling)
다른 feature(`chrome_form_filler` 등)와 직접 import로 연결하지 않는다.
대신 `data/results/latest_crawl.json` 파일을 통해 데이터를 공유한다.

**JSON 구조:**
```json
{
  "timestamp": "2025-11-23T15:30:00",
  "address": "서울시 강남구 테헤란로",
  "building": "강남빌딩",
  "items": [
    {"title": "전용면적", "content": "84.5㎡"},
    {"title": "층수", "content": "15층"}
  ]
}
```

### 3. 독립 ChromeDriver 관리
`chrome_driver_manager.py`가 **webdriver-manager** 라이브러리를 사용해
ChromeDriver를 자동으로 다운로드하고 `drivers/` 폴더에 저장한다.

- 다른 feature와 driver를 공유하지 않는다 (각자 독립 복사본).
- 시스템 PATH 설정 불필요.

### 4. 독립 콘솔 (Independent Console)
각 GUI는 자체 콘솔(`QPlainTextEdit`)을 가진다.
- 최근 50개 메시지만 유지 (메모리 제한).
- 크롤러의 `on_status` 콜백과 연결.

### 5. 헤드리스 모드 기본값: OFF
기본적으로 브라우저 창이 보이도록 설정한다.
- 메뉴바에서 토글 가능.
- 설정은 `data/settings.json`에 저장.

### 6. 프로필 관리
Chrome 유저 데이터는 `data/profiles/crawler-profile/`에 저장한다.
- 쿠키/세션 유지로 로그인 상태 지속.

---

## 폴더 구조
```
src/features/site_crawler/
├── __main__.py                  # 독립 실행 엔트리 포인트
├── README.md                    # 이 문서
├── chrome_driver_manager.py     # ChromeDriver 자동 다운로드/관리
├── gui/
│   ├── main_window.py          # QMainWindow (메뉴바 포함)
│   ├── site_crawler_widget.py  # QWidget (핵심 UI 로직)
│   └── widgets.py              # CrawlingRowWidget 등 재사용 위젯
├── core/
│   └── site_crawler.py         # 크롤링 로직 (콜백 기반)
├── data/
│   ├── settings.json           # 헤드리스 모드 등 설정
│   ├── profiles/
│   │   └── crawler-profile/    # Chrome 유저 데이터
│   ├── presets/
│   │   └── crawl_presets.json  # 프리셋 저장
│   └── results/
│       └── latest_crawl.json   # 최근 크롤링 결과
└── drivers/                     # ChromeDriver 다운로드 위치
```

---

## 개발 원칙
- **DI (의존성 주입)**: 크롤러는 외부 자원(driver, logger 등)을 생성자로 받는다.
- **순수 함수 우선**: 비즈니스 로직은 가능한 한 부수효과 없는 함수로 작성.
- **타입 힌트 필수**: 모든 공개 함수/메서드는 타입 힌트 명시.
- **이름 규칙**: `동사_대상_세부` 패턴 (예: `search_address`, `select_building`).
