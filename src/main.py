import sys
import os
import json
import time
import re
import logging
from pathlib import Path
from difflib import SequenceMatcher
from contextlib import contextmanager

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QMenuBar,
    QAction,
    QFrame,
    QPlainTextEdit,
    QMenu,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont
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

from shared.logging.app_logger import get_logger
from features.DiscoreCrawler.discore_crawler import DiscoreCrawler

sys.dont_write_bytecode = True

# 애플리케이션 전역 로거 (파일 로깅 전용, UI 콘솔과 분리됨)
LOGGER = get_logger()

DEFAULT_PROFILE_DIR = Path.home() / "Documents" / "chrome-automation-profile"
PROFILE_DIR = Path(os.environ.get("CHROME_AUTOMATION_PROFILE", str(DEFAULT_PROFILE_DIR)))
PRESETS_PATH = PROFILE_DIR / "form_presets.json"
CRAWL_PRESETS_PATH = PROFILE_DIR / "crawl_presets.json"
SETTINGS_PATH = PROFILE_DIR / "settings.json"


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
            raise RuntimeError("요소 기다리는 중에 문제가 생겼어. 로그를 확인해줘!") from exc

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
            except (InvalidElementStateException, StaleElementReferenceException) as exc:
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
        if not value:
            return ""
        lowered = value.lower()
        lowered = re.sub(r"\s+", "", lowered)
        lowered = re.sub(r"[^\w가-힣]", "", lowered)
        return lowered

    @staticmethod
    def _match_score(target_norm: str, candidate_norm: str) -> float:
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


class AddressItemWidget(QWidget):
    """주소 목록 아이템 커스텀 위젯 (메인 주소 + 서브 주소)"""
    def __init__(self, main_address, sub_address, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        # 메인 주소 레이블 (굵게, 검정)
        self.main_label = QLabel(main_address)
        main_font = self.main_label.font()
        main_font.setBold(True)
        self.main_label.setFont(main_font)
        self.main_label.setStyleSheet("color: #000000;")

        # 서브 주소 레이블 (90% 크기, #555555)
        self.sub_label = QLabel(sub_address)
        sub_font = self.sub_label.font()
        base_size = sub_font.pointSize()
        if base_size > 0:
            sub_font.setPointSize(int(base_size * 0.9))
        else:
            # pointSize가 -1인 경우 픽셀 크기 사용
            pixel_size = sub_font.pixelSize()
            if pixel_size > 0:
                sub_font.setPixelSize(int(pixel_size * 0.9))
        self.sub_label.setFont(sub_font)
        self.sub_label.setStyleSheet("color: #555555;")

        layout.addWidget(self.main_label)
        layout.addWidget(self.sub_label)

        self.setLayout(layout)


class CrawlingRowWidget(QWidget):
    """크롤링 항목 위젯 (제목 + 매치 + 내용)"""
    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("제목 입력")

        self.match_combo = QComboBox()
        self.match_combo.addItem("항목 선택...")

        self.content_input = QLineEdit()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 비율 30% 30% 40%
        layout.addWidget(self.title_input, 3)
        layout.addWidget(self.match_combo, 3)
        layout.addWidget(self.content_input, 4)

        self.setLayout(layout)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def get_title(self) -> str:
        return self.title_input.text().strip()

    def get_match_item(self) -> str:
        """선택된 매치 항목의 item 이름 반환"""
        if self.match_combo.currentIndex() == 0:
            return ""
        return self.match_combo.currentText()

    def get_content(self) -> str:
        return self.content_input.text()

    def set_content(self, content: str):
        self.content_input.setText(content)

    def set_preset(self, title: str, match_item: str = ""):
        self.title_input.setText(title)
        if match_item:
            index = self.match_combo.findText(match_item)
            if index >= 0:
                self.match_combo.setCurrentIndex(index)

    def update_match_combo(self, items: list):
        """매치 콤보박스 업데이트 (우측 폼 항목들)"""
        current_selection = self.get_match_item()
        self.match_combo.clear()
        self.match_combo.addItem("항목 선택...")

        for item in items:
            if item:  # 빈 항목은 추가 안 함
                self.match_combo.addItem(item)

        # 기존 선택 복원 시도
        if current_selection:
            index = self.match_combo.findText(current_selection)
            if index >= 0:
                self.match_combo.setCurrentIndex(index)
            else:
                self.match_combo.setCurrentIndex(0)  # 항목이 없으면 초기화

    def _show_context_menu(self, pos):
        global_pos = self.mapToGlobal(pos)
        menu = QMenu(self)

        move_up_action = menu.addAction("위로 이동")
        move_down_action = menu.addAction("아래로 이동")
        delete_action = menu.addAction("삭제")

        if self._is_first_row():
            move_up_action.setEnabled(False)
        if self._is_last_row():
            move_down_action.setEnabled(False)

        action = menu.exec_(global_pos)
        if action is None:
            return
        if action == move_up_action:
            self.move_up_requested.emit(self)
        elif action == move_down_action:
            self.move_down_requested.emit(self)
        elif action == delete_action:
            self.delete_requested.emit(self)

    def _is_first_row(self) -> bool:
        parent = self.parent()
        if not parent or not hasattr(parent, "crawling_rows"):
            return False
        return parent.crawling_rows and parent.crawling_rows[0] is self

    def _is_last_row(self) -> bool:
        parent = self.parent()
        if not parent or not hasattr(parent, "crawling_rows"):
            return False
        return parent.crawling_rows and parent.crawling_rows[-1] is self


class RowWidget(QWidget):
    submitted = pyqtSignal(object)
    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.item_input = QLineEdit()
        self.item_input.setPlaceholderText("예: 전용면적")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("일반", "normal")
        self.mode_combo.addItem("셀렉트", "select")

        self.locator_combo = QComboBox()
        self.locator_combo.addItem("id", "id")
        self.locator_combo.addItem("name", "name")
        self.locator_combo.addItem("class name", "class name")
        self.locator_combo.addItem("css selector", "css selector")
        self.locator_combo.addItem("xpath", "xpath")

        self.locator_input = QLineEdit()
        self.locator_input.setPlaceholderText("floor")

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("1층")

        self.send_button = QPushButton("전송")
        self.send_button.clicked.connect(lambda: self.submitted.emit(self))

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.item_input)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.locator_combo)
        layout.addWidget(self.locator_input)
        layout.addWidget(self.value_input)
        layout.addWidget(self.send_button)

        self.setLayout(layout)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def get_item_label(self) -> str:
        return self.item_input.text().strip()

    def get_mode(self) -> str:
        return self.mode_combo.currentData()

    def get_locator_type(self) -> str:
        return self.locator_combo.currentData()

    def get_locator_value(self) -> str:
        return self.locator_input.text()

    def get_input_value(self) -> str:
        return self.value_input.text()

    def set_preset(
        self,
        item: str,
        locator_type: str,
        locator_value: str,
        mode: str = "normal",
    ) -> None:
        self.item_input.setText(item)
        index_mode = self.mode_combo.findData(mode)
        if index_mode >= 0:
            self.mode_combo.setCurrentIndex(index_mode)
        index = self.locator_combo.findData(locator_type)
        if index >= 0:
            self.locator_combo.setCurrentIndex(index)
        self.locator_input.setText(locator_value)
        self.value_input.clear()

    def _show_context_menu(self, pos):
        global_pos = self.mapToGlobal(pos)
        menu = QMenu(self)

        move_up_action = menu.addAction("위로 이동")
        move_down_action = menu.addAction("아래로 이동")
        delete_action = menu.addAction("삭제")

        if self._is_first_row():
            move_up_action.setEnabled(False)
        if self._is_last_row():
            move_down_action.setEnabled(False)

        action = menu.exec_(global_pos)
        if action is None:
            return
        if action == move_up_action:
            self.move_up_requested.emit(self)
        elif action == move_down_action:
            self.move_down_requested.emit(self)
        elif action == delete_action:
            self.delete_requested.emit(self)

    def _is_first_row(self) -> bool:
        parent = self.parent()
        if not parent or not hasattr(parent, "rows"):
            return False
        return parent.rows and parent.rows[0] is self

    def _is_last_row(self) -> bool:
        parent = self.parent()
        if not parent or not hasattr(parent, "rows"):
            return False
        return parent.rows and parent.rows[-1] is self


class FormFiller(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = None
        self.discore_crawler = None  # disco.re 크롤러 인스턴스
        self.crawler_driver = None  # 하위 호환용 - discore_crawler.crawler_driver를 가리킴
        self.rows = []
        self.crawling_rows = []
        self.crawled_data = []  # 크롤링된 데이터 저장용
        self.output_bottom_console_history = []
        self.headless_mode = True  # 기본값: 헤드리스 모드 ON
        self.setWindowTitle("Chrome 폼 자동 채우기 (테스트)")
        self.setFixedWidth(1100)

        # 설정 파일 로드
        self._load_settings()

        self.menu_bar = QMenuBar()
        file_menu = self.menu_bar.addMenu("파일")
        save_action = QAction("저장하기", self)
        load_action = QAction("불러오기", self)
        file_menu.addAction(save_action)
        file_menu.addAction(load_action)

        edit_menu = self.menu_bar.addMenu("편집")
        add_action = QAction("추가하기", self)
        add_crawl_action = QAction("크롤링 항목 추가", self)
        edit_menu.addAction(add_action)
        edit_menu.addAction(add_crawl_action)

        # 개발자모드 메뉴 추가
        # AI를 위한 주석: 개발자 옵션 - 헤드리스 모드와 디버그 로깅
        dev_menu = self.menu_bar.addMenu("개발자모드")
        self.headless_action = QAction("헤드리스 모드", self)
        self.headless_action.setCheckable(True)
        self.headless_action.setChecked(self.headless_mode)
        self.headless_action.triggered.connect(self._toggle_headless_mode)
        dev_menu.addAction(self.headless_action)

        # 디버그 로깅 옵션 추가
        self.debug_logging_action = QAction("디버그 로깅", self)
        self.debug_logging_action.setCheckable(True)
        self.debug_logging_action.setChecked(False)  # 기본값: OFF
        self.debug_logging_action.triggered.connect(self._toggle_debug_logging)
        dev_menu.addAction(self.debug_logging_action)

        save_action.triggered.connect(lambda: self.save_presets())
        load_action.triggered.connect(lambda: self.load_presets())
        add_action.triggered.connect(self.add_row)
        add_crawl_action.triggered.connect(self.add_crawling_row)

        # 왼쪽 영역: 주소 검색
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("주소 검색")

        self.search_button = QPushButton("검색")
        self.search_button.clicked.connect(self._handle_search)

        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(self.address_input)
        search_input_layout.addWidget(self.search_button)

        # 주소 선택 콤보박스 (QListWidget → QComboBox로 변경)
        # 목적: 공간 절약 + 1줄 표시 (주소1 / 주소2 형식)
        self.crawling_select_area = QComboBox()
        self.crawling_select_area.setMaxVisibleItems(5)  # 펼쳤을 때 5개 항목 표시
        # 플레이스홀더 추가
        self.crawling_select_area.addItem("주소 선택")
        self.crawling_select_area.currentIndexChanged.connect(self._handle_address_click)  # 선택 시그널
        self.address_data_list = []  # data-index 저장용

        # 건물 선택 UI 추가
        building_label = QLabel("건물 선택:")
        self.building_combo = QComboBox()
        self.building_combo.addItem("건물 선택...")
        self.building_combo.setEnabled(False)
        self.building_combo.currentIndexChanged.connect(self._handle_building_selection)
        self.building_list = []  # 건물 데이터 저장용 (원본 인덱스 포함)

        self.refresh_crawl_button = QPushButton("다시 가져오기")
        self.refresh_crawl_button.clicked.connect(self._refresh_crawling)
        self.refresh_crawl_button.setEnabled(False)

        self.apply_match_button = QPushButton("모두 매치")
        self.apply_match_button.clicked.connect(self._apply_all_matches)

        building_layout = QHBoxLayout()
        building_layout.addWidget(building_label)
        building_layout.addWidget(self.building_combo)
        building_layout.addWidget(self.refresh_crawl_button)
        building_layout.addWidget(self.apply_match_button)

        left_divider = QFrame()
        left_divider.setFrameShape(QFrame.HLine)
        left_divider.setFrameShadow(QFrame.Sunken)

        # 크롤링 행 레이아웃과 스크롤 영역
        # AI를 위한 주석: 크롤링 행들을 담을 레이아웃과 스크롤 영역 설정
        self.crawl_rows_layout = QVBoxLayout()
        self.crawl_rows_layout.setSpacing(6)
        self.crawl_rows_layout.addStretch()  # 행들을 위로 밀어올리기 위한 stretch

        # 크롤링 행들을 담을 컨테이너 위젯
        crawl_container = QWidget()
        crawl_container.setLayout(self.crawl_rows_layout)

        # 크롤링 행 스크롤 영역
        self.crawl_scroll_area = QScrollArea()
        self.crawl_scroll_area.setWidget(crawl_container)
        self.crawl_scroll_area.setWidgetResizable(True)
        self.crawl_scroll_area.setMinimumHeight(150)  # 최소 높이 설정
        self.crawl_scroll_area.setMaximumHeight(400)  # 최대 높이 설정
        self.crawl_scroll_area.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        left_layout = QVBoxLayout()
        left_layout.addLayout(search_input_layout)
        left_layout.addWidget(self.crawling_select_area)
        left_layout.addLayout(building_layout)
        left_layout.addWidget(left_divider)
        left_layout.addWidget(self.crawl_scroll_area)

        # 우측 영역: 기존 폼 입력
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(QLabel("항목"))
        header_layout.addWidget(QLabel("구분"))
        header_layout.addWidget(QLabel("방식"))
        header_layout.addWidget(QLabel("이름"))
        header_layout.addWidget(QLabel("내용"))
        header_layout.addStretch()

        # 우측 폼 행 레이아웃과 스크롤 영역
        # AI를 위한 주석: 우측 폼 행들을 담을 레이아웃과 스크롤 영역 설정
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)
        self.rows_layout.addStretch()  # 행들을 위로 밀어올리기 위한 stretch

        # 우측 폼 행들을 담을 컨테이너 위젯
        rows_container = QWidget()
        rows_container.setLayout(self.rows_layout)

        # 우측 폼 행 스크롤 영역
        self.rows_scroll_area = QScrollArea()
        self.rows_scroll_area.setWidget(rows_container)
        self.rows_scroll_area.setWidgetResizable(True)
        self.rows_scroll_area.setMinimumHeight(250)  # 최소 높이 설정
        self.rows_scroll_area.setMaximumHeight(500)  # 최대 높이 설정
        self.rows_scroll_area.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        right_layout = QVBoxLayout()
        right_layout.addLayout(header_layout)
        right_layout.addWidget(self.rows_scroll_area)

        # 좌우 분할 레이아웃 (4:6 비율)
        vertical_divider = QFrame()
        vertical_divider.setFrameShape(QFrame.VLine)
        vertical_divider.setFrameShadow(QFrame.Sunken)

        split_layout = QHBoxLayout()
        split_layout.addLayout(left_layout, 4)
        split_layout.addWidget(vertical_divider)
        split_layout.addLayout(right_layout, 6)

        # 하단 콘솔 및 버튼
        self.send_all_button = QPushButton("모두 전송")
        self.send_all_button.clicked.connect(self.send_all)

        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFrameShadow(QFrame.Sunken)

        self.output_bottom_console = QPlainTextEdit()
        self.output_bottom_console.setReadOnly(True)
        self.output_bottom_console.setMinimumHeight(100)
        self.output_bottom_console.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.output_bottom_console.setPlaceholderText("상태 메시지가 여기에 표시돼.")

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.send_all_button)
        bottom_layout.addStretch()

        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addLayout(split_layout)
        main_layout.addWidget(self.divider)
        main_layout.addWidget(self.output_bottom_console)
        main_layout.addLayout(bottom_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self._connect_driver()

        # disco.re 크롤러 초기화
        self.discore_crawler = DiscoreCrawler(gui_ref=self, headless_mode=self.headless_mode)
        self.discore_crawler.init_crawler_driver()
        self.crawler_driver = self.discore_crawler.crawler_driver  # 하위 호환용

        self.load_presets(silent=True)
        self.load_crawl_presets(silent=True)

    @contextmanager
    def wait_cursor(self):
        """모래시계 커서를 표시하는 Context Manager"""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            yield
        finally:
            QApplication.restoreOverrideCursor()

    def _connect_driver(self):
        try:
            self.controller = ChromeController()
        except RuntimeError as exc:
            LOGGER.exception("초기 드라이버 연결 실패", exc_info=exc)
            QMessageBox.critical(self, "연결 실패", str(exc))
            self.update_status("크롬 연결 실패! 옵션을 다시 확인해줘.")
        else:
            LOGGER.info("드라이버 연결 완료")
            self.update_status("크롬 연결에 성공했어.")

    def _handle_search(self):
        """검색 버튼 클릭 및 주소 입력 핸들러 - DiscoreCrawler 호출"""
        address = self.address_input.text().strip()
        if self.discore_crawler:
            self.discore_crawler.handle_search(address)

    def _handle_address_click(self, index):
        """
        주소 콤보박스 선택 핸들러 - DiscoreCrawler 호출
        목적: 사용자가 선택한 주소를 DiscoreCrawler에 전달

        Args:
            index: 선택된 콤보박스 인덱스 (0은 플레이스홀더이므로 무시)
        """
        # 0번 인덱스는 "주소 선택" 플레이스홀더이므로 무시
        if index <= 0:
            return

        if self.discore_crawler:
            # index - 1: 플레이스홀더를 제외한 실제 주소 인덱스
            self.discore_crawler.handle_address_click(index - 1)

    def _handle_building_selection(self, index):
        """건물 선택 이벤트 처리 - DiscoreCrawler 호출"""
        if self.discore_crawler:
            self.discore_crawler.handle_building_selection(index)

    def add_row(self, preset=None):
        row = RowWidget(self)
        if preset:
            row.set_preset(
                preset.get("item", ""),
                preset.get("locator_type", "id"),
                preset.get("locator_value", ""),
                preset.get("mode", "normal"),
            )
        row.submitted.connect(self._handle_row_submit)
        row.move_up_requested.connect(self._move_row_up)
        row.move_down_requested.connect(self._move_row_down)
        row.delete_requested.connect(self._confirm_delete_row)
        self.rows.append(row)
        # AI를 위한 주석: stretch 앞에 위젯을 추가하기 위해 insertWidget 사용
        # count()-1은 stretch의 위치이므로 그 앞에 추가
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)

        # 크롤 행의 매치 콤보박스 업데이트
        self._update_crawl_match_combos()

        LOGGER.info("새 항목 행 추가. 현재 행 수: %s", len(self.rows))
        if preset:
            self.update_status(f"프리셋 '{preset.get('item', '이름 없음')}' 추가 완료.")
        else:
            self.update_status("새로운 항목 행을 추가했어.")

    def _handle_row_submit(self, row: RowWidget):
        success, error_message = self._perform_submission(row, show_popups=True)
        if success:
            LOGGER.info("전송 버튼 처리 완료")
            label = row.get_item_label() or row.get_locator_value()
            self.update_status(f"'{label}' 입력을 완료했어!")
        else:
            LOGGER.warning("단일 전송 실패: %s", error_message)
            self.update_status(error_message)

    def _perform_submission(self, row: RowWidget, *, show_popups: bool) -> tuple[bool, str]:
        if self.controller is None:
            LOGGER.warning("드라이버 없이 전송 시도")
            message = "크롬 연결이 아직 안 돼 있어!"
            if show_popups:
                QMessageBox.warning(self, "준비 안 됨", message)
            self.update_status(message)
            return False, message

        locator_type = row.get_locator_type()
        locator_value = row.get_locator_value().strip()
        input_value = row.get_input_value()
        mode = row.get_mode()
        item_label = row.get_item_label()
        display_name = item_label or locator_value or "(이름 없음)"

        if item_label:
            LOGGER.info("선택한 항목: %s", item_label)

        if not locator_value:
            message = f"'{display_name}' 이름 칸이 비어 있어."
            LOGGER.warning(message)
            if show_popups:
                QMessageBox.warning(self, "입력 부족", "이름 칸을 채워줘!")
            return False, message

        if mode == "select" and not input_value.strip():
            message = f"'{display_name}' 셀렉트 항목 내용이 비어 있어."
            LOGGER.warning(message)
            if show_popups:
                QMessageBox.warning(self, "입력 부족", "셀렉트 항목은 내용(선택값)이 필요해!")
            self.update_status("셀렉트 항목을 고르려면 내용 칸을 채워줘.")
            return False, message

        row.locator_input.setText(locator_value)

        last_exception = None
        for attempt in range(1, 4):
            try:
                self.controller.fill_field(locator_type, locator_value, input_value, mode)
            except (ValueError, RuntimeError) as exc:
                last_exception = exc
                LOGGER.exception(
                    "입력 처리 실패 (시도 %s/3, 항목=%s)",
                    attempt,
                    display_name,
                    exc_info=exc,
                )
                time.sleep(1)
            else:
                if show_popups:
                    QMessageBox.information(self, "완료!", "값 넣기 성공했어 🙌")
                success_msg = f"'{display_name}' 입력 성공!"
                self.update_status(success_msg)
                return True, success_msg

        error_message = f"'{display_name}' 입력 실패: {last_exception}"
        self.update_status(error_message)
        if show_popups:
            QMessageBox.warning(self, "전송 실패", error_message)
        return False, error_message

    def save_presets(self):
        entries = []
        for row in self.rows:
            item = row.get_item_label()
            mode = row.get_mode()
            locator_type = row.get_locator_type()
            locator_value = row.get_locator_value().strip()
            if not locator_value:
                continue
            entries.append(
                {
                    "item": item,
                    "mode": mode,
                    "locator_type": locator_type,
                    "locator_value": locator_value,
                }
            )

        if not entries:
            QMessageBox.information(self, "저장", "저장할 내용이 없어!")
            self.update_status("저장할 항목이 없어서 넘어갔어.")
            return

        try:
            PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with PRESETS_PATH.open("w", encoding="utf-8") as fp:
                json.dump(entries, fp, ensure_ascii=False, indent=2)
            LOGGER.info("프리셋 저장 완료: %s", PRESETS_PATH)

            # 크롤 프리셋도 함께 저장
            self.save_crawl_presets()

            QMessageBox.information(self, "저장", "프리셋 저장 완료!")
            self.update_status(f"프리셋 {len(entries)}건을 저장했어.")
        except OSError as exc:
            LOGGER.exception("프리셋 저장 실패", exc_info=exc)
            QMessageBox.warning(self, "저장 실패", f"저장 중 오류가 났어: {exc}")
            self.update_status("프리셋 저장 중 오류가 발생했어.")

    def load_presets(self, silent: bool = False):
        if not PRESETS_PATH.exists():
            if not silent:
                QMessageBox.warning(self, "불러오기", "불러올 파일이 없어!")
            LOGGER.info("프리셋 파일이 없어 기본 행으로 초기화")
            self._clear_rows()
            self.add_row()
            self.update_status("프리셋 파일이 없어 기본 행을 준비했어.")
            return

        try:
            with PRESETS_PATH.open("r", encoding="utf-8") as fp:
                entries = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.exception("프리셋 불러오기 실패", exc_info=exc)
            if not silent:
                QMessageBox.warning(self, "불러오기 실패", f"불러오다 오류가 났어: {exc}")
            self.update_status("프리셋 불러오다가 오류가 났어.")
            return

        self._clear_rows()
        for entry in entries:
            self.add_row(entry)

        if not self.rows:
            self.add_row()

        LOGGER.info("프리셋 불러오기 완료. 행 수: %s", len(self.rows))
        if not silent:
            QMessageBox.information(self, "불러오기", "프리셋 불러오기 완료!")
        self.update_status(f"프리셋 {len(self.rows)}건을 불러왔어.")

    def _clear_rows(self):
        while self.rows:
            row = self.rows.pop()
            row.setParent(None)
            row.deleteLater()
        LOGGER.info("행을 모두 비웠어.")

    def send_all(self):
        if self.controller is None:
            QMessageBox.warning(self, "준비 안 됨", "크롬 연결이 아직 안 돼 있어!")
            self.update_status("크롬 연결이 없어서 모두 전송을 못 했어.")
            return

        total = len(self.rows)
        if total == 0:
            QMessageBox.information(self, "모두 전송", "전송할 항목이 없어!")
            self.update_status("전송할 항목이 없었어.")
            return

        success = 0
        skipped = 0
        failures = []

        for idx, row in enumerate(self.rows, start=1):
            locator_value = row.get_locator_value().strip()
            if not locator_value:
                skipped += 1
                LOGGER.info("행 %s 건너뜀: locator 비어 있음", idx)
                continue

            item_label = row.get_item_label() or f"{idx}번째 행"
            ok, error_message = self._perform_submission(row, show_popups=False)
            if ok:
                success += 1
            else:
                failures.append(item_label)
                LOGGER.warning("모두 전송 중단: %s", error_message)
                self.update_status(f"모두 전송 중단: {error_message}")
                break

        summary_lines = []
        summary_lines.append(f"총 행 수: {total}")
        summary_lines.append(f"성공: {success}")
        if skipped:
            summary_lines.append(f"스킵: {skipped}")
        if failures:
            summary_lines.append(f"실패: {len(failures)} ({', '.join(failures)})")

        QMessageBox.information(self, "모두 전송", "\n".join(summary_lines))

        if failures:
            LOGGER.warning("모두 전송 실패 항목: %s", ", ".join(failures))
        self.update_status(" / ".join(summary_lines))

    def update_status(self, message: str):
        text = message.strip()
        if not text:
            return
        self.output_bottom_console_history.append(text)
        if len(self.output_bottom_console_history) > 50:
            self.output_bottom_console_history = self.output_bottom_console_history[-50:]
        display = "\n".join(self.output_bottom_console_history)
        self.output_bottom_console.setPlainText(display)
        cursor = self.output_bottom_console.textCursor()
        cursor.movePosition(cursor.End)
        self.output_bottom_console.setTextCursor(cursor)

    def _move_row_up(self, row: RowWidget):
        try:
            index = self.rows.index(row)
        except ValueError:
            return
        if index == 0:
            return
        self.rows[index], self.rows[index - 1] = self.rows[index - 1], self.rows[index]
        self.rows_layout.removeWidget(row)
        # AI를 위한 주석: stretch가 있으므로 실제 레이아웃 인덱스는 그대로 사용
        self.rows_layout.insertWidget(index - 1, row)
        label = row.get_item_label() or row.get_locator_value() or "(이름 없음)"
        LOGGER.info("행 위로 이동: %s", label)
        self.update_status(f"'{label}' 행을 위로 올렸어.")

    def _move_row_down(self, row: RowWidget):
        try:
            index = self.rows.index(row)
        except ValueError:
            return
        if index == len(self.rows) - 1:
            return
        self.rows[index], self.rows[index + 1] = self.rows[index + 1], self.rows[index]
        self.rows_layout.removeWidget(row)
        self.rows_layout.insertWidget(index + 1, row)
        label = row.get_item_label() or row.get_locator_value() or "(이름 없음)"
        LOGGER.info("행 아래로 이동: %s", label)
        self.update_status(f"'{label}' 행을 아래로 내렸어.")

    def _confirm_delete_row(self, row: RowWidget):
        label = row.get_item_label() or row.get_locator_value() or "(이름 없음)"
        reply = QMessageBox.question(
            self,
            "행 삭제",
            f"정말로 항목 '{label}'을(를) 삭제할까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._delete_row(row, label)

    def _delete_row(self, row: RowWidget, label: str):
        try:
            index = self.rows.index(row)
        except ValueError:
            return
        self.rows_layout.removeWidget(row)
        self.rows.pop(index)
        row.setParent(None)
        row.deleteLater()

        # 크롤 행의 매치 콤보박스 업데이트
        self._update_crawl_match_combos()

        LOGGER.info("행 삭제: %s", label)
        self.update_status(f"'{label}' 행을 삭제했어.")
        if not self.rows:
            self.add_row()

    def _load_settings(self):
        """설정 파일 로드"""
        if SETTINGS_PATH.exists():
            try:
                with SETTINGS_PATH.open("r", encoding="utf-8") as fp:
                    settings = json.load(fp)
                    self.headless_mode = settings.get("headless_mode", True)
                    LOGGER.info("설정 파일 로드 완료: headless_mode=%s", self.headless_mode)
            except (OSError, json.JSONDecodeError) as exc:
                LOGGER.warning("설정 파일 로드 실패: %s", exc)
                self.headless_mode = True  # 기본값
        else:
            # 설정 파일이 없으면 기본값 사용
            self.headless_mode = True
            LOGGER.info("설정 파일이 없어 기본값 사용: headless_mode=True")

    def _save_settings(self):
        """설정 파일 저장"""
        settings = {"headless_mode": self.headless_mode}
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with SETTINGS_PATH.open("w", encoding="utf-8") as fp:
                json.dump(settings, fp, ensure_ascii=False, indent=2)
            LOGGER.info("설정 파일 저장 완료: %s", SETTINGS_PATH)
        except OSError as exc:
            LOGGER.exception("설정 파일 저장 실패", exc_info=exc)
            self.update_status(f"설정 저장 실패: {exc}")

    def _toggle_headless_mode(self):
        """헤드리스 모드 토글"""
        self.headless_mode = self.headless_action.isChecked()
        LOGGER.info("헤드리스 모드 변경: %s", self.headless_mode)

        # 설정 저장
        self._save_settings()

        # 크롤러 재시작 메시지
        self.update_status("크롤러를 재시작합니다...")

        with self.wait_cursor():
            # 기존 크롤러 종료
            if self.crawler_driver:
                try:
                    self.crawler_driver.quit()
                    LOGGER.info("기존 크롤러 드라이버 종료 완료")
                except Exception as exc:
                    LOGGER.warning("크롤러 드라이버 종료 중 오류: %s", exc)
                self.crawler_driver = None

            # 새 크롤러 시작
            self.discore_crawler = DiscoreCrawler(gui_ref=self, headless_mode=self.headless_mode)
            self.discore_crawler.init_crawler_driver()
            self.crawler_driver = self.discore_crawler.crawler_driver

            mode_text = "헤드리스" if self.headless_mode else "풀"
            self.update_status(f"{mode_text} 모드로 크롤러가 재시작되었어.")

    def _toggle_debug_logging(self):
        """디버그 로깅 토글"""
        # AI를 위한 주석: DEBUG 레벨로 전환하면 크롤링 시 선택자 정보가 로그에 기록됨
        is_debug = self.debug_logging_action.isChecked()

        if is_debug:
            LOGGER.setLevel(logging.DEBUG)
            LOGGER.info("디버그 로깅 활성화 - DEBUG 레벨 메시지가 표시됩니다")
            self.update_status("디버그 로깅이 활성화되었어. 더 자세한 로그를 확인할 수 있어.")
        else:
            LOGGER.setLevel(logging.INFO)
            LOGGER.info("디버그 로깅 비활성화 - INFO 레벨 메시지만 표시됩니다")
            self.update_status("디버그 로깅이 비활성화되었어.")

        # 현재 로깅 레벨 확인
        current_level = logging.getLevelName(LOGGER.level)
        LOGGER.info("현재 로깅 레벨: %s", current_level)

    def add_crawling_row(self, preset=None):
        """크롤링 행 추가"""
        row = CrawlingRowWidget(self)
        if preset:
            row.set_preset(preset.get("title", ""), preset.get("match_item", ""))

        row.move_up_requested.connect(self._move_crawl_row_up)
        row.move_down_requested.connect(self._move_crawl_row_down)
        row.delete_requested.connect(self._confirm_delete_crawl_row)

        self.crawling_rows.append(row)
        # AI를 위한 주석: stretch 앞에 위젯을 추가하기 위해 insertWidget 사용
        # count()-1은 stretch의 위치이므로 그 앞에 추가
        self.crawl_rows_layout.insertWidget(self.crawl_rows_layout.count() - 1, row)

        # 매치 콤보박스 업데이트
        self._update_crawl_match_combos()

        LOGGER.info("크롤링 행 추가. 현재 행 수: %s", len(self.crawling_rows))
        if preset:
            self.update_status(f"크롤 프리셋 '{preset.get('title', '이름 없음')}' 추가 완료.")
        else:
            self.update_status("새로운 크롤링 행을 추가했어.")

    def _refresh_crawling(self):
        """다시 가져오기 버튼 핸들러 - DiscoreCrawler 호출"""
        if self.discore_crawler:
            self.discore_crawler.refresh_crawling()

    def _apply_all_matches(self):
        """모두 매치 버튼 핸들러"""
        if not self.crawling_rows:
            self.update_status("크롤링 행이 없습니다.")
            return

        matched_count = 0

        for crawl_row in self.crawling_rows:
            match_item = crawl_row.get_match_item()
            content = crawl_row.get_content()

            if not match_item:
                continue

            # 우측 폼 행에서 일치하는 항목 찾기
            for form_row in self.rows:
                if form_row.get_item_label() == match_item:
                    # 내용 덮어쓰기
                    form_row.value_input.setText(content)
                    matched_count += 1
                    LOGGER.info("매치 적용: %s -> %s (값: %s)", crawl_row.get_title(), match_item, content)
                    break

        self.update_status(f"{matched_count}개 항목 매치 완료")
        LOGGER.info("모두 매치 완료: %d개", matched_count)

    def _update_crawl_match_combos(self):
        """모든 크롤 행의 매치 콤보박스 업데이트"""
        # 우측 폼의 항목 이름들 수집
        items = []
        for row in self.rows:
            item_label = row.get_item_label()
            if item_label:
                items.append(item_label)

        # 모든 크롤 행 업데이트
        for crawl_row in self.crawling_rows:
            crawl_row.update_match_combo(items)

    def save_crawl_presets(self):
        """크롤 프리셋 저장"""
        entries = []
        for row in self.crawling_rows:
            title = row.get_title()
            if not title:
                continue
            match_item = row.get_match_item()
            entries.append({
                "title": title,
                "match_item": match_item
            })

        if not entries:
            LOGGER.info("저장할 크롤 항목이 없음")
            return

        try:
            CRAWL_PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with CRAWL_PRESETS_PATH.open("w", encoding="utf-8") as fp:
                json.dump(entries, fp, ensure_ascii=False, indent=2)
            LOGGER.info("크롤 프리셋 저장 완료: %s", CRAWL_PRESETS_PATH)
        except OSError as exc:
            LOGGER.exception("크롤 프리셋 저장 실패", exc_info=exc)

    def load_crawl_presets(self, silent: bool = False):
        """크롤 프리셋 로드"""
        if not CRAWL_PRESETS_PATH.exists():
            if not silent:
                LOGGER.info("크롤 프리셋 파일이 없음")
            # 기본 빈 행 추가
            self.add_crawling_row()
            return

        try:
            with CRAWL_PRESETS_PATH.open("r", encoding="utf-8") as fp:
                entries = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.exception("크롤 프리셋 불러오기 실패", exc_info=exc)
            self.add_crawling_row()
            return

        self._clear_crawl_rows()
        for entry in entries:
            self.add_crawling_row(entry)

        if not self.crawling_rows:
            self.add_crawling_row()

        LOGGER.info("크롤 프리셋 불러오기 완료. 행 수: %s", len(self.crawling_rows))

    def _clear_crawl_rows(self):
        """모든 크롤 행 제거"""
        while self.crawling_rows:
            row = self.crawling_rows.pop()
            row.setParent(None)
            row.deleteLater()
        LOGGER.info("크롤 행을 모두 비웠어.")

    def _move_crawl_row_up(self, row: CrawlingRowWidget):
        try:
            index = self.crawling_rows.index(row)
        except ValueError:
            return
        if index == 0:
            return
        self.crawling_rows[index], self.crawling_rows[index - 1] = self.crawling_rows[index - 1], self.crawling_rows[index]
        self.crawl_rows_layout.removeWidget(row)
        # AI를 위한 주석: stretch가 있으므로 실제 레이아웃 인덱스는 그대로 사용
        self.crawl_rows_layout.insertWidget(index - 1, row)
        LOGGER.info("크롤 행 위로 이동: %s", row.get_title())
        self.update_status(f"'{row.get_title()}' 크롤 행을 위로 올렸어.")

    def _move_crawl_row_down(self, row: CrawlingRowWidget):
        try:
            index = self.crawling_rows.index(row)
        except ValueError:
            return
        if index == len(self.crawling_rows) - 1:
            return
        self.crawling_rows[index], self.crawling_rows[index + 1] = self.crawling_rows[index + 1], self.crawling_rows[index]
        self.crawl_rows_layout.removeWidget(row)
        # AI를 위한 주석: stretch가 있으므로 실제 레이아웃 인덱스는 그대로 사용
        self.crawl_rows_layout.insertWidget(index + 1, row)
        LOGGER.info("크롤 행 아래로 이동: %s", row.get_title())
        self.update_status(f"'{row.get_title()}' 크롤 행을 아래로 내렸어.")

    def _confirm_delete_crawl_row(self, row: CrawlingRowWidget):
        reply = QMessageBox.question(
            self,
            "크롤 행 삭제",
            f"정말로 크롤 항목 '{title}'을(를) 삭제할까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._delete_crawl_row(row, title)

    def _delete_crawl_row(self, row: CrawlingRowWidget, title: str):
        try:
            index = self.crawling_rows.index(row)
        except ValueError:
            return
        self.crawl_rows_layout.removeWidget(row)
        self.crawling_rows.pop(index)
        row.setParent(None)
        row.deleteLater()
        LOGGER.info("크롤 행 삭제: %s", title)
        self.update_status(f"'{title}' 크롤 행을 삭제했어.")

    def closeEvent(self, event):
        """프로그램 종료 시 크롤러 드라이버 정리"""
        if self.crawler_driver:
            try:
                LOGGER.info("크롤러 드라이버 종료 중")
                self.crawler_driver.quit()
                LOGGER.info("크롤러 드라이버 종료 완료")
            except Exception as exc:
                LOGGER.warning("크롤러 드라이버 종료 중 오류: %s", exc)
        event.accept()

def main():
    LOGGER.info("앱 실행 시작")
    app = QApplication(sys.argv)
    window = FormFiller()
    LOGGER.info("UI 초기화 완료, 창 표시")
    window.show()
    exit_code = app.exec_()
    LOGGER.info("앱 종료: %s", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
