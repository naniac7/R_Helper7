"""
목적: Site Crawler 핵심 UI 위젯

SiteCrawlerWidget: 크롤러 UI 로직을 담당하는 QWidget
독립적으로 사용 가능하며, 다른 윈도우에 임베딩 가능
"""

import json
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QComboBox,
    QScrollArea,
    QPlainTextEdit,
    QLabel,
    QApplication,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

from src.features.site_crawler.core.site_crawler import SiteCrawler
from src.features.site_crawler.gui.widgets import CrawlingRowWidget
from src2.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class SiteCrawlerWidget(QWidget):
    """
    Site Crawler UI 위젯
    목적: 크롤러와 UI를 콜백 패턴으로 연결하여 독립적인 크롤링 인터페이스 제공
    """

    def __init__(self, parent=None, headless: bool = False):
        """
        생성자
        목적: UI 초기화 및 크롤러 인스턴스 생성

        Args:
            parent: 부모 위젯
            headless: 헤드리스 모드 사용 여부
        """
        super().__init__(parent)

        self.headless_mode = headless
        self.crawling_rows: List[CrawlingRowWidget] = []
        self.console_history: List[str] = []

        # UI 초기화
        self._init_ui()

        # 크롤러 인스턴스 생성 (콜백 연결)
        self.crawler = SiteCrawler(
            on_status=self._on_crawler_status,
            on_addresses_found=self._on_addresses_found,
            on_buildings_found=self._on_buildings_found,
            on_complete=self._on_crawling_complete,
            on_error=self._on_crawler_error,
        )

        # 크롤러 초기화
        self.crawler.init_driver(headless=self.headless_mode)

    def _init_ui(self) -> None:
        """
        목적: UI 레이아웃 및 위젯 초기화
        """
        layout = QVBoxLayout()

        # === 주소 검색 영역 ===
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("주소 검색:"))

        self.address_search_input = QLineEdit()
        self.address_search_input.setPlaceholderText("검색할 주소 입력")
        self.address_search_input.returnPressed.connect(self._handle_search)
        search_layout.addWidget(self.address_search_input, 1)

        self.search_button = QPushButton("검색")
        self.search_button.clicked.connect(self._handle_search)
        search_layout.addWidget(self.search_button)

        layout.addLayout(search_layout)

        # === 주소 선택 영역 ===
        address_select_layout = QHBoxLayout()
        address_select_layout.addWidget(QLabel("주소 선택:"))

        self.address_combo = QComboBox()
        self.address_combo.addItem("주소 선택")
        self.address_combo.currentIndexChanged.connect(self._handle_address_selection)
        address_select_layout.addWidget(self.address_combo, 1)

        layout.addLayout(address_select_layout)

        # === 건물 선택 영역 ===
        building_layout = QHBoxLayout()
        building_layout.addWidget(QLabel("건물 선택:"))

        self.building_combo = QComboBox()
        self.building_combo.addItem("건물 선택")
        self.building_combo.setEnabled(False)
        self.building_combo.currentIndexChanged.connect(self._handle_building_selection)
        building_layout.addWidget(self.building_combo, 1)

        self.refresh_button = QPushButton("다시 가져오기")
        self.refresh_button.setEnabled(False)
        self.refresh_button.clicked.connect(self._handle_refresh_crawl)
        building_layout.addWidget(self.refresh_button)

        layout.addLayout(building_layout)

        # === 크롤링 행 추가 버튼 ===
        row_buttons_layout = QHBoxLayout()
        self.add_row_button = QPushButton("행 추가")
        self.add_row_button.clicked.connect(self._add_crawling_row)
        row_buttons_layout.addWidget(self.add_row_button)

        row_buttons_layout.addStretch()
        layout.addLayout(row_buttons_layout)

        # === 크롤링 행 스크롤 영역 ===
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_content.setLayout(self.scroll_layout)
        scroll_area.setWidget(self.scroll_content)

        layout.addWidget(scroll_area, 1)

        # === 콘솔 영역 ===
        layout.addWidget(QLabel("콘솔:"))
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        layout.addWidget(self.console)

        self.setLayout(layout)

        # 초기 행 3개 추가
        for _ in range(3):
            self._add_crawling_row()

    @contextmanager
    def wait_cursor(self):
        """
        목적: 대기 커서 컨텍스트 매니저
        """
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            yield
        finally:
            QApplication.restoreOverrideCursor()

    def update_status(self, message: str) -> None:
        """
        목적: 콘솔에 상태 메시지 추가 (50개 제한)
        """
        self.console_history.append(message)
        if len(self.console_history) > 50:
            self.console_history = self.console_history[-50:]

        self.console.setPlainText("\n".join(self.console_history))
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )

    def _on_crawler_status(self, message: str) -> None:
        """
        목적: 크롤러 상태 메시지 콜백
        """
        self.update_status(message)

    def _on_crawler_error(self, error_msg: str) -> None:
        """
        목적: 크롤러 에러 메시지 콜백
        """
        self.update_status(f"[에러] {error_msg}")

    def _on_addresses_found(self, addresses: List[Dict[str, str]]) -> None:
        """
        목적: 주소 검색 결과 콜백
        """
        self.address_combo.clear()
        self.address_combo.addItem("주소 선택")

        for addr in addresses:
            self.address_combo.addItem(addr["display"], addr)

        LOGGER.info("주소 콤보박스 업데이트: %d개", len(addresses))

        # 자동으로 콤보박스 펼치기
        if addresses:
            self.address_combo.showPopup()

    def _on_buildings_found(self, buildings: List[Dict[str, Any]]) -> None:
        """
        목적: 건물 목록 콜백
        """
        self.building_combo.clear()

        if not buildings:
            self.building_combo.addItem("건물 없음")
            self.building_combo.setEnabled(False)
            LOGGER.warning("건물 목록이 비어 있음")
            return

        for building in buildings:
            self.building_combo.addItem(building["display"], building)

        self.building_combo.setEnabled(True)
        LOGGER.info("건물 콤보박스 업데이트: %d개", len(buildings))

    def _on_crawling_complete(self, crawled_data: List[Dict[str, str]]) -> None:
        """
        목적: 크롤링 완료 콜백
        """
        # 각 크롤 행의 내용 업데이트 (제목 매칭)
        for crawl_row in self.crawling_rows:
            title = crawl_row.get_title()
            if not title:
                continue

            # 정확히 일치하는 제목 찾기
            found = False
            for data in crawled_data:
                if data["title"] == title:
                    crawl_row.set_content(data["content"])
                    LOGGER.info("크롤 행 '%s' 내용 설정: %s", title, data["content"])
                    found = True
                    break

            if not found:
                crawl_row.set_content("항목 없음")
                LOGGER.warning("크롤 행 '%s': 매칭되는 항목 없음", title)

        # JSON 저장 (선택한 주소와 건물 정보 포함)
        selected_address = ""
        selected_building = ""

        if self.address_combo.currentIndex() > 0:
            addr_data = self.address_combo.currentData()
            if addr_data:
                selected_address = addr_data.get("display", "")

        if self.building_combo.currentIndex() >= 0:
            building_data = self.building_combo.currentData()
            if building_data:
                selected_building = building_data.get("display", "")

        self.crawler.save_results_to_json(
            address=selected_address, building=selected_building
        )

    def _handle_search(self) -> None:
        """
        목적: 주소 검색 버튼 핸들러
        """
        address = self.address_search_input.text().strip()
        if not address:
            self.update_status("검색할 주소를 입력해주세요.")
            return

        with self.wait_cursor():
            self.crawler.search_address(address)

    def _handle_address_selection(self, index: int) -> None:
        """
        목적: 주소 선택 콤보박스 핸들러
        """
        if index <= 0:
            return

        # 크롤러에서 주소 목록 인덱스는 0부터 시작
        # 콤보박스 인덱스는 1부터 시작 ("주소 선택" 항목 제외)
        crawler_index = index - 1

        with self.wait_cursor():
            self.crawler.select_address(crawler_index)

    def _handle_building_selection(self, index: int) -> None:
        """
        목적: 건물 선택 콤보박스 핸들러
        """
        if index < 0 or not self.building_combo.isEnabled():
            return

        # 건물 콤보박스는 "건물 없음" 없이 바로 시작하므로 인덱스 그대로 사용
        with self.wait_cursor():
            self.crawler.select_building(index)

        # 다시 가져오기 버튼 활성화
        self.refresh_button.setEnabled(True)

    def _handle_refresh_crawl(self) -> None:
        """
        목적: 다시 가져오기 버튼 핸들러
        """
        with self.wait_cursor():
            self.crawler.perform_crawling()

    def _add_crawling_row(self) -> None:
        """
        목적: 크롤링 행 추가
        """
        row = CrawlingRowWidget(parent=self.scroll_content)

        # 시그널 연결
        row.move_up_requested.connect(self._move_row_up)
        row.move_down_requested.connect(self._move_row_down)
        row.delete_requested.connect(self._delete_row)

        self.crawling_rows.append(row)
        self.scroll_layout.addWidget(row)

        LOGGER.info("크롤링 행 추가 (총 %d개)", len(self.crawling_rows))

    def _move_row_up(self, row: CrawlingRowWidget) -> None:
        """
        목적: 행을 위로 이동
        """
        try:
            index = self.crawling_rows.index(row)
        except ValueError:
            return

        if index <= 0:
            return

        # 리스트에서 위치 교환
        self.crawling_rows[index], self.crawling_rows[index - 1] = (
            self.crawling_rows[index - 1],
            self.crawling_rows[index],
        )

        # 레이아웃에서 제거 후 재추가
        self.scroll_layout.removeWidget(row)
        self.scroll_layout.insertWidget(index - 1, row)

        LOGGER.info("행 위로 이동: %d → %d", index, index - 1)

    def _move_row_down(self, row: CrawlingRowWidget) -> None:
        """
        목적: 행을 아래로 이동
        """
        try:
            index = self.crawling_rows.index(row)
        except ValueError:
            return

        if index >= len(self.crawling_rows) - 1:
            return

        # 리스트에서 위치 교환
        self.crawling_rows[index], self.crawling_rows[index + 1] = (
            self.crawling_rows[index + 1],
            self.crawling_rows[index],
        )

        # 레이아웃에서 제거 후 재추가
        self.scroll_layout.removeWidget(row)
        self.scroll_layout.insertWidget(index + 1, row)

        LOGGER.info("행 아래로 이동: %d → %d", index, index + 1)

    def _delete_row(self, row: CrawlingRowWidget) -> None:
        """
        목적: 행 삭제
        """
        try:
            index = self.crawling_rows.index(row)
        except ValueError:
            return

        # 리스트와 레이아웃에서 제거
        self.crawling_rows.remove(row)
        self.scroll_layout.removeWidget(row)
        row.deleteLater()

        LOGGER.info("행 삭제 (인덱스: %d, 남은 행: %d개)", index, len(self.crawling_rows))

    def _save_preset(self) -> None:
        """
        목적: 크롤링 행 제목 프리셋 저장
        """
        preset_data = []
        for row in self.crawling_rows:
            title = row.get_title()
            if title:
                preset_data.append({"title": title})

        if not preset_data:
            self.update_status("저장할 제목이 없습니다.")
            return

        try:
            # 프리셋 저장 경로
            feature_dir = Path(__file__).parent.parent
            presets_dir = feature_dir / "data" / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)

            file_path = presets_dir / "crawl_presets.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(preset_data, f, ensure_ascii=False, indent=2)

            LOGGER.info("프리셋 저장 완료: %s (%d개)", file_path, len(preset_data))
            self.update_status(f"프리셋 저장 완료: {len(preset_data)}개 항목")

        except Exception as exc:
            error_msg = f"프리셋 저장 실패: {exc}"
            LOGGER.exception(error_msg)
            self.update_status(error_msg)

    def _load_preset(self) -> None:
        """
        목적: 프리셋 불러오기
        """
        try:
            feature_dir = Path(__file__).parent.parent
            file_path = feature_dir / "data" / "presets" / "crawl_presets.json"

            if not file_path.exists():
                self.update_status("프리셋 파일이 없습니다.")
                return

            with open(file_path, "r", encoding="utf-8") as f:
                preset_data = json.load(f)

            # 기존 행 모두 삭제
            for row in self.crawling_rows[:]:
                self._delete_row(row)

            # 프리셋 데이터로 행 추가
            for item in preset_data:
                self._add_crawling_row()
                row = self.crawling_rows[-1]
                row.set_preset(item["title"])

            LOGGER.info("프리셋 불러오기 완료: %d개 항목", len(preset_data))
            self.update_status(f"프리셋 불러오기 완료: {len(preset_data)}개 항목")

        except Exception as exc:
            error_msg = f"프리셋 불러오기 실패: {exc}"
            LOGGER.exception(error_msg)
            self.update_status(error_msg)

    def closeEvent(self, event) -> None:
        """
        목적: 위젯 종료 시 크롤러 정리
        """
        if self.crawler:
            self.crawler.close()
        event.accept()
