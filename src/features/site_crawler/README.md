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
from src.features.site_crawler.api.gui.site_crawler_widget import SiteCrawlerWidget

# 다른 윈도우에 임베딩
widget = SiteCrawlerWidget(parent=some_parent)
layout.addWidget(widget)
```

---

## 설계 결정 (Design Decisions)

### 1. 이벤트 시스템 (Event System) - 2025-11-24 리팩토링
레이어 간 통신을 이벤트 발행/구독 패턴으로 구현한다.
- **이벤트 버스** (`app/event_bus.py`): 중앙 이벤트 관리
- **도메인 이벤트** (`domain/events.py`):
  - `StatusEvent`: 상태 메시지
  - `AddressesFoundEvent`: 주소 검색 결과
  - `BuildingsFoundEvent`: 건물 목록
  - `CrawlingCompleteEvent`: 크롤링 완료
  - `ErrorEvent`: 에러 발생
- **구독 관리**: `__main__.py`에서 중앙 관리
- GUI와 비즈니스 로직이 완전히 분리되어 테스트 용이

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

## 폴더 구조 (레이어 기반 아키텍처)
```
src/features/site_crawler/
├── __main__.py                  # 독립 실행 엔트리 포인트 (DI 컨테이너)
├── README.md                    # 이 문서
├── TESTING.md                   # 테스트 체크리스트
│
├── domain/                      # 도메인 레이어 (비즈니스 규칙)
│   ├── __init__.py
│   ├── models.py               # Address, Building, CrawlItem 엔티티
│   └── events.py               # 도메인 이벤트 정의
│
├── app/                         # 애플리케이션 레이어 (유즈케이스)
│   ├── __init__.py
│   ├── event_bus.py            # 이벤트 발행/구독 시스템
│   ├── search_address_use_case.py      # 주소 검색 유즈케이스
│   ├── select_building_use_case.py     # 건물 선택 유즈케이스
│   ├── crawl_detail_use_case.py        # 상세 크롤링 유즈케이스
│   ├── save_preset_use_case.py         # 프리셋 저장 유즈케이스
│   ├── load_preset_use_case.py         # 프리셋 로드 유즈케이스
│   └── save_result_use_case.py         # 결과 저장 유즈케이스
│
├── api/                         # API 레이어 (외부 인터페이스)
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py      # QMainWindow (메뉴바 포함)
│       ├── site_crawler_widget.py  # QWidget (핵심 UI 로직)
│       └── crawling_item_result_row.py  # CrawlingItemResultRow (크롤링 결과 행 위젯)
│
├── infra/                       # 인프라 레이어 (기술 구현체)
│   ├── __init__.py
│   ├── i_crawler.py            # 크롤러 인터페이스 (Protocol)
│   ├── selenium_crawler.py     # Selenium 기반 크롤러 구현
│   ├── chrome_driver_manager.py # ChromeDriver 자동 다운로드/관리
│   ├── settings_repository.py   # 설정 파일 저장소
│   ├── preset_repository.py     # 프리셋 파일 저장소
│   └── result_repository.py     # 결과 파일 저장소
│
├── data/                        # 데이터 파일 (설정, 프리셋, 결과)
│   ├── settings.json           # 헤드리스 모드 등 설정
│   ├── profiles/
│   │   └── crawler-profile/    # Chrome 유저 데이터
│   ├── presets/
│   │   └── crawl_presets.json  # 프리셋 저장
│   └── results/
│       └── latest_crawl.json   # 최근 크롤링 결과
│
├── drivers/                     # ChromeDriver 다운로드 위치
└── _deprecated/                 # 리팩토링 전 코드 (수동 삭제 예정)
    ├── core/                   # 구 크롤링 로직
    ├── gui/                    # 구 GUI 코드
    └── README.md               # 삭제 안내
```

---

## 개발 원칙
- **레이어 아키텍처**: domain → app → api/infra 의존성 방향 엄격히 준수
- **DI (의존성 주입)**: 모든 의존성은 `__main__.py`에서 주입
- **순수 함수 우선**: 비즈니스 로직은 가능한 한 부수효과 없는 함수로 작성
- **타입 힌트 필수**: 모든 공개 함수/메서드는 타입 힌트 명시
- **이름 규칙**: `동사_대상_세부` 패턴 (예: `search_address_use_case.py`)
- **상태 없는 설계**: 크롤러는 인스턴스 변수 대신 지역 변수 사용
- **이벤트 기반 통신**: 레이어 간 직접 호출 대신 이벤트 발행/구독

---

## 변경 이력

### 2025-12-08: 코드 리뷰 기반 품질 개선
- **중복 파일 삭제**: 루트의 `chrome_driver_manager.py` 삭제 (infra/ 버전만 유지)
- **로깅 일관성**: `print()` → `LOGGER.warning()` 변경
  - event_bus.py, settings_repository.py, preset_repository.py
- **인덱스 경계 검증 추가**: site_crawler_widget.py (규칙23 준수)
  - `_handle_address_selection()`, `_handle_building_selection()`에 범위 체크 추가
- **sleep 주석 추가**: selenium_crawler.py
  - 동적 대기만으로 데이터 바인딩 완료를 보장할 수 없어 sleep 유지 (이유 명시)
- **헤더 주석 표준화**: 17개 파일 전체
  - 규칙13 형식 적용 (레이어, 역할, 의존, 외부, 목적)
- **Chrome 로그 최소화**: chrome_driver_manager.py
  - `enable-logging` 비활성화 + `--log-level=3` 설정 (치명적 에러만 출력)
- 수정 파일: 17개 전체

### 2025-11-27: 건물 선택 UX 개선 및 버그 수정
- **건물 1개 자동 크롤링**: 건물이 1개뿐일 때 자동 선택 + 자동 크롤링 실행
- **첫 크롤링 UI 미표시 버그 수정**: QComboBox 시그널 블로킹으로 이벤트 루프 차단 문제 해결
- **동적 대기 적용**: `time.sleep(2)` 제거 → `WebDriverWait` (5초 타임아웃) 사용
- **여러 건물 선택 UX**: placeholder("건물 선택") + 드롭다운 자동 펼침(`showPopup()`)
- 수정 파일: `site_crawler_widget.py`, `selenium_crawler.py`

### 2025-11-26: widgets.py 리팩토링
- `widgets.py` → `crawling_item_result_row.py` 파일명 변경
- `CrawlingRowWidget` → `CrawlingItemResultRow` 클래스명 변경
- 이유: 모듈명이 역할을 명확히 드러내도록 개선 (이름 규칙 준수)

### 2025-11-26: `__init__.py` re-export 제거
- `domain/__init__.py`, `app/__init__.py`, `infra/__init__.py`, `api/gui/__init__.py` 비움
- 이유: Import 규칙 강화 - `__init__.py`에서 re-export 금지
- 모든 import는 파일(모듈) 레벨까지 풀경로로 작성
- 예: `from src.features.site_crawler.app.event_bus import EventBus`
