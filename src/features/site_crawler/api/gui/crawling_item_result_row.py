"""
목적: 크롤링 결과를 표시하는 행 위젯

CrawlingItemResultRow: 제목 + 크롤링 결과 내용을 한 행으로 표시
"""

from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QMenu,
)
from PyQt5.QtCore import Qt, pyqtSignal


class CrawlingItemResultRow(QWidget):
    """
    크롤링 항목 위젯 (제목 + 내용)
    목적: 크롤링 결과를 표시하는 행 위젯
    """

    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        """
        생성자
        목적: 제목과 내용 입력 필드를 가진 행 위젯 생성
        """
        super().__init__(parent)

        # 제목 입력 (사용자가 편집 가능)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("제목 입력")

        # 내용 입력 (크롤링 결과 표시용, 읽기 전용)
        self.content_input = QLineEdit()
        self.content_input.setPlaceholderText("크롤링 결과가 여기 표시됩니다")
        self.content_input.setReadOnly(True)

        # 레이아웃 설정 (비율 40% : 60%)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(self.title_input, 4)
        layout.addWidget(self.content_input, 6)

        self.setLayout(layout)

        # 컨텍스트 메뉴 설정
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def get_title(self) -> str:
        """
        목적: 제목 텍스트 반환
        """
        return self.title_input.text().strip()

    def get_content(self) -> str:
        """
        목적: 내용 텍스트 반환
        """
        return self.content_input.text()

    def set_content(self, content: str) -> None:
        """
        목적: 내용 텍스트 설정 (크롤링 결과 표시용)
        """
        self.content_input.setText(content)

    def set_preset(self, title: str) -> None:
        """
        목적: 프리셋 데이터로 제목 설정
        """
        self.title_input.setText(title)

    def _show_context_menu(self, pos) -> None:
        """
        목적: 우클릭 컨텍스트 메뉴 표시 (위로 이동, 아래로 이동, 삭제)
        """
        global_pos = self.mapToGlobal(pos)
        menu = QMenu(self)

        move_up_action = menu.addAction("위로 이동")
        move_down_action = menu.addAction("아래로 이동")
        delete_action = menu.addAction("삭제")

        # 첫 번째 행이면 위로 이동 비활성화
        if self._is_first_row():
            move_up_action.setEnabled(False)

        # 마지막 행이면 아래로 이동 비활성화
        if self._is_last_row():
            move_down_action.setEnabled(False)

        # 메뉴 실행 및 액션 처리
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
        """
        목적: 현재 행이 첫 번째 행인지 확인
        """
        parent = self.parent()
        if not parent or not hasattr(parent, "crawling_rows"):
            return False
        return parent.crawling_rows and parent.crawling_rows[0] is self

    def _is_last_row(self) -> bool:
        """
        목적: 현재 행이 마지막 행인지 확인
        """
        parent = self.parent()
        if not parent or not hasattr(parent, "crawling_rows"):
            return False
        return parent.crawling_rows and parent.crawling_rows[-1] is self
