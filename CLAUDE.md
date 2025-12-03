# AI 협업 메모
* 설계 단계에서 중요한 내용은 관련 feature의 `README.md`에 한줄 이상 기록해 둔다. 
* AI는 해당 feature를 수정할때 해당 feature의 `README.md` 파일을 참조한다. 
* 큰 설계 변경이나 중요한 결정(예: 크롤링 방식 변경, 입찰 로직 변경 등)은  
  관련 feature의 `README.md`에 한 줄 이상 기록해둔다.
* 메모에는 "왜 이렇게 결정했는지"를 짧게 적어, 이후 AI가 같은 질문을 반복하지 않도록 한다.
* AI는 필요시 언제든지 `README.md`를 사용자의 승인 없이 생성 및 참조할 수 있다. 
* 전체적으로 큰 줄기의 수정내용 큰 줄기의 코드의 진행상황은 src/ 루트 폴더에 `README.md`에 기록한다. 
* `README.md`에 적은 내용을 반드시 해당 feature명과 함께 명시하고 사용자가 수정을 요청하면 `README.md`내용을 수정한다. 
* 코드가 수정되면 해당 해당 feature 폴더 안의 `README.md`를 항상 수정 업데이트 한다. 
* 코드 작성 완료 직후 해당 feature의 README.md를 업데이트한다.
(순서: 승인 → 코딩 및 README 업데이트)

# 불확실한 것에 대한 대답
- 모델이 답변의 정확도에 대해 확신이 없다고 판단될 때는, 내용을 지어내지 말고 ‘잘 모르겠다’고 답하거나, 불확실하다는 점을 명시한다.
- 모델이 내부적으로 산출한 답변 신뢰도가 설정된 임계값(threshold)보다 낮을 경우, 추측하거나 내용을 지어내지 않고 ‘잘 모르겠다’고 답한다. 단, 단순 대화나 창작·아이디어 브레인스토밍과 같이 사실성보다 상상력이 중요한 문맥에서는 이 규칙을 완화할 수 있다.
- 모르는 것에 모른다고 대답할 권리를 사용자가 AI에게 부여한다. 

# 코드 작성전에 지켜야 할 규칙
**중요**: **코드를 작성하거나 파일을 수정하기 전에 반드시 AI는 사용자의 "승인"이라는 명시적인 명령을 받은 후에만 코드를 수정할 수 있습니다**

## 워크플로우
작업은 다음과 같은 **순환적 프로세스**로 진행됩니다:
```
목적 제시(사용자→AI) → [목적 해석](AI→사용자) → 확정(사용자→AI) → 질문(AI→사용자) → 답변(사용자→AI) → ... → 승인(사용자→AI) → 코딩(AI)
```

### 0. 명령어 모음
- 사용자는 어떤 단계에서든지 다음 명령어를 사용할 수 있습니다
- **"해석"** 명령: "해석", "ㅎㅅ"
- **"질문"** 명령: "질문", "ㅈㅁ", "ㅈ"
- **"브리핑"** 명령: "브리핑", "ㅂㄹㅍ", "ㅂ"

### 1. 목적 제시
- 사용자가 원하는 바를 말합니다

### 2. 목적 해석 단계 (무조건 실행)
- 사용자가 목적을 제시하면 AI는 **무조건** 목적 해석을 수행합니다
- 단, 요청이 매우 명확한 경우(파일명+변경내용+기대결과 모두 명시)에는 해석 1개만 제시

#### 2.1. AI 행동
1. 관련 코드 분석 (의존성까지 추적, import 따라가기)
2. 사용자의 요청을 **최소 3개** 구체적 해석으로 변환 (필요시 더 추가)
3. 각 해석에 "현재 → 변경 → 결과" 포함

#### 2.2. 해석 출력 형식
```
🔍 **목적 해석**

**네 목적:**
[사용자가 뭘 원하는지 한 줄 요약]

**현재 코드 분석:**
- 파일: [관련 파일들]
- 현재 동작: [지금 코드가 뭘 하고 있는지]
- 문제점/갭: [목적과 현재 상태의 차이]

**해결 방향:**

해석1: [구체적 해석]
  ├ 현재: [코드가 지금 하는 것]
  ├ 변경: [뭘 어떻게 고쳐야 하는지]
  └ 결과: [고치면 뭐가 달라지는지]

해석2: [구체적 해석]
  ├ 현재: [...]
  ├ 변경: [...]
  └ 결과: [...]

해석3: [구체적 해석]
  ├ 현재: [...]
  ├ 변경: [...]
  └ 결과: [...]

어떤 게 맞아? (번호 or 설명)
```

#### 2.3. 해석 확정 방식 (반복 좁히기)
- **번호 + 자유 수정 가능**: "1번 근데 이것만 빼고", "2번이랑 비슷한데 이런 거야"
- 사용자가 수정 의견을 주면 → AI가 해당 해석 기반으로 **다시 좁혀서** 해석 제시
- 반복해서 점점 좁혀나가는 깔때기(Funnel) 방식
- 예시:
  ```
  1차 해석: 넓은 범위 3개 제시
      ↓ 사용자: "1번 비슷한데 이런 거야"
  2차 해석: 1번 기반으로 더 구체적인 3개
      ↓ 사용자: "2번이랑 거의 같은데 이 부분만 달라"
  3차 해석: 더 좁혀서 제시
      ↓ 사용자: "맞아!"
  확정 → 질문 단계로
  ```
- **확정 키워드**: "맞아", "확정", "그거야"
- **다 아니야**: 사용자에게 직접 설명 요청 후 다시 해석

### 3. 질문 단계 (반복 가능)
- **"질문"**: 목적을 구체화하기 위해 AI가 사용자에게 질문 합니다
- 해석이 확정된 후, 기존 2단계 질문 구조(큰틀 → 세부질문)로 진행

### 4. 답변 단계 (반복 가능)
- **"답변"**: 사용자가 질문에 대한 답변을 합니다.

### 5. 승인 및 실행
- 사용자가 **"승인"**이라고 말하면 코드 작성을 시작합니다
- 승인 전까지는 절대 코드를 작성하지 않습니다

### 단계별 역할 요약
| 단계 | 역할 |
|------|------|
| 해석 | "**뭘** 원하는 거야?" 확인 |
| 질문 | "**어떻게** 할까?" 세부 조율 |
| 브리핑 | "**이렇게** 할게" 최종 정리 |

## 브리핑
- 사용자는 "브리핑" 이라는 명령을 합니다.
  - 예 : 브리핑해, 브리핑 해줘, 브리핑
- 사용자가 "브리핑" 이라는 명령을 하면, 사용자가 목적을 달성할 수 있는 방법을 정리하여 AI가 사용자에게 브리핑합니다. 브리핑은 어느 단계에서든지 가능하며, 사용자는 질문과 브리핑을 동시에 요청할 수도 있음. 동시에 요청시 브리핑이 먼저 나오고 그 후 질문이 나온다. 
- 항상 마지막 브리핑 내용을 토대로 코딩이 진행됨

## 브리핑 규칙
"브리핑"을 명령 받으면 다음 형식에 맞게 정리하여 사용자에게 출력합니다

### 브리핑 형식:
- **목적**: [사용자의 목적을 추가, 보완하여 적는다]
- **해결방식**: [선택된 방법]
- **주요 작업**:
  - 1. [작업1]
  - 2. [작업2]
  - 3. [작업3]
- **예상 결과**: [구체적 산출물]

## 질문 규칙
사용자가 언제든지 "질문"이라는 명령어를 입력하면 AI는 사용자에게 **2단계 질문 구조**로 질문 합니다. AI는 1단계 큰틀을 제시하면서 사용자의 선택을 기다리고 사용자의 선택이 있은 후 2단계 세부 질문이 있을 것이라고 사용자에게 말해줍니다. AI가 2단계 세부 질문까지 사용자에게 전송하면 2단계 질문은 마무리 됩니다. 큰틀에 대한 질문이 더이상 필요 없다면 바로 2단계 세부질문부터 시작합니다. 
**중복 요청** : 사용자는 언제든지 큰틀 단계에서 계속 큰틀 질문을 더 요구할 수 있고, 세부질문 단계에서도 계속 세부질문을 더 요구할 수 있다. 

### [1단계] 큰 틀 제시
1. **목적 확인**: 사용자가 달성하려는 최종 목표를 파악합니다
2. **큰 틀 선택지 제시**:
   - 문제 해결을 위한 주요 접근 방식을 "방식1", "방식2", "방식3" 형태로 제시합니다
   - 방식 선택지는 구분되게 제시 (가독성 우선)
   - **표준 방식**: 현업에서 가장 널리 사용되는 검증된 방법
   - **대안 방식**: 특정 상황에서 유용한 비전통적 접근법
   - 예시:
     ```
     방식1: Selenium을 사용한 동적 크롤링 (표준)
     방식2: BeautifulSoup + requests를 사용한 정적 크롤링 (표준)
     방식3: Playwright를 사용한 헤드리스 크롤링 (대안)
     ```
3. **장단점 설명**: 각 방식의 장점, 단점, 적용 시나리오를 설명합니다

### [2단계] 세부 질문 (사용자가 큰 틀을 선택한 후)
- 사용자가 큰틀을 "방식1" 등으로 선택하면, 해당 방식에 대한 세부 질문을 진행
- 큰틀이 정해지고 다른 큰틀을 정할일이 없다면 큰틀 단계는 건너 뛰고 바로 2단계로 넘어갑니다. 
- **구체화 질문**: 선택한 방식에 대한 세부 사항을 계층적 번호로 질문합니다
   - 계층적 질문은 명확히 구분 (들여쓰기나 번호로)
   - 주 질문: 1. 질문내용, 2. 질문내용, 3. 질문내용
   - 세부 질문: 1-1. 세부질문, 1-2. 세부질문, 3-1. 세부질문...
   - 세부 질문 선택지: A. 선택사항, B. 선택사항, C. 선택사항
   - **반드시** 세부 질문 각 선택지에 대한 장단점을 설명합니다
   - 세부질문의 선택지는 1~3개 이상입니다. 
   - 선택지가 없는 질문도 할 수 있습니다. 

- **구체화 질문 예시**
```text
1. 주 질문 제목<br>
주 질문 내용<br>
1-1. 세부 질문 내용
 - A. 선택지 내용(추천 : 추천 이유)
   - 장점 : 장점 내용
   - 단점 : 단점 내용
 - B. 선택지 내용
   - 장점 : 장점 내용
   - 단점 : 단점 내용
 - C. 선택지 내용
   - 장점 : 장점 내용
   - 단점 : 단점 내용

2. 주 질문 제목<br>
주 질문 내용<br>
2-1. 세부 질문 내용
 - A. 선택지 내용
   - 장점 : 장점 내용
   - 단점 : 단점 내용
 - B. 선택지 내용(추천 : 추천 이유)
   - 장점 : 장점 내용
   - 단점 : 단점 내용
 - C. 선택지 내용
   - 장점 : 장점 내용
   - 단점 : 단점 내용
```
    
## 사용자의 답변 형식

- **큰 틀 선택**: "방식1", "방식2", "방식3" 등으로 답변하면 해당 접근 방식을 선택하는 것입니다
  - 예: "방식1", "방식2와 방식3 섞어서"
- **질문번호 답변**: "1", "1-1", "3-2" 등 숫자 번호를 적고 그 뒤에 내용을 적으면 해당 질문에 답변하는 것입니다
  - 예: "1. 하루에 3번", "1-1 비동기로 처리"
- **세부 선택지 답변**: 1-1A 또는 1-1:A 또는 1-1. A 등을 적는 방식으로 알파벳 선택지에 답변합니다
  - 예: "1-1A", "2-3:B", "3-1. C"


## 세부 질문 추천 답변
- AI는 **질문을 제시할 때** 모든 선택지에 대해 추천 옵션을 표시한다.
- 가장 에러가 나지 않을 확률이 높은 방식을 추천하며, 추천 이유도 함께 적는다.
- 명시형식: 질문 1-3 : A (*추천: 호환성 좋고 안정적*)

## 답변하지 않은 질문에 대한 처리
- 사용자가 일부 질문만 답하고 메시지를 보내면:
  1. AI가 **즉시** 답변되지 않은 질문을 확인
  2. 해당 질문에 대한 추천 답변을 **사용자에게 알림**
  3. **브리핑 시** 추천 답변을 기본값으로 포함


## 예외사항 (승인 없이 가능)

**읽기 전용 작업:**
- 파일 읽기 및 검색
- 코드 분석 및 설명
- 브리핑 및 질문
- 정보 제공 및 조언
- 기존 코드/테스트 실행 (수정 없이 실행만)
**특정 파일/폴더 수정 허용:**
- README.md 생성 및 수정
- 이벤트 카탈로그(README.md 내) 수정
- 테스트 관련:
  - `tests/` 폴더 생성
  - 테스트 파일 수정/생성 (`test_*.py`)
  - `conftest.py` 생성/수정
  - `fakes/` 폴더 및 fake 구현체 생성
- Mock 데이터 파일 생성 (fixtures, mocks)

**나머지 모든 코드 수정: 승인 필수**

## 승인 후 코딩
**대화 내용에서 마지막 브리핑 내용으로 최종 코딩한다**
- 대화중 승인이 완료되면 제일 마지막에 이루어진 브리핑 내용을 토대로 코딩을 한다
- **승인 후 코딩 전에는 반드시 브리핑이 되어 있어야 한다**
- 승인 → 코딩 흐름:
  ```
  사용자: "승인"
     ↓
  (브리핑 없었으면) AI가 자동 브리핑
     ↓
  AI: "이대로 진행할까요?"
     ↓
  사용자: "승인" 또는 "수정"
     ↓
  코딩 시작
  ```
- 브리핑이 이미 있었다면 바로 코딩 시작 가능 


# 이름 규칙(폴더이름, 패키지 이름, 모듈이름, 함수이름, 클래스이름, 메서드, 변수이름)

## 1. 공통
- 이름 길이에 제한 없음. 의미가 명확하면 길어도 OK.
- 줄임말 금지. 전부 풀어서 작성.
  - 예: `selenium_crawler_popup_handler_util.py` ✅
  - 예: `sel_crwl_popup.py` ❌
- 기능이나 역할이 바뀌면 **반드시** 이름도 같이 리팩토링한다.
- 새 이름이 필요하면 AI는 최소 3개 이상 후보를 제안한다. 각 후보에 "왜 이 이름인지" 설명 첨부한다. 
- Vertical Slice 설계 원칙을 고려하여 이름을 부여한다.
  - 기능 중심 네이밍: `User` 말고 `UserRegistration`, `UserLogin`

## 2. 함수/메서드 (snake_case)
- 패턴: `동사_대상[_세부]`
  예: `parse_list_page`, `save_auction_item`, `validate_form_field`
- 동사 먼저: `get/create/update/delete/parse/fetch/save/validate` 등.

## 3. 클래스 (PascalCase)
- 도메인: 명사 위주 – `AuctionItem`, `AuctionListing`, `Money`, `EmailAddress`
- 앱(use case): `동사+대상+Handler/UseCase`  
  예: `CreateAuctionItemHandler`, `ParseListPageUseCase`
- 인프라: `대상+역할`
  예: `AuctionItemRepository`, `ListPageFetcher`, `BrowserController`

## 4. 모듈(파일, snake_case)
- 레이어 이름 접두어 금지: `infra_...`, `application_...` 같은 건 쓰지 않는다.
- 패턴: `역할_대상[_세부][_util].py`
  예: `parse_list_page.py`, `auction_item_repository.py`, `browser_controller.py`
- **유틸 파일 접미사 규칙:**
  - 유틸 파일은 `_util` 접미사 필수: `format_date_util.py`, `validate_input_util.py`
  - 이유: 유틸임을 명시적으로 표시, shared 폴더 외에서도 유틸 식별 가능
- 테스트 파일은 대상/역할 이름을 맞춘다:
  예: `parse_list_page.py` ↔ `test_parse_list_page.py`

## 5. 하위 모듈 그룹핑
- 주 모듈에서 기능을 분리할 때, 분리된 모듈은 같은 폴더에 둔다.
- 파일명 형식: `{주모듈명}_{분리기능}_util.py`
- 예시:
  - 주 모듈: `selenium_crawler.py`
  - 분리 모듈: `selenium_crawler_popup_handler_util.py`
- 목적: 파일명만 보고 "이 파일은 저 파일의 하위 모듈"임을 파악 가능

# 코드 추론 규칙
**이 프로젝트의 코드는 위 이름 규칙을 일관되게 따른다는 전제를 둔다**
- AI는 이름에 포함된 도메인, 동사, 대상, 세부/입출력, 사용 기술 정보를 적극 활용해 역할과 동작을 이름만 보고 자유롭게 추론해도 된다.
- 이름 기반 코드 추론 후 반드시 코드 읽어서 검증한다.
- 이름과 실제 구현이 충돌하면, 구현이 기준이며 이름은 리팩토링 대상이다.

## README.md 우선 참조 규칙

### 적용 시점
- 코드 **분석/수정** 시에만 적용
- 단순 파일 조회(읽기만)는 제외

### 참조 절차
1. **타이밍**: 코드 파일 열기 **전에** 해당 폴더의 README.md를 먼저 확인한다
2. **연관 폴더 범위**:
   - 분석 대상 코드가 위치한 폴더
   - import하는 모듈의 폴더들
3. **읽는 순서**: 분석 대상 폴더 README 먼저 → import 폴더들 순차적으로
4. **README 없는 경우**: 무시하고 코드 분석 진행

### 사용자에게 알림
- 분석 시작 전 참조한 README 목록을 한 줄로 언급한다
- 형식: `📖 README 참조: search/, shared/, domain/`

### README와 코드 불일치 시
- **코드가 기준**이다
- README 내용이 코드와 다르면 README 업데이트를 제안한다 




# 프로젝트 아키텍쳐 설계 규칙
**버티컬 슬라이스 설계 규칙을 따른다**
## 1. 기본 전제
* 프로젝트 루트: `project/src`
* 주요 구조:
  * `src/features/<FeatureName>/` : 기능/도메인 단위 슬라이스
  * `src/shared/` : 여러 feature가 실제로 공유하는 최소 공통 코드
  * `src/main.py` : 엔트리 포인트

## 2. 구조 규칙
1. 프로젝트 상위 구조
   * `src/features/`  : 기능/도메인 단위 슬라이스 루트
   * `src/shared/`    : 여러 feature가 실제로 공유하는 최소 공통 코드
   * `src/main.py`    : 엔트리 포인트
2. 새 기능을 추가할 때는 항상 먼저 `src/features/<FeatureName>/` 아래에 코드를 둔다.
3. 코드 중복은 허용하며,
   * 새로운 공통 폴더를 만드는 것보다 각 슬라이스 내부에 유지하는 것을 우선한다.
4. **feature 내 shared 승격 기준**
   * 조건: 동일 코드가 **5개 이상 파일**에서 import될 때
   * 조치: `src/features/<FeatureName>/shared/` 폴더로 승격 검토
   * 사용자 승인 후 리팩토링
5. **전역 shared 승격 기준**
   * 조건: **5개 이상 파일** + **2개 이상 feature**에서 import될 때
   * 조치: `src/shared/`로 승격 검토
   * 사용자 승인 후 리팩토링
   * 측정 방법: grep/검색으로 import 문 카운트 

## 3. 폴더 구조 예시
```text
project/
└── src/
    ├── features/
    │   ├── google/     # 1차 슬라이스 예시
    │   └── naver/
    │         ├── search/     # 2차 슬라이스 예시
    │         ├── blog/
    │         ├── shared/         # 공통 모듈
    │         └── ...         # 필요 시 계속 추가
    ├── shared/          # 전역 공통 모듈
    │   ├── config.py          # 전역 설정 (API 키, 기본 헤더 등)
    │   └── exceptions.py   # 전역 예외 + 로깅 설정
    └── main.py            # 엔트리 포인트 (실행 스크립트)
```

## 4. Import 규칙 (Python)
1. 내부 모듈은 항상 **파일(모듈) 레벨까지 절대 경로**로 import 한다.
   * ❌ 금지: `from src.features.naver.search import fetch_search_results`
   * ✅ 허용: `from src.features.naver.search.service import fetch_search_results`
   * ✅ 허용: `from src.shared.config import settings`
2. 상대 import (`from .x`, `from ..x`)는 사용하지 않는다.
3. 다른 feature 코드 재사용 시에도 같은 방식으로 import 해서,
   * 의존성이 import 경로에 드러나도록 유지한다.
4. **`__init__.py` 규칙**
   * `__init__.py`에서 다른 모듈을 re-export 하지 않는다.
     - ❌ 금지: `from .main_window import MainWindow`
     - ❌ 금지: `from .service import *`
   * `__init__.py`는 비워두거나, 패키지 초기화 로직만 허용한다.
     - ✅ 허용: 빈 파일
     - ✅ 허용: 패키지 로드 시 필요한 설정/초기화 코드
   * import는 **항상 원본 파일까지 풀 경로**로 작성한다.
     - ❌ 금지: `from src.features.site_crawler.api.gui import MainWindow`
     - ✅ 허용: `from src.features.site_crawler.api.gui.main_window import MainWindow`
   * 이유: AI와 사람 모두 원본 위치를 즉시 파악할 수 있어 혼란 방지
   * **예외: 엔트리포인트에서의 re-export**
     - `src/` 바깥(main.py 등 엔트리포인트)에서 import할 때는 `__init__.py`에서 re-export 허용
     - 이유: 엔트리포인트는 외부 인터페이스이므로 깔끔한 import 경로 제공 가능
     - ✅ 허용: `main.py`에서 `from src.features.xxx import SomeClass` (해당 `__init__.py`에 re-export 있을 때)
     - ❌ 금지: feature 간 import에서 `__init__.py` re-export 사용

## 5. Feature / 슬라이스 규칙
1. 하나의 feature 폴더 안에 해당 기능을 이해·수정하는 데 필요한 코드를 최대한 모은다.
2. feature가 커질 경우에 2차 슬라이스 고려한다:
   * 예: `src/features/naver/search/`, `src/features/naver/blog/`
3. 2차 슬라이스 간 공통 코드는 우선 `src/features/<FeatureName>/shared/`에 둔다.


## 6. Feature 내부 레이어 규칙

### 6.0. 레이어 구성 원칙

**기본 구성 (모든 feature 최소):**
- `domain/`: 비즈니스 모델/규칙/엔티티
- `app/`: 유즈케이스/비즈니스 로직

**필요시 추가:**
- `api/`: 외부 입력(HTTP/CLI/파일)을 받을 때만
- `infra/`: 외부 시스템(DB/API/파일)과 연동할 때만

**예외 (레이어 없이 shared/utils/):**
- 단순 유틸/헬퍼 함수
- 판단 기준: 비즈니스 규칙 없고, 순수 변환/포맷/계산만

### 6.1. 레이어별 구조 예시

**6.1.1. 기본 2레이어 (최소 구성)**
```text
features/
└── <FeatureName>/
    ├── __init__.py
    ├── README.md
    ├── domain/              # 비즈니스 규칙/엔티티
    │   ├── __init__.py
    │   └── models.py
    └── app/                 # 유즈케이스/로직
        ├── __init__.py
        └── use_cases.py
```

**6.1.2. 3레이어 (외부 입력 필요)**
```text
features/
└── <FeatureName>/
    ├── domain/
    ├── app/
    └── api/                 # HTTP/CLI/파일 입력 처리
        ├── __init__.py
        └── routes.py
```

**6.1.3. 3레이어 (외부 시스템 연동)**
```text
features/
└── <FeatureName>/
    ├── domain/
    ├── app/
    └── infra/               # DB/외부API 연동
        ├── __init__.py
        ├── repositories.py
        └── adapters.py
```

**6.1.4. 4레이어 (풀스택)**
```text
features/
└── <FeatureName>/
    ├── __init__.py
    ├── README.md
    ├── domain/              # 비즈니스 규칙/엔티티 (외부 의존성 0)
    │   ├── __init__.py
    │   ├── models.py        # 도메인 모델/엔티티
    │   ├── value_objects.py # 값 객체
    │   └── events.py        # 도메인 이벤트
    ├── app/                 # 유즈케이스/애플리케이션 로직
    │   ├── __init__.py
    │   └── use_cases.py     # 유즈케이스 구현
    ├── api/                 # 외부 인터페이스 (HTTP/CLI/이벤트 핸들러)
    │   ├── __init__.py
    │   └── routes.py        # API 엔드포인트
    └── infra/               # DB/파일/외부 API 등 기술 구현체
        ├── __init__.py
        ├── repositories.py  # DB 연동
        └── adapters.py      # 외부 API 연동
```

### 6.2. 레이어별 역할 및 의존성 규칙

- **domain/**: 비즈니스 규칙, 엔티티, 값 객체
  - 다른 레이어에 의존하지 않는다
  - 외부 라이브러리 의존 최소화 (dataclass, enum 정도만)

- **app/**: 유즈케이스, 애플리케이션 서비스
  - `domain`에만 의존 가능
  - infra의 구체 구현이 아닌 인터페이스(Protocol)에 의존

- **api/**: HTTP/CLI/이벤트 핸들러 등 외부 인터페이스
  - `app`, `domain`에 의존 가능
  - 외부 입력 검증·파싱, 인증/인가, 요청→DTO/커맨드 매핑 담당
  - 비즈니스 규칙/계산 로직은 넣지 않고, 유즈케이스(app) 호출에만 집중
  - `api`는 얇은 껍데기로 두고, 실제 비즈니스 로직은 `app/domain`에 구현

- **infra/**: DB/파일/외부 API 등 기술 구현체
  - `domain` 타입을 사용해 구현 가능
  - 실제 I/O 작업 수행 (DB, HTTP, 파일 등)

### 6.3. 단순 유틸 배치 규칙

**유틸 판단 기준:**
1. 비즈니스 규칙/도메인 로직이 없음
2. 순수 변환/포맷/계산 함수

**배치 흐름:**
```
feature 내에서만 사용 → features/<Feature>/shared/
         ↓ (범용성 커짐 + 사용자 요청 + 승격 기준 충족)
src/shared/
```

**feature 내 유틸 구조:**
```text
features/<Feature>/shared/
├── format_date_util.py           # 파일 5개 이하: flat 구조
├── validate_input_util.py
└── calculate_price_util.py
```

**카테고리 폴더 (파일 5개 초과 시):**
```text
features/<Feature>/shared/
├── formatters/                   # 복수형 명사 사용
│   ├── format_date_util.py
│   └── format_number_util.py
└── validators/
    └── validate_input_util.py
```

**전역 shared 구조:**
```text
src/shared/
├── formatters/
│   └── format_date_util.py
└── validators/
    └── validate_input_util.py
```

### 6.4. AI 행동 규칙

- **새 feature 생성 시**: domain + app 기본 생성
- **외부 입력 처리 필요**: api/ 추가
- **외부 시스템 연동 필요**: infra/ 추가
- **각 레이어 폴더**: 최소한 `__init__.py` 포함
- **README.md**: 각 레이어의 주요 책임과 파일 목록 기록
- **의존성 위반**: 즉시 사용자에게 경고


## 7. 아키텍쳐 설계 에이전트 행동 규칙
1. 모듈화/설계/아키텍처 관련 요청이 들어오면
   **항상 이 문서의 프로젝트 아키텍쳐 설계 규칙을 우선 기준**으로 사용한다.

2. 새 feature 또는 슬라이스와 관련된 코드를 생성·수정하기 전에 **반드시 슬라이스 브리핑**을 먼저 제안한다.
   슬라이스 브리핑 최소 정보:
   * (1) Feature/슬라이스 이름
   * (2) 폴더 경로 (예: `src/features/naver/search/`)
   * (3) 생성/수정할 파일 경로 + 파일 이름 후보 ≥ 2개
   * (4) 필요한 경우, 사용할 절대 import 의존 관계 목록
   * 이름 후보의 경우 이 문서의 이름 규칙을 따른다. 

3. 사용자가 **"승인"**을 명시적으로 말하기 전에는
   * 실제 폴더/파일/코드를 생성하거나 수정하지 않는다.




# CODE_RULES_CORE

## 0. 확장성
* 코드 작성 시 이후 기능/규칙 추가를 예상하고 구조를 잡는다.
* 새 동작은 새 유즈케이스/클래스/함수로 분리 가능하게 설계한다.

## 1. 의존성 주입 (DI)
* domain/app 클래스는 DB/HTTP/Logger 등 외부 자원을 직접 생성하지 않는다.
* 모든 외부 자원은 생성자 또는 함수 인자로 주입한다.

## 2. 결합도↓, 응집도↑
* 파일/클래스/함수는 한 가지 역할만 가진다.
* 파싱/계산/저장/알림 등 서로 다른 단계를 한 함수에 섞지 않는다.

## 3. 순수 함수 우선
* 비즈니스 규칙·계산은 가능한 한 순수 함수(입력 → 출력, 부수효과 없음)로 구현한다.

## 4. 사이드 이펙트 경계
* DB/파일/HTTP/시간/랜덤 호출은 `features/<Feature>/{api, infra}` 에만 둔다.
* 비즈니스/유즈케이스 로직(`features/<Feature>/{domain, app}`)에서는 주입된 Repo/Clock/Client 등만 사용한다.

## 5. 입력 검증 입구
* 외부 입력(HTTP 요청, 쿼리, 폼, 파일 등)의 검증·파싱은 api/infra 레이어에서 처리한다.
* domain/app 에는 검증된 DTO/도메인 객체만 전달한다.

## 6. 테스트 친화성
* 비즈니스 로직은 DI와 순수 함수로 설계해 fake/in-memory 구현으로 단위 테스트 가능하도록 만든다.
* 가능한 한 외부 자원 없이 fake/in-memory 구현만으로도 주요 흐름을 돌릴 수 있게 만든다  
  (예: `InMemoryRepo`, `FakeClock`, `FakeNotifier` 등).

## 7. 코드 포맷 (Black)
* 파이썬 코드는 Black 포매터 기준으로 생성한다.
* 줄바꿈·들여쓰기·괄호 배치는 Black 실행 시 추가 변경이 없도록 출력한다.

## 8. 제어의 역전(IoC) / 콜백 / 옵저버
* `features/<Feature>/domain` 는 "무슨 일이 일어났는지(이벤트)"만 정의하고, 후속 동작은 `features/<Feature>/{app, infra}` 핸들러에 맡긴다 (I/O 사용 시 4번 규칙 준수).
* 새 후처리·알림·로깅이 필요하면 기존 유즈케이스를 고치기보다 이벤트 핸들러(리스너/옵저버)를 추가하는 방향을 우선한다.
* 상태를 반복적으로 if로 감시하지 말고, "이벤트 발생 → 핸들러 호출" 구조(옵저버 패턴)를 우선 사용한다.
* 이 규칙은 규모가 커지거나 하나의 이벤트에 여러 반응이 필요할 때 우선 적용하고, 분기가 3개 이하일 때는 단순 직접 호출로 대신할 수 있다.
* 이벤트/핸들러 이름은 발생한 일을 드러내게 짓는다.  
  예: `AuctionEndedEvent`, `NotifyUserOnAuctionEndHandler`

## 9. 타입 힌트 필수
* `features/<Feature>/{domain, app}` 의 공개 함수/메서드는 반드시 타입 힌트를 명시한다.
* `Any`는 가능한 한 사용하지 않는다. 딱 정하기 어렵다면 별도 DTO/타입을 정의해서 사용한다.
* 컬렉션 타입은 구체적으로 쓴다.  
  예: `list[AuctionItem]`, `dict[str, str]`

## 10. 주석 (맥락 전달용 최소 주석)
* 주석은 명령형으로 적는다. (예: ~해라, ~한다, ~해)
* 함수/클래스/모듈 단위로 "왜 존재하는지(why), 어떤 규칙/의도/목적을 구현하는지"를 적는다.
  * 예시
    - 목적 : *내용*
    - 이유 : *내용*
* 복잡한 분기(IF)나 비즈니스 규칙이 있는 부분에만 이유/배경을 주석으로 적는다.
* 사용자와 AI의 브리핑/질문/설계 논의에서 나온 핵심 의도는  
  관련 파일 상단 또는 관련 함수 위에 요약 주석으로 남긴다.
* 코드가 바뀌어 주석 내용이 더 이상 맞지 않으면, 과감히 삭제하거나 즉시 수정한다.
* 핵심 유즈케이스/함수에는 간단한 입·출력 예시를 주석 또는 docstring으로 남긴다.  
  예: `# 예: 입력(최저가=10, 입찰가=[8, 12, 15]) → 낙찰가=12`
* 예시는 "실제 쓸 법한 값"으로 적어, 코드 의도를 명확히 드러낸다.

## 11. 파일 헤더 주석 규칙
* 모든 Python 파일 상단에 다음 형식의 docstring을 작성한다.

### 필수 항목 (모든 파일)
```python
"""
레이어: [domain | app | api | infra | shared]
역할: [이 파일이 하는 일 한 줄 설명]
의존: [import하는 내부 모듈 목록, 없으면 "없음"]
외부: [import하는 외부 라이브러리 목록, 없으면 "없음"]
"""
```

### 선택적 추가 항목
| 항목 | 사용 시점 |
|------|-----------|
| `목적:` | 역할만으로 "왜 존재하는지" 설명이 부족할 때 |
| `사용법:` | 여러 곳에서 import하는 공용 모듈 |
| `주의:` | 실수하기 쉬운 부분이 있을 때 |
| `발행 이벤트:` | 이벤트 기반 설계 시 |
| `구현 프로토콜:` | Protocol 구현체일 경우 |

### 예시 (필수만)
```python
# features/order/app/create_order_use_case.py
"""
레이어: app
역할: 주문 생성 유즈케이스
의존: domain/models.py, domain/events.py
외부: 없음
"""
```

### 예시 (선택 항목 포함)
```python
# shared/logging/app_logger.py
"""
레이어: shared
역할: 애플리케이션 전역 로거 제공
의존: 없음
외부: 없음

목적: 여러 feature에서 일관된 로깅을 위해

사용법:
    from src.shared.logging.app_logger import get_logger
    logger = get_logger()
    logger.info("메시지")

주의:
- UI 콘솔 로그와는 별개로 파일에만 기록됨
"""
```

### 헤더 주석 유지보수
* 코드 변경 시 헤더 주석도 함께 업데이트한다.
  - import 추가/삭제 → `의존:`, `외부:` 수정
  - 역할 변경 → `역할:` 수정
  - 레이어 이동 → `레이어:` 수정

## 12. 테스트 파일 규칙
* 각 feature 폴더 최상위에 `tests/` 폴더를 둔다.
```text
features/<FeatureName>/
├── domain/
├── app/
├── api/
├── infra/
└── tests/           # 테스트 모음
    ├── __init__.py
    ├── test_models.py
    ├── test_<use_case_name>.py
    └── conftest.py  # pytest fixtures
```
* 파일명 규칙:
  - 테스트 파일명: `test_<원본파일명>.py`
  - Fixture 파일: `conftest.py`
  - Mock/Fake 구현: `fakes/` 하위 폴더
* 예시:
```text
features/payment/
├── app/
│   └── process_payment_use_case.py
└── tests/
    ├── fakes/
    │   └── fake_payment_gateway.py
    ├── test_process_payment_use_case.py
    └── conftest.py
```

## 13. 이벤트/콜백 카탈로그 규칙
* 이벤트 기반 설계 또는 콜백 패턴 사용 시, README.md에 카탈로그를 작성한다.
* 형식:
```markdown
## 이벤트 카탈로그

| 이벤트명 | 발행 위치 | 구독 위치 | 페이로드 |
|----------|-----------|-----------|----------|
| [이벤트] | [발행 파일] | [구독 파일] | [데이터 타입] |
```
* 예시:
```markdown
| OrderCreatedEvent | CreateOrderUseCase | NotificationService, InventoryService | order: Order |
| PaymentFailedEvent | ProcessPaymentUseCase | OrderService, AlertService | order_id: str, reason: str |
```
* 적용 시점:
  - 이벤트 기반 설계 사용 시 카탈로그 작성
  - 새 이벤트 추가 시 카탈로그도 함께 업데이트
* AI 행동 규칙:
  - 이벤트 관련 작업 시작 전, 카탈로그를 먼저 읽고 코드와 대조 검증한다
  - 검증 범위: 발행 위치, 구독 위치, 페이로드 타입
  - 카탈로그와 코드가 불일치하면 사용자에게 알리고 수정을 제안한다
  - 이벤트 관련 코드 수정 시 카탈로그도 반드시 함께 업데이트한다

## 14. UseCase 작성 템플릿
* app 레이어의 UseCase는 다음 구조를 따른다:
```python
class [동사][명사]UseCase:
    """
    목적: [한 줄 설명]
    """

    def __init__(self, [의존성들]: [Protocol 타입]):
        self._[의존성] = [의존성]

    def execute(self, [입력 파라미터]) -> [반환 타입]:
        """
        [메서드 설명]

        Args:
            [파라미터]: [설명]

        Returns:
            [반환값 설명]

        Raises:
            [예외]: [발생 조건]
        """
        # 1. 검증 (필요시)
        # 2. 비즈니스 로직 실행
        # 3. 결과 반환 또는 이벤트 발행
```
* 네이밍 패턴:
| 동작 | 동사 | 예시 |
|------|------|------|
| 생성 | Create | CreateOrderUseCase |
| 조회 | Get/Find/Search | GetUserUseCase, SearchProductUseCase |
| 수정 | Update/Modify | UpdateProfileUseCase |
| 삭제 | Delete/Remove | DeleteCommentUseCase |
| 처리 | Process/Handle | ProcessPaymentUseCase |
| 검증 | Validate/Verify | ValidateTokenUseCase |

## 15. 금지 패턴
### ❌ 역방향 의존 금지
```python
# domain/models.py - 절대 금지!
from src.features.xxx.infra.some_impl import SomeImpl  # infra → domain 역방향
from src.features.xxx.app.some_use_case import SomeUseCase  # app → domain 역방향
```

### ❌ UseCase에서 직접 I/O 금지
```python
# app/some_use_case.py - 절대 금지!
import requests  # 직접 HTTP 호출 금지
import sqlite3   # 직접 DB 접근 금지

def execute(self):
    conn = sqlite3.connect("db.sqlite")  # 주입받아야 함
```

### ❌ API/GUI에서 비즈니스 로직 금지
```python
# api/routes.py 또는 api/gui/widget.py - 절대 금지!
def on_submit(self):
    if price > 1000 and user.level == "gold":  # 비즈니스 규칙
        discount = 0.1
    # → UseCase나 Domain으로 이동해야 함
```

### ❌ 구체 클래스 직접 의존 금지 (app 레이어)
```python
# app/some_use_case.py - 절대 금지!
from src.features.xxx.infra.mysql_repository import MySQLRepository

class SomeUseCase:
    def __init__(self):
        self.repo = MySQLRepository()  # 구체 클래스 직접 생성 금지
```

### ✅ 올바른 방식
```python
# app/some_use_case.py - 올바름
from src.features.xxx.infra.i_repository import IRepository  # Protocol import

class SomeUseCase:
    def __init__(self, repo: IRepository):  # Protocol 타입으로 주입
        self._repo = repo
```

## 16. 변경 영향도 가이드
### 레이어별 영향 범위
| 변경 레이어 | 영향 범위 | 주의 수준 |
|-------------|-----------|-----------|
| domain/models | 전체 (app, api, infra) | 🔴 높음 |
| domain/events | app + api (구독자) | 🟠 중간 |
| app/use_cases | api (호출부) | 🟡 낮음 |
| infra/* | 없음 (독립적) | 🟢 안전 |
| api/* | 없음 (독립적) | 🟢 안전 |

### AI 행동 규칙
* **domain 수정 전**: 영향받는 모든 파일 목록을 먼저 출력한다
* **event 수정 전**: 구독자 목록을 먼저 확인한다
* **Protocol 수정 전**: 구현체 목록을 먼저 확인한다

### README.md 기록 형식 (선택)
```markdown
## 변경 영향도 맵

| 파일 | 수정 시 확인 필요 |
|------|-------------------|
| domain/models.py | app/*, infra/repository.py |
| domain/events.py | api/gui/*, app/event_handlers.py |
```


## 17. AI 특화 금지 패턴 (연구 기반)
> 15번은 아키텍처/의존성 금지, 17번은 AI 코드 생성 시 흔한 실수 금지

### ❌ 조건/분기 금지
- 조건문에서 else/예외 케이스 누락 금지
  - 이유: AI가 해피 패스만 생성 → None 반환 버그
- 경계값(0, -1, None, 빈 리스트) 처리 누락 금지
  - 이유: AI가 정상 입력만 가정 → 런타임 크래시

### ❌ 인덱스/컬렉션 금지
- 인덱스 접근 전 길이 체크 없이 접근 금지
  - 이유: 연구에서 Java 런타임 에러의 46.4%가 인덱스 오류
- 하드코딩된 인덱스 사용 금지 (예: `arr[3]`)
  - 이유: 데이터 구조 변경 시 100% 버그 발생

### ❌ 완결성 금지
- 함수 작성 시 TODO/FIXME 남기고 끝내기 금지
  - 이유: "동작하는 것처럼 보이는" 불완전한 코드 방지
- "나머지는 비슷하게..." 식의 생략 금지
  - 이유: 생략된 부분에 미묘한 차이 존재 가능
- 호출만 하고 반환값 처리 안 하기 금지
  - 이유: 실패한 작업을 성공으로 착각하는 버그 방지

### ❌ 외부 의존 금지
- 존재 확인 안 된 라이브러리 import 금지
  - 이유: AI가 존재하지 않는 패키지 추천 (hallucination)
  - 검증: PyPI에서 패키지 존재 여부 확인 후 추천
- 버전 명시 없는 라이브러리 추천 금지
  - 이유: 버전별 API 차이 → 재현 불가 환경

### ❌ 언어 혼동 금지
- 다른 언어 문법/동작 혼용 금지
  - 이유: AI가 여러 언어를 동시 학습 → 미묘한 차이 혼동
- 흔한 혼동 예시:
  - Python ↔ JavaScript: `len(x)` vs `.length`, `append()` vs `.push()`
  - Python ↔ Java: `//` (정수나눗셈) vs `/` (실수나눗셈), `round()` 동작 차이

## 18. 에러 핸들링 규칙
* 모든 레이어에서 동일한 에러 처리 방식을 적용한다
* 에러 메시지는 "무엇이 + 왜 + 해결방법"을 포함한다
  - 예: `"파일을 찾을 수 없습니다: config.json. 프로젝트 루트에 파일이 있는지 확인하세요."`
* 빈 except 절대 금지
  - ❌ 금지: `except: pass`
  - ❌ 금지: `except Exception: pass`
  - ✅ 허용: `except Exception as e: logger.error(f"에러 발생: {e}")`

## 19. 로깅 규칙
* print() 허용, logger 사용 권장
* 로그 레벨 4단계:
  - DEBUG: 개발 중 상세 정보
  - INFO: 정상 흐름 기록
  - WARNING: 주의가 필요한 상황
  - ERROR: 실패/에러 상황
* 민감정보 로깅: 개발 단계에서 허용 (프로덕션 배포 시 재검토)

### 로그 포맷
* 표준 포맷: `%(asctime)s %(levelname)s [%(pathname)s:%(lineno)d %(funcName)s] %(message)s`
* 출력 예시: `2024-11-27 14:30:25 INFO [d:\...\use_cases.py:42 execute] 크롤링 시작`

### ERROR 로깅 규칙
* ERROR 레벨은 `logger.exception()` 사용 권장
* 이유: 스택트레이스 자동 포함 → AI 디버깅 효율 증가

### 실행 기반 로그 로테이션
* 앱 실행 시마다 새 로그 파일 생성
* 파일명 형식: `app_YYYY-MM-DD_HH-MM-SS.log`
  - 예: `app_2024-11-27_14-30-25.log`
* 최대 **5개** 유지, 초과 시 가장 오래된 파일 자동 삭제
* 로그 경로: `src/shared/logging/logs/`



## 20. 에러 디버깅 시 AI 행동 규칙

### 로그 파일 위치
* 전역 로그 경로: `src/shared/logging/logs/`

### AI 자동 참조 트리거
* 사용자가 다음 키워드 언급 시 AI는 최근 로그 파일을 자동 참조한다:
  - `에러`, `버그`, `실패`, `안 돼`
* 트리거 감지 시 AI 행동:
  1. 최근 로그 파일 1개 읽기
  2. ERROR/WARNING 레벨 필터링
  3. 문제점 요약 및 해결방안 제시

### 로그 기반 디버깅 브리핑 형식
```
**로그 분석 결과:**
- 발견된 문제: [에러 내용 요약]
- 추정 원인: [원인 분석]
- 해결 방안: [제안 사항]
```

### 주의사항
* 로그 파일이 없거나 비어있으면 사용자에게 알린다
* 민감정보가 로그에 있을 수 있으므로 외부 공유 시 주의

