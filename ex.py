import sys
import os
import json
import time
import re
import logging
from pathlib import Path
from difflib import SequenceMatcher

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
)
from PyQt5.QtCore import pyqtSignal, Qt
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

sys.dont_write_bytecode = True


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("test_app")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    try:
        handler = logging.FileHandler("test.log", mode="w", encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("로거 초기화 완료")
    return logger


LOGGER = _build_logger()

DEFAULT_PROFILE_DIR = Path.home() / "Documents" / "chrome-automation-profile"
PROFILE_DIR = Path(os.environ.get("CHROME_AUTOMATION_PROFILE", str(DEFAULT_PROFILE_DIR)))
PRESETS_PATH = PROFILE_DIR / "form_presets.json"


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
        self.rows = []
        self.status_history = []
        self.setWindowTitle("Chrome 폼 자동 채우기 (테스트)")
        self.setFixedWidth(760)

        self.menu_bar = QMenuBar()
        file_menu = self.menu_bar.addMenu("파일")
        save_action = QAction("저장하기", self)
        load_action = QAction("불러오기", self)
        file_menu.addAction(save_action)
        file_menu.addAction(load_action)

        edit_menu = self.menu_bar.addMenu("편집")
        add_action = QAction("추가하기", self)
        edit_menu.addAction(add_action)

        save_action.triggered.connect(lambda: self.save_presets())
        load_action.triggered.connect(lambda: self.load_presets())
        add_action.triggered.connect(self.add_row)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(QLabel("항목"))
        header_layout.addWidget(QLabel("구분"))
        header_layout.addWidget(QLabel("방식"))
        header_layout.addWidget(QLabel("이름"))
        header_layout.addWidget(QLabel("내용"))
        header_layout.addStretch()

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)

        self.send_all_button = QPushButton("모두 전송")
        self.send_all_button.clicked.connect(self.send_all)

        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFrameShadow(QFrame.Sunken)

        self.status_box = QPlainTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setMinimumHeight(100)
        self.status_box.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.status_box.setPlaceholderText("상태 메시지가 여기에 표시돼.")

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.send_all_button)
        bottom_layout.addStretch()

        main_layout = QVBoxLayout()
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addLayout(header_layout)
        main_layout.addLayout(self.rows_layout)
        main_layout.addWidget(self.divider)
        main_layout.addWidget(self.status_box)
        main_layout.addLayout(bottom_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self._connect_driver()
        self.load_presets(silent=True)

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
        self.rows_layout.addWidget(row)
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
        self.status_history.append(text)
        if len(self.status_history) > 5:
            self.status_history = self.status_history[-5:]
        display = "\n".join(self.status_history)
        self.status_box.setPlainText(display)
        cursor = self.status_box.textCursor()
        cursor.movePosition(cursor.End)
        self.status_box.setTextCursor(cursor)

    def _move_row_up(self, row: RowWidget):
        try:
            index = self.rows.index(row)
        except ValueError:
            return
        if index == 0:
            return
        self.rows[index], self.rows[index - 1] = self.rows[index - 1], self.rows[index]
        self.rows_layout.removeWidget(row)
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
        LOGGER.info("행 삭제: %s", label)
        self.update_status(f"'{label}' 행을 삭제했어.")
        if not self.rows:
            self.add_row()

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
