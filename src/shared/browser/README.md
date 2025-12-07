# shared/browser

크롬 브라우저 자동 실행 및 연결 관리 모듈

## 파일 구조

| 파일 | 역할 |
|------|------|
| `chrome_controller.py` | 크롬 브라우저 자동 실행 및 연결 관리 |

## ChromeController

### 주요 기능
- 크롬이 실행 중이면 기존 크롬에 연결
- 실행 중이 아니면 자동으로 크롬 실행 후 연결
- 모든 feature가 동일한 프로필(캐시) 공유

### 사용법
```python
from src.shared.browser.chrome_controller import ChromeController

controller = ChromeController()
driver = controller.get_driver()
controller.focus_active_tab()
```

### 설계 결정

#### 2025-12-07: 포트 체크 최적화
- **문제**: 크롬이 없을 때 `webdriver.Chrome()` 연결 시도가 60초+ 타임아웃
- **해결**: `_is_port_open()` 메서드 추가, 소켓으로 1초 내 포트 체크
- **결과**: 크롬 없을 때 시작 시간 65초 → 1~2초로 단축
- **타임아웃 값**: 하드코딩 1.0초 (YAGNI 원칙, 한 군데서만 사용)
