import time
import re
from difflib import SequenceMatcher

from selenium import webdriver
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    InvalidElementStateException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from src2.shared.logging.app_logger import get_logger

# ChromeController 전용 로거
# 목적: ChromeController의 모든 동작을 파일로 기록
LOGGER = get_logger()


class ChromeController:
    """Wraps Selenium attachment to the already running Chrome session."""

    def __init__(self, debugger_address: str = "127.0.0.1:2578"):
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", debugger_address)

        try:
            self.driver = webdriver.Chrome(options=options)
            LOGGER.info("Chrome 연결 성공: %s", debugger_address)
            self._log_versions()
            try:
                self.main_handle = self.driver.current_window_handle
                LOGGER.info("메인 핸들 기억: %s", self.main_handle)
            except WebDriverException:
                LOGGER.warning("초기 메인 핸들을 가져오지 못했어")
                self.main_handle = None
        except WebDriverException as exc:
            LOGGER.exception("Chrome 드라이버 연결 실패", exc_info=exc)
            raise RuntimeError(
                "Chrome 드라이버에 붙을 수 없었어. 크롬이 --remote-debugging-port 옵션으로 켜져 있는지 확인해줘!"
            ) from exc

    def fill_field(
        self,
        locator_type: str,
        locator_value: str,
        input_value: str,
        mode: str = "normal",
    ) -> None:
        LOGGER.info(
            "필드 채우기 요청: mode=%s %s=%s 값=%s",
            mode,
            locator_type,
            locator_value,
            input_value,
        )
        locator_value = locator_value.strip()
        if not locator_value:
            LOGGER.warning("빈 locator_value 입력")
            raise ValueError("찾을 요소 이름이 비어 있어. 두 번째 칸 채워줘!")

        strategies = {
            "id": By.ID,
            "name": By.NAME,
            "class name": By.CLASS_NAME,
            "css selector": By.CSS_SELECTOR,
            "xpath": By.XPATH,
        }

        by = strategies.get(locator_type)
        if by is None:
            raise ValueError(f"지원하지 않는 찾기 방식이야: {locator_type}")

        mode_key = (mode or "normal").lower()

        self._focus_active_tab()

        try:
            try:
                LOGGER.info("현재 URL: %s", self.driver.current_url)
                LOGGER.info("현재 제목: %s", self.driver.title)
            except WebDriverException:
                LOGGER.warning("현재 URL이나 제목을 가져오지 못했어")

            wait = WebDriverWait(self.driver, 10)
            element = wait.until(EC.presence_of_element_located((by, locator_value)))
        except (NoSuchElementException, TimeoutException) as exc:
            LOGGER.exception("요소 탐색 실패", exc_info=exc)
            raise RuntimeError(
                f"요소를 못 찾았어. {locator_type}='{locator_value}' 확인해줘!"
            ) from exc
        except Exception as exc:
            LOGGER.exception("요소 대기 중 예외", exc_info=exc)
            raise RuntimeError(
                "요소 기다리는 중에 문제가 생겼어. 로그를 확인해줘!"
            ) from exc

        if mode_key == "select":
            try:
                self._fill_select_field(element, input_value)
                return
            except Exception as exc:
                LOGGER.warning("셀렉트 즉시 선택 실패, 안전장치 진입: %s", exc)
                initial_signature = ()
                try:
                    initial_options = element.find_elements(By.TAG_NAME, "option")
                    initial_signature = self._options_signature(initial_options)
                except WebDriverException:
                    initial_signature = ()
                try:
                    element, options = self._wait_for_select_ready(
                        by, locator_value, initial_signature
                    )
                except TimeoutException as wait_exc:
                    LOGGER.exception("셀렉트 옵션 대기 중 타임아웃", exc_info=wait_exc)
                    raise RuntimeError("셀렉트 옵션이 준비되지 않았어!") from wait_exc
                self._fill_select_field(element, input_value, options)
        else:
            self._fill_text_field(by, locator_value, input_value)

    def _focus_active_tab(self):
        # 목적: 활성 탭에 포커스를 맞춰 입력 대상 페이지를 명확히 함
        try:
            handles = self.driver.window_handles
        except WebDriverException:
            LOGGER.warning("윈도우 핸들을 가져오지 못했어")
            return

        if not handles:
            LOGGER.warning("열린 탭이 없어 보여. 디버깅 포트 연결이 맞는지 확인해줘!")
            return

        current = self.driver.current_window_handle

        if getattr(self, "main_handle", None) in handles:
            target = self.main_handle
            if current != target:
                LOGGER.info("탭 전환: %s -> %s (메인 핸들)", current, target)
                try:
                    self.driver.switch_to.window(target)
                except WebDriverException:
                    LOGGER.warning("메인 핸들 전환이 실패했어")
            return

        fallback = None
        for handle in handles:
            if handle == current:
                continue
            try:
                self.driver.switch_to.window(handle)
                url = self.driver.current_url
            except WebDriverException:
                continue

            LOGGER.info("탭 검사: %s -> %s", handle, url)
            if not url.startswith("devtools://"):
                fallback = handle
                break

        try:
            self.driver.switch_to.window(current)
        except WebDriverException:
            LOGGER.warning("원래 탭으로 복귀 실패")

        if fallback:
            self.main_handle = fallback
            if current != fallback:
                LOGGER.info("탭 전환: %s -> %s (대체)", current, fallback)
                try:
                    self.driver.switch_to.window(fallback)
                except WebDriverException:
                    LOGGER.warning("대체 핸들 전환 실패")

    def _fill_text_field(self, by, locator_value: str, input_value: str) -> None:
        # 목적: 텍스트 입력 필드에 값을 채움 (재시도 로직 포함)
        last_exception = None
        for attempt in range(1, 4):
            try:
                element = self.driver.find_element(by, locator_value)
            except (NoSuchElementException, StaleElementReferenceException) as exc:
                last_exception = exc
                LOGGER.warning(
                    "텍스트 요소 재탐색 실패 (시도 %s/3, locator=%s)",
                    attempt,
                    locator_value,
                )
                time.sleep(0.5)
                continue

            if not element.is_enabled():
                LOGGER.info(
                    "텍스트 요소 비활성화 상태 (시도 %s/3, locator=%s)",
                    attempt,
                    locator_value,
                )
                time.sleep(0.5)
                continue

            readonly = (element.get_attribute("readonly") or "").lower()
            if readonly in {"true", "readonly"}:
                LOGGER.info(
                    "텍스트 요소 readonly 상태 (시도 %s/3, locator=%s)",
                    attempt,
                    locator_value,
                )
                time.sleep(0.5)
                continue

            try:
                element.clear()
                if input_value:
                    element.send_keys(input_value)
                LOGGER.info("입력 성공 (텍스트)")
                return
            except (
                InvalidElementStateException,
                StaleElementReferenceException,
            ) as exc:
                last_exception = exc
                LOGGER.warning(
                    "텍스트 입력 시도 실패 (시도 %s/3, locator=%s): %s",
                    attempt,
                    locator_value,
                    exc,
                )
                time.sleep(0.5)
        raise RuntimeError(f"텍스트 필드를 편집할 수 없었어: {last_exception}")

    def _fill_select_field(self, element, target_value: str, options=None) -> None:
        # 목적: 셀렉트 박스에서 유사도 기반으로 옵션 선택
        tag = element.tag_name.lower()
        if tag != "select":
            raise RuntimeError("셀렉트 모드인데 <select> 요소를 찾지 못했어!")

        if options is None:
            options = element.find_elements(By.TAG_NAME, "option")
        if not options:
            raise RuntimeError("선택할 옵션이 없어!")

        target_value = target_value.strip()
        norm_target = self._normalize_option(target_value)

        best_index = None
        best_score = -1.0
        best_desc = ""
        for idx, option in enumerate(options):
            text = option.text.strip()
            value_attr = option.get_attribute("value") or ""
            candidates = [text, value_attr]
            score = max(
                self._match_score(norm_target, self._normalize_option(candidate))
                for candidate in candidates
            )
            LOGGER.info(
                "옵션 검사 #%s: text='%s' value='%s' score=%.3f",
                idx,
                text,
                value_attr,
                score,
            )
            if score > best_score:
                best_score = score
                best_index = idx
                best_desc = text or value_attr

        if best_index is None:
            raise RuntimeError("선택할 옵션을 결정하지 못했어!")

        if norm_target and best_score < 0.5:
            raise RuntimeError(
                f"'{target_value}'와 비슷한 옵션을 찾지 못했어. (최대 유사도 {best_score:.2f})"
            )

        select = Select(element)
        select.select_by_index(best_index)
        LOGGER.info(
            "셀렉트 입력 성공: index=%s label='%s' (score=%.3f)",
            best_index,
            best_desc,
            best_score,
        )

    def _wait_for_select_ready(self, by, locator_value, initial_signature):
        # 목적: 셀렉트 박스의 옵션이 동적으로 로딩될 때까지 대기
        start = time.time()

        def _condition(driver):
            try:
                elem = driver.find_element(by, locator_value)
            except (WebDriverException, StaleElementReferenceException):
                return False

            if not elem.is_enabled():
                return False

            try:
                opts = elem.find_elements(By.TAG_NAME, "option")
            except (WebDriverException, StaleElementReferenceException):
                return False

            if not opts:
                return False

            signature = self._options_signature(opts)
            if not initial_signature:
                return (elem, opts)
            if signature and signature != initial_signature:
                return (elem, opts)
            if len(opts) > 1 and len(initial_signature) <= 1:
                return (elem, opts)
            if time.time() - start > 1.0:
                return (elem, opts)
            return False

        wait = WebDriverWait(self.driver, 10)
        return wait.until(_condition)

    @staticmethod
    def _options_signature(options):
        # 목적: 옵션 목록의 고유 시그니처를 생성하여 변경 감지
        signature = []
        for opt in options:
            try:
                text = (opt.text or "").strip()
                value_attr = (opt.get_attribute("value") or "").strip()
            except StaleElementReferenceException:
                continue
            signature.append((text, value_attr))
        return tuple(signature)

    @staticmethod
    def _normalize_option(value: str) -> str:
        # 목적: 옵션 값을 정규화하여 유사도 비교 정확도 향상
        if not value:
            return ""
        lowered = value.lower()
        lowered = re.sub(r"\s+", "", lowered)
        lowered = re.sub(r"[^\w가-힣]", "", lowered)
        return lowered

    @staticmethod
    def _match_score(target_norm: str, candidate_norm: str) -> float:
        # 목적: 타깃과 후보 간 유사도 점수 계산 (0.0 ~ 1.0)
        if not candidate_norm:
            return 0.0
        if not target_norm:
            # 빈 타깃이면 옵션 첫 번째를 선택할 수 있도록 낮은 가중치
            return 0.1
        ratio = SequenceMatcher(None, target_norm, candidate_norm).ratio()
        if target_norm in candidate_norm or candidate_norm in target_norm:
            ratio += 0.2
        return min(ratio, 1.0)

    def _log_versions(self) -> None:
        # 목적: 브라우저와 ChromeDriver 버전 호환성 확인 및 로깅
        caps = getattr(self.driver, "capabilities", {}) or {}
        browser_version = caps.get("browserVersion") or caps.get("version") or "unknown"
        chrome_info = caps.get("chrome") or {}
        chromedriver_version_raw = chrome_info.get("chromedriverVersion") or "unknown"
        chromedriver_version = chromedriver_version_raw.split(" ")[0]

        LOGGER.info("브라우저 버전: %s", browser_version)
        LOGGER.info("ChromeDriver 버전: %s", chromedriver_version)

        def _major(ver: str) -> str:
            return ver.split(".")[0] if ver and ver != "unknown" else ""

        if _major(browser_version) and _major(chromedriver_version):
            if _major(browser_version) != _major(chromedriver_version):
                LOGGER.warning(
                    "브라우저와 ChromeDriver 메이저 버전이 달라! 자동 입력에 문제가 생길 수 있어."
                )
            else:
                LOGGER.info("브라우저와 ChromeDriver 메이저 버전이 잘 맞아 떨어졌어.")
