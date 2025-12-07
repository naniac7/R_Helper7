"""
레이어: api/gui
역할: 오일장 폼 자동 채우기 메인 윈도우
의존: app/use_cases, api/gui/row_widget.py, domain
외부: PyQt5

목적: 사용자가 폼 필드를 설정하고 전송하는 메인 UI
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.features.oiljang_form_filler.api.gui.row_widget import (
    FIELD_CONFIG,
    ROW_HORIZONTAL_SPACING,
    ROW_LAYOUT_MARGINS,
    ROW_VERTICAL_SPACING,
    RowWidget,
)
from src.features.oiljang_form_filler.app.fill_field_use_case import FillFieldUseCase
from src.features.oiljang_form_filler.app.load_presets_use_case import LoadPresetsUseCase
from src.features.oiljang_form_filler.app.save_presets_use_case import SavePresetsUseCase
from src.features.oiljang_form_filler.app.send_all_use_case import SendAllUseCase
from src.features.oiljang_form_filler.domain.models import FormPreset
from src.features.oiljang_form_filler.domain.value_objects import FieldMode
from src.shared.logging.app_logger import get_logger

logger = get_logger()


class MainWindow(QWidget):
    """
    오일장 폼 자동 채우기 메인 윈도우

    기능:
    - 폼 필드 행 추가/삭제/이동
    - 개별 필드 전송
    - 모든 필드 일괄 전송
    - 프리셋 저장/불러오기
    """

    STATUS_HISTORY_MAX = 5

    def __init__(
        self,
        fill_field_use_case: FillFieldUseCase,
        save_presets_use_case: SavePresetsUseCase,
        load_presets_use_case: LoadPresetsUseCase,
        send_all_use_case: SendAllUseCase,
    ):
        """
        메인 윈도우 초기화

        Args:
            fill_field_use_case: 단일 필드 채우기 유즈케이스 (DI)
            save_presets_use_case: 프리셋 저장 유즈케이스 (DI)
            load_presets_use_case: 프리셋 불러오기 유즈케이스 (DI)
            send_all_use_case: 모두 전송 유즈케이스 (DI)
        """
        super().__init__()

        self._fill_field = fill_field_use_case
        self._save_presets = save_presets_use_case
        self._load_presets = load_presets_use_case
        self._send_all = send_all_use_case

        self.rows: list[RowWidget] = []
        self.status_history: list[str] = []

        self._init_ui()
        self._load_presets_on_start()

    def _init_ui(self) -> None:
        """UI 초기화"""
        self.setWindowTitle("오일장 폼 자동 채우기")
        self.setFixedWidth(760)

        # 메뉴바
        self.menu_bar = QMenuBar()
        file_menu = self.menu_bar.addMenu("파일")
        save_action = QAction("저장하기", self)
        load_action = QAction("불러오기", self)
        file_menu.addAction(save_action)
        file_menu.addAction(load_action)

        edit_menu = self.menu_bar.addMenu("편집")
        add_action = QAction("추가하기", self)
        edit_menu.addAction(add_action)

        save_action.triggered.connect(self._on_save)
        load_action.triggered.connect(self._on_load)
        add_action.triggered.connect(self._add_row)

        # 헤더 (FIELD_CONFIG 기반으로 라벨 생성)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(*ROW_LAYOUT_MARGINS)
        header_layout.setSpacing(ROW_HORIZONTAL_SPACING)

        for field in FIELD_CONFIG:
            label = QLabel(field["label"])
            label.setFixedWidth(field["width"])
            label.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(label)

        header_layout.addStretch()

        # 행 목록 레이아웃
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setContentsMargins(*ROW_LAYOUT_MARGINS)
        self.rows_layout.setSpacing(ROW_VERTICAL_SPACING)

        # 모두 전송 버튼
        self.send_all_button = QPushButton("모두 전송")
        self.send_all_button.clicked.connect(self._on_send_all)

        # 구분선
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFrameShadow(QFrame.Sunken)

        # 상태 표시 박스
        self.status_box = QPlainTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setMinimumHeight(100)
        self.status_box.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.status_box.setPlaceholderText("상태 메시지가 여기에 표시돼.")

        # 하단 레이아웃
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.send_all_button)
        bottom_layout.addStretch()

        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addLayout(header_layout)
        main_layout.addLayout(self.rows_layout)
        main_layout.addWidget(self.divider)
        main_layout.addWidget(self.status_box)
        main_layout.addLayout(bottom_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _load_presets_on_start(self) -> None:
        """시작 시 프리셋 로드"""
        presets, msg = self._load_presets.execute()

        if presets:
            for preset in presets:
                self._add_row(preset)
            self._update_status(msg)
        else:
            # 프리셋 없으면 빈 행 하나 추가
            self._add_row()
            self._update_status("새로운 항목을 추가해줘.")

    def _add_row(self, preset: FormPreset = None) -> None:
        """
        행 추가

        Args:
            preset: 프리셋 (없으면 빈 행)
        """
        row = RowWidget(self)

        if preset:
            row.set_preset(
                preset.item,
                preset.locator_type,
                preset.locator_value,
                preset.mode,
            )

        # 시그널 연결
        row.submitted.connect(self._on_row_submit)
        row.move_up_requested.connect(self._move_row_up)
        row.move_down_requested.connect(self._move_row_down)
        row.delete_requested.connect(self._confirm_delete_row)

        self.rows.append(row)
        self.rows_layout.addWidget(row)

        logger.info("행 추가됨. 현재 행 수: %d", len(self.rows))

        if preset:
            self._update_status(f"프리셋 '{preset.item}' 추가됨.")
        else:
            self._update_status("새 행 추가됨.")

    def _on_row_submit(self, row: RowWidget) -> None:
        """개별 행 전송 처리"""
        locator_value = row.get_locator_value().strip()
        item_label = row.get_item_label() or locator_value or "(이름 없음)"

        if not locator_value:
            QMessageBox.warning(self, "입력 부족", "이름 칸을 채워줘!")
            self._update_status(f"'{item_label}' 이름 칸이 비어있어.")
            return

        mode = row.get_mode()
        input_value = row.get_input_value()

        if mode == FieldMode.SELECT and not input_value.strip():
            QMessageBox.warning(self, "입력 부족", "셀렉트는 내용이 필요해!")
            self._update_status("셀렉트 항목은 내용 칸을 채워줘.")
            return

        # 전송 실행
        success, msg = self._fill_field.execute(
            locator_type=row.get_locator_type(),
            locator_value=locator_value,
            input_value=input_value,
            mode=mode,
        )

        if success:
            QMessageBox.information(self, "완료", "입력 성공!")
            self._update_status(f"'{item_label}' 입력 완료!")
        else:
            QMessageBox.warning(self, "전송 실패", msg)
            self._update_status(f"'{item_label}' {msg}")

    def _on_send_all(self) -> None:
        """모두 전송 처리"""
        if not self.rows:
            QMessageBox.information(self, "모두 전송", "전송할 항목이 없어!")
            self._update_status("전송할 항목이 없어.")
            return

        # 필드 정보 수집
        fields = []
        for row in self.rows:
            fields.append({
                "item": row.get_item_label(),
                "locator_type": row.get_locator_type(),
                "locator_value": row.get_locator_value(),
                "input_value": row.get_input_value(),
                "mode": row.get_mode(),
            })

        # 전송 실행
        success, skipped, failures = self._send_all.execute(fields)

        # 결과 표시
        total = len(self.rows)
        summary_lines = [
            f"총 행 수: {total}",
            f"성공: {success}",
        ]
        if skipped:
            summary_lines.append(f"스킵: {skipped}")
        if failures:
            summary_lines.append(f"실패: {len(failures)} ({', '.join(failures)})")

        QMessageBox.information(self, "모두 전송", "\n".join(summary_lines))
        self._update_status(" / ".join(summary_lines))

    def _on_save(self) -> None:
        """프리셋 저장"""
        presets = []
        for row in self.rows:
            locator_value = row.get_locator_value().strip()
            if not locator_value:
                continue

            presets.append(FormPreset(
                item=row.get_item_label(),
                locator_type=row.get_locator_type(),
                locator_value=locator_value,
                mode=row.get_mode(),
            ))

        if not presets:
            QMessageBox.information(self, "저장", "저장할 내용이 없어!")
            self._update_status("저장할 항목이 없어.")
            return

        success, msg = self._save_presets.execute(presets)

        if success:
            QMessageBox.information(self, "저장", msg)
        else:
            QMessageBox.warning(self, "저장 실패", msg)

        self._update_status(msg)

    def _on_load(self) -> None:
        """프리셋 불러오기"""
        presets, msg = self._load_presets.execute()

        if not presets:
            QMessageBox.warning(self, "불러오기", msg)
            self._update_status(msg)
            return

        # 기존 행 삭제 후 새로 추가
        self._clear_rows()

        for preset in presets:
            self._add_row(preset)

        if not self.rows:
            self._add_row()

        QMessageBox.information(self, "불러오기", msg)
        self._update_status(msg)

    def _clear_rows(self) -> None:
        """모든 행 삭제"""
        while self.rows:
            row = self.rows.pop()
            row.setParent(None)
            row.deleteLater()

        logger.info("모든 행 삭제됨")

    def _move_row_up(self, row: RowWidget) -> None:
        """행 위로 이동"""
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
        logger.info("행 위로 이동: %s", label)
        self._update_status(f"'{label}' 위로 이동됨.")

    def _move_row_down(self, row: RowWidget) -> None:
        """행 아래로 이동"""
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
        logger.info("행 아래로 이동: %s", label)
        self._update_status(f"'{label}' 아래로 이동됨.")

    def _confirm_delete_row(self, row: RowWidget) -> None:
        """행 삭제 확인"""
        label = row.get_item_label() or row.get_locator_value() or "(이름 없음)"

        reply = QMessageBox.question(
            self,
            "행 삭제",
            f"'{label}'을(를) 삭제할까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self._delete_row(row, label)

    def _delete_row(self, row: RowWidget, label: str) -> None:
        """행 삭제"""
        try:
            index = self.rows.index(row)
        except ValueError:
            return

        self.rows_layout.removeWidget(row)
        self.rows.pop(index)
        row.setParent(None)
        row.deleteLater()

        logger.info("행 삭제됨: %s", label)
        self._update_status(f"'{label}' 삭제됨.")

        # 모든 행이 삭제되면 빈 행 추가
        if not self.rows:
            self._add_row()

    def _update_status(self, message: str) -> None:
        """상태 메시지 업데이트"""
        text = message.strip()
        if not text:
            return

        self.status_history.append(text)

        # 최대 개수 유지
        if len(self.status_history) > self.STATUS_HISTORY_MAX:
            self.status_history = self.status_history[-self.STATUS_HISTORY_MAX:]

        display = "\n".join(self.status_history)
        self.status_box.setPlainText(display)

        # 스크롤 맨 아래로
        cursor = self.status_box.textCursor()
        cursor.movePosition(cursor.End)
        self.status_box.setTextCursor(cursor)
