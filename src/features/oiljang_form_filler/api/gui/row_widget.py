"""
레이어: api/gui
역할: 폼 입력 행 위젯
의존: domain/value_objects.py
외부: PyQt5

목적: 하나의 폼 필드 설정을 입력받는 UI 위젯
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QWidget,
)

from src.features.oiljang_form_filler.domain.value_objects import (
    FieldMode,
    LocatorType,
)

# [문자열-변수명 참조 패턴]
# widget_name 문자열은 실제 위젯 변수명(self.xxx)과 일치해야 함
# 리팩토링 시 변수명 변경하면 이 문자열도 함께 변경할 것
FIELD_CONFIG = [
    {"label": "항목", "widget_name": "item_input", "width": 100},
    {"label": "구분", "widget_name": "mode_combo", "width": 70},
    {"label": "방식", "widget_name": "locator_combo", "width": 100},
    {"label": "이름", "widget_name": "locator_input", "width": 120},
    {"label": "내용", "widget_name": "value_input", "width": 150},
    {"label": "전송", "widget_name": "send_button", "width": 50},
]


class RowWidget(QWidget):
    """
    폼 입력 행 위젯

    한 줄짜리 입력 UI로, 다음 요소를 포함:
    - 항목 이름 입력
    - 입력 모드 선택 (일반/셀렉트)
    - 찾기 방식 선택 (id/name/class 등)
    - 찾을 값 입력
    - 입력할 값 입력
    - 전송 버튼

    Signals:
        submitted: 전송 버튼 클릭 시 발생 (self 전달)
        move_up_requested: 위로 이동 요청 시 발생
        move_down_requested: 아래로 이동 요청 시 발생
        delete_requested: 삭제 요청 시 발생
    """

    submitted = pyqtSignal(object)
    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """UI 초기화"""
        # FIELD_CONFIG에서 너비 참조용 dict 생성
        width_map = {f["widget_name"]: f["width"] for f in FIELD_CONFIG}

        # 항목 이름 입력
        self.item_input = QLineEdit()
        self.item_input.setPlaceholderText("예: 전용면적")
        self.item_input.setFixedWidth(width_map["item_input"])

        # 입력 모드 선택
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("일반", FieldMode.NORMAL)
        self.mode_combo.addItem("셀렉트", FieldMode.SELECT)
        self.mode_combo.setFixedWidth(width_map["mode_combo"])

        # 찾기 방식 선택
        self.locator_combo = QComboBox()
        self.locator_combo.addItem("id", LocatorType.ID)
        self.locator_combo.addItem("name", LocatorType.NAME)
        self.locator_combo.addItem("class name", LocatorType.CLASS_NAME)
        self.locator_combo.addItem("css selector", LocatorType.CSS_SELECTOR)
        self.locator_combo.addItem("xpath", LocatorType.XPATH)
        self.locator_combo.setFixedWidth(width_map["locator_combo"])

        # 찾을 값 입력
        self.locator_input = QLineEdit()
        self.locator_input.setPlaceholderText("floor")
        self.locator_input.setFixedWidth(width_map["locator_input"])

        # 입력할 값 입력
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("1층")
        self.value_input.setFixedWidth(width_map["value_input"])

        # 전송 버튼
        self.send_button = QPushButton("전송")
        self.send_button.clicked.connect(lambda: self.submitted.emit(self))
        self.send_button.setFixedWidth(width_map["send_button"])

        # 레이아웃 구성
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

        # 컨텍스트 메뉴 설정
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def get_item_label(self) -> str:
        """항목 이름 반환"""
        return self.item_input.text().strip()

    def get_mode(self) -> FieldMode:
        """입력 모드 반환"""
        return self.mode_combo.currentData()

    def get_locator_type(self) -> LocatorType:
        """찾기 방식 반환"""
        return self.locator_combo.currentData()

    def get_locator_value(self) -> str:
        """찾을 값 반환"""
        return self.locator_input.text()

    def get_input_value(self) -> str:
        """입력할 값 반환"""
        return self.value_input.text()

    def set_preset(
        self,
        item: str,
        locator_type: LocatorType,
        locator_value: str,
        mode: FieldMode = FieldMode.NORMAL,
    ) -> None:
        """
        프리셋 값으로 설정

        Args:
            item: 항목 이름
            locator_type: 찾기 방식
            locator_value: 찾을 값
            mode: 입력 모드
        """
        self.item_input.setText(item)

        # 모드 설정
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == mode:
                self.mode_combo.setCurrentIndex(i)
                break

        # 찾기 방식 설정
        for i in range(self.locator_combo.count()):
            if self.locator_combo.itemData(i) == locator_type:
                self.locator_combo.setCurrentIndex(i)
                break

        self.locator_input.setText(locator_value)
        self.value_input.clear()

    def _show_context_menu(self, pos) -> None:
        """컨텍스트 메뉴 표시"""
        global_pos = self.mapToGlobal(pos)
        menu = QMenu(self)

        move_up_action = menu.addAction("위로 이동")
        move_down_action = menu.addAction("아래로 이동")
        delete_action = menu.addAction("삭제")

        # 첫 번째/마지막 행이면 이동 비활성화
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
        """첫 번째 행인지 확인"""
        parent = self.parent()
        if not parent or not hasattr(parent, "rows"):
            return False
        return parent.rows and parent.rows[0] is self

    def _is_last_row(self) -> bool:
        """마지막 행인지 확인"""
        parent = self.parent()
        if not parent or not hasattr(parent, "rows"):
            return False
        return parent.rows and parent.rows[-1] is self
