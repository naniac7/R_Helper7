"""
레이어: infra
역할: 오일장 사이트 폼 필드 채우기 구현
의존: domain/value_objects.py, shared/browser/chrome_controller.py
외부: selenium

목적: Selenium을 사용하여 실제 폼 필드에 값을 입력

사용법:
    from src.shared.browser.chrome_controller import ChromeController
    from src.features.oiljang_form_filler.infra.form_filler import OiljangFormFiller

    controller = ChromeController()
    filler = OiljangFormFiller(controller)
    filler.fill_field(LocatorType.ID, "floor", "1층", FieldMode.SELECT)
"""
import re
import time
from difflib import SequenceMatcher

from selenium.common.exceptions import (
    InvalidElementStateException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from src.features.oiljang_form_filler.domain.value_objects import (
    FieldMode,
    LocatorType,
)
from src.shared.browser.chrome_controller import ChromeController
from src.shared.logging.app_logger import get_logger

logger = get_logger()


class OiljangFormFiller:
    """
    오일장 사이트 전용 폼 채우기

    ChromeController로부터 WebDriver를 받아서 폼 필드를 채움
    """

    # LocatorType을 Selenium By로 매핑
    LOCATOR_MAP = {
        LocatorType.ID: By.ID,
        LocatorType.NAME: By.NAME,
        LocatorType.CLASS_NAME: By.CLASS_NAME,
        LocatorType.CSS_SELECTOR: By.CSS_SELECTOR,
        LocatorType.XPATH: By.XPATH,
    }

    def __init__(self, chrome_controller: ChromeController):
        """
        폼 필러 초기화

        Args:
            chrome_controller: 크롬 컨트롤러 (DI)
        """
        self._controller = chrome_controller
        self._driver = chrome_controller.get_driver()

    def fill_field(
        self,
        locator_type: LocatorType,
        locator_value: str,
        input_value: str,
        mode: FieldMode = FieldMode.NORMAL,
    ) -> None:
        """
        필드 하나 채우기

        Args:
            locator_type: 요소 찾기 방식
            locator_value: 찾을 값
            input_value: 입력할 값
            mode: 입력 방식 (NORMAL 또는 SELECT)

        Raises:
            ValueError: locator_value가 비어있을 때
            RuntimeError: 요소를 찾지 못하거나 입력 실패 시
        """
        logger.info(
            "필드 채우기: mode=%s, %s=%s, 값=%s",
            mode.value,
            locator_type.value,
            locator_value,
            input_value,
        )

        locator_value = locator_value.strip()
        if not locator_value:
            logger.warning("빈 locator_value")
            raise ValueError("찾을 요소 이름이 비어 있어!")

        by = self.LOCATOR_MAP.get(locator_type)
        if by is None:
            raise ValueError(f"지원하지 않는 찾기 방식: {locator_type}")

        # 활성 탭으로 포커스
        self._controller.focus_active_tab()

        # 현재 페이지 정보 로깅
        try:
            logger.info("현재 URL: %s", self._driver.current_url)
            logger.info("현재 제목: %s", self._driver.title)
        except WebDriverException:
            logger.warning("현재 URL/제목을 가져오지 못함")

        # 요소 찾기
        try:
            wait = WebDriverWait(self._driver, 10)
            element = wait.until(EC.presence_of_element_located((by, locator_value)))
        except (NoSuchElementException, TimeoutException) as e:
            logger.exception("요소 찾기 실패", exc_info=e)
            raise RuntimeError(
                f"요소를 못 찾았어: {locator_type.value}='{locator_value}'"
            ) from e
        except Exception as e:
            logger.exception("요소 대기 중 예외", exc_info=e)
            raise RuntimeError("요소 찾는 중 문제 발생") from e

        # 모드에 따라 입력
        if mode == FieldMode.SELECT:
            self._fill_select_field_with_retry(by, locator_value, element, input_value)
        else:
            self._fill_text_field(by, locator_value, input_value)

    def _fill_select_field_with_retry(
        self, by, locator_value: str, element, input_value: str
    ) -> None:
        """
        셀렉트 필드 채우기 (재시도 포함)
        """
        try:
            self._fill_select_field(element, input_value)
            return
        except Exception as e:
            logger.warning("셀렉트 즉시 선택 실패, 재시도: %s", e)

        # 옵션 로딩 대기 후 재시도
        initial_signature = ()
        try:
            initial_options = element.find_elements(By.TAG_NAME, "option")
            initial_signature = self._options_signature(initial_options)
        except WebDriverException:
            pass

        try:
            element, options = self._wait_for_select_ready(
                by, locator_value, initial_signature
            )
        except TimeoutException as e:
            logger.exception("셀렉트 옵션 대기 타임아웃", exc_info=e)
            raise RuntimeError("셀렉트 옵션이 준비되지 않았어!") from e

        self._fill_select_field(element, input_value, options)

    def _fill_text_field(self, by, locator_value: str, input_value: str) -> None:
        """
        텍스트 필드 채우기 (재시도 포함)

        Args:
            by: Selenium By 타입
            locator_value: 찾을 값
            input_value: 입력할 값

        Raises:
            RuntimeError: 3회 재시도 후에도 실패 시
        """
        last_exception = None

        for attempt in range(1, 4):
            try:
                element = self._driver.find_element(by, locator_value)
            except (NoSuchElementException, StaleElementReferenceException) as e:
                last_exception = e
                logger.warning(
                    "텍스트 요소 재탐색 실패 (시도 %s/3): %s", attempt, locator_value
                )
                time.sleep(0.5)
                continue

            # 활성화 상태 확인
            if not element.is_enabled():
                logger.info(
                    "텍스트 요소 비활성화 (시도 %s/3): %s", attempt, locator_value
                )
                time.sleep(0.5)
                continue

            # readonly 확인
            readonly = (element.get_attribute("readonly") or "").lower()
            if readonly in {"true", "readonly"}:
                logger.info(
                    "텍스트 요소 readonly (시도 %s/3): %s", attempt, locator_value
                )
                time.sleep(0.5)
                continue

            # 입력 시도
            try:
                element.clear()
                if input_value:
                    element.send_keys(input_value)
                logger.info("텍스트 입력 성공")
                return
            except (InvalidElementStateException, StaleElementReferenceException) as e:
                last_exception = e
                logger.warning(
                    "텍스트 입력 실패 (시도 %s/3): %s", attempt, e
                )
                time.sleep(0.5)

        raise RuntimeError(f"텍스트 필드 입력 실패: {last_exception}")

    def _fill_select_field(
        self, element, target_value: str, options=None
    ) -> None:
        """
        셀렉트 필드 선택

        유사도 매칭으로 가장 비슷한 옵션 선택

        Args:
            element: select 요소
            target_value: 선택할 값
            options: 옵션 목록 (없으면 자동 조회)

        Raises:
            RuntimeError: select 요소가 아니거나 옵션이 없을 때
        """
        tag = element.tag_name.lower()
        if tag != "select":
            raise RuntimeError("셀렉트 모드인데 <select> 요소가 아님!")

        if options is None:
            options = element.find_elements(By.TAG_NAME, "option")
        if not options:
            raise RuntimeError("선택할 옵션이 없어!")

        target_value = target_value.strip()
        norm_target = self._normalize_option(target_value)

        # 유사도 매칭으로 최적 옵션 찾기
        best_index = None
        best_score = -1.0
        best_desc = ""

        for idx, option in enumerate(options):
            text = option.text.strip()
            value_attr = option.get_attribute("value") or ""
            candidates = [text, value_attr]

            score = max(
                self._match_score(norm_target, self._normalize_option(c))
                for c in candidates
            )

            logger.info(
                "옵션 #%s: text='%s', value='%s', score=%.3f",
                idx, text, value_attr, score
            )

            if score > best_score:
                best_score = score
                best_index = idx
                best_desc = text or value_attr

        if best_index is None:
            raise RuntimeError("선택할 옵션을 결정하지 못함!")

        if norm_target and best_score < 0.5:
            raise RuntimeError(
                f"'{target_value}'와 비슷한 옵션을 못 찾음 (최대 유사도: {best_score:.2f})"
            )

        select = Select(element)
        select.select_by_index(best_index)
        logger.info(
            "셀렉트 선택 성공: index=%s, label='%s', score=%.3f",
            best_index, best_desc, best_score
        )

    def _wait_for_select_ready(self, by, locator_value: str, initial_signature: tuple):
        """
        셀렉트 옵션이 준비될 때까지 대기

        Returns:
            tuple: (element, options)
        """
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

            # 초기 시그니처가 없으면 옵션이 있는 것만으로 OK
            if not initial_signature:
                return (elem, opts)

            # 시그니처가 바뀌었으면 OK
            if signature and signature != initial_signature:
                return (elem, opts)

            # 옵션 개수가 늘었으면 OK
            if len(opts) > 1 and len(initial_signature) <= 1:
                return (elem, opts)

            # 1초 지나면 그냥 OK
            if time.time() - start > 1.0:
                return (elem, opts)

            return False

        wait = WebDriverWait(self._driver, 10)
        return wait.until(_condition)

    @staticmethod
    def _options_signature(options) -> tuple:
        """옵션 목록의 시그니처 생성 (변경 감지용)"""
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
        """옵션 값 정규화 (비교용)"""
        if not value:
            return ""
        lowered = value.lower()
        lowered = re.sub(r"\s+", "", lowered)
        lowered = re.sub(r"[^\w가-힣]", "", lowered)
        return lowered

    @staticmethod
    def _match_score(target_norm: str, candidate_norm: str) -> float:
        """
        두 문자열의 유사도 점수 계산

        Returns:
            float: 0.0 ~ 1.0 사이의 유사도
        """
        if not candidate_norm:
            return 0.0
        if not target_norm:
            # 빈 타깃이면 낮은 가중치 (첫 번째 옵션 선택용)
            return 0.1

        ratio = SequenceMatcher(None, target_norm, candidate_norm).ratio()

        # 부분 문자열 포함 시 보너스
        if target_norm in candidate_norm or candidate_norm in target_norm:
            ratio += 0.2

        return min(ratio, 1.0)
