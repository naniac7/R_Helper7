"""
레이어: api
역할: Site Crawler 핵심 UI 위젯
의존: api/gui/crawling_item_result_row, domain/models, domain/events, app/*_use_case
외부: json, pathlib, contextlib, datetime, typing, PyQt5, src.shared.logging.app_logger

목적: SiteCrawlerWidget - 크롤러 UI 로직을 담당하는 QWidget
독립적으로 사용 가능하며, 다른 윈도우에 임베딩 가능
"""

import json
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional

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
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor

from src.features.site_crawler.api.gui.crawling_item_result_row import CrawlingItemResultRow
from src.features.site_crawler.domain.models import Address, Building, CrawlItem, CrawlResult
from src.features.site_crawler.domain.events import (
    StatusEvent,
    AddressesFoundEvent,
    BuildingsFoundEvent,
    CrawlingCompleteEvent,
    ErrorEvent,
)
from src.features.site_crawler.app.search_address_use_case import SearchAddressUseCase
from src.features.site_crawler.app.select_building_use_case import (
    SelectBuildingUseCase,
)
from src.features.site_crawler.app.crawl_detail_use_case import CrawlDetailUseCase
from src.features.site_crawler.app.save_preset_use_case import SavePresetUseCase
from src.features.site_crawler.app.load_preset_use_case import LoadPresetUseCase
from src.features.site_crawler.app.save_result_use_case import SaveResultUseCase
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class SiteCrawlerWidget(QWidget):
    """
    Site Crawler UI 위젯
    목적: 유즈케이스와 이벤트 시스템을 통해 크롤링 인터페이스 제공
    """

    def __init__(
        self,
        parent=None,
        search_uc: Optional[SearchAddressUseCase] = None,
        select_building_uc: Optional[SelectBuildingUseCase] = None,
        crawl_uc: Optional[CrawlDetailUseCase] = None,
        save_preset_uc: Optional[SavePresetUseCase] = None,
        load_preset_uc: Optional[LoadPresetUseCase] = None,
        save_result_uc: Optional[SaveResultUseCase] = None,
    ):
        """
        생성자
        목적: UI 초기화 및 유즈케이스 주입

        Args:
            parent: 부모 위젯
            search_uc: 주소 검색 유즈케이스
            select_building_uc: 건물 선택 유즈케이스
            crawl_uc: 상세 크롤링 유즈케이스
            save_preset_uc: 프리셋 저장 유즈케이스
            load_preset_uc: 프리셋 로드 유즈케이스
            save_result_uc: 결과 저장 유즈케이스
        """
        super().__init__(parent)

        # 유즈케이스 주입
        self.search_uc = search_uc
        self.select_building_uc = select_building_uc
        self.crawl_uc = crawl_uc
        self.save_preset_uc = save_preset_uc
        self.load_preset_uc = load_preset_uc
        self.save_result_uc = save_result_uc

        # 내부 상태
        self.crawling_rows: List[CrawlingItemResultRow] = []
        self.console_history: List[str] = []
        self.current_addresses: List[Address] = []
        self.current_buildings: List[Building] = []
        self.selected_address: str = ""
        self.selected_building: str = ""

        # UI 초기화
        self._init_ui()

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

    # === 이벤트 핸들러 (콜백이 아닌 이벤트 객체를 받음) ===

    def on_status_event(self, event: StatusEvent) -> None:
        """
        목적: 상태 메시지 이벤트 핸들러
        """
        self.update_status(event.message)

    def on_error_event(self, event: ErrorEvent) -> None:
        """
        목적: 에러 메시지 이벤트 핸들러
        """
        self.update_status(f"[에러] {event.message}")

    def on_addresses_found_event(self, event: AddressesFoundEvent) -> None:
        """
        목적: 주소 검색 결과 이벤트 핸들러
        """
        self.current_addresses = event.addresses
        self.address_combo.clear()
        self.address_combo.addItem("주소 선택")

        for addr in event.addresses:
            self.address_combo.addItem(addr.display, addr)

        LOGGER.info("주소 콤보박스 업데이트: %d개", len(event.addresses))

        # 자동으로 콤보박스 펼치기
        if event.addresses:
            self.address_combo.showPopup()

    def on_buildings_found_event(self, event: BuildingsFoundEvent) -> None:
        """
        목적: 건물 목록 이벤트 핸들러
        이유: blockSignals로 시그널 차단하여 의도치 않은 크롤링 방지
        """
        self.current_buildings = event.buildings

        # 시그널 차단하여 addItem 시 currentIndexChanged 방지
        self.building_combo.blockSignals(True)
        try:
            self.building_combo.clear()

            if not event.buildings:
                self.building_combo.addItem("건물 없음")
                self.building_combo.setEnabled(False)
                LOGGER.warning("건물 목록이 비어 있음")
                return

            if len(event.buildings) == 1:
                # 건물 1개: 바로 표시 (플레이스홀더 없음)
                building = event.buildings[0]
                self.building_combo.addItem(building.display, building)
                self.building_combo.setCurrentIndex(0)
                self.building_combo.setEnabled(True)
                self.selected_building = building.display
                LOGGER.info("건물 1개 자동 선택: %s", building.display)
            else:
                # 건물 여러 개: 플레이스홀더 추가
                self.building_combo.addItem("건물 선택")
                for building in event.buildings:
                    self.building_combo.addItem(building.display, building)
                self.building_combo.setCurrentIndex(0)
                self.building_combo.setEnabled(True)
                LOGGER.info("건물 콤보박스 업데이트: %d개", len(event.buildings))
        finally:
            # 시그널 복원
            self.building_combo.blockSignals(False)

        # 건물 1개일 때: 비동기로 자동 크롤링
        if len(event.buildings) == 1:
            self.update_status("건물이 1개뿐이라 자동 크롤링합니다")
            # QTimer.singleShot(0)으로 이벤트 루프 끊어서 UI 갱신 보장
            QTimer.singleShot(0, self._auto_crawl_single_building)
        elif len(event.buildings) > 1:
            # 건물 여러 개: 콤보박스 펼치기
            self.building_combo.showPopup()

    def _auto_crawl_single_building(self) -> None:
        """
        목적: 건물 1개일 때 자동 크롤링 실행
        이유: QTimer.singleShot에서 호출되어 이벤트 루프 분리
        """
        if self.crawl_uc and len(self.current_buildings) == 1:
            with self.wait_cursor():
                self.crawl_uc.execute(0)
            self.refresh_button.setEnabled(True)

    def on_crawling_complete_event(self, event: CrawlingCompleteEvent) -> None:
        """
        목적: 크롤링 완료 이벤트 핸들러
        """
        # 각 크롤 행의 내용 업데이트 (제목 매칭)
        for crawl_row in self.crawling_rows:
            title = crawl_row.get_title()
            if not title:
                continue

            # 정확히 일치하는 제목 찾기
            found = False
            for item in event.items:
                if item.title == title:
                    crawl_row.set_content(item.content)
                    LOGGER.info("크롤 행 '%s' 내용 설정: %s", title, item.content)
                    found = True
                    break

            if not found:
                crawl_row.set_content("항목 없음")
                LOGGER.warning("크롤 행 '%s': 매칭되는 항목 없음", title)

        # JSON 저장 (SaveResultUseCase 호출)
        if self.save_result_uc:
            result = CrawlResult(
                timestamp=datetime.now().isoformat(),
                address=self.selected_address,
                building=self.selected_building,
                items=event.items,
            )
            file_path = self.save_result_uc.execute(result)
            self.update_status(f"결과를 저장했어: {file_path.name}")

    # === UI 이벤트 핸들러 ===

    def _handle_search(self) -> None:
        """
        목적: 주소 검색 버튼 핸들러
        """
        address = self.address_search_input.text().strip()
        if not address:
            self.update_status("검색할 주소를 입력해주세요.")
            return

        if self.search_uc:
            with self.wait_cursor():
                self.search_uc.execute(address)

    def _handle_address_selection(self, index: int) -> None:
        """
        목적: 주소 선택 콤보박스 핸들러
        """
        if index <= 0:
            return

        # 선택한 주소 저장
        if self.address_combo.currentData():
            addr = self.address_combo.currentData()
            self.selected_address = addr.display

        # 크롤러에서 주소 목록 인덱스는 0부터 시작
        # 콤보박스 인덱스는 1부터 시작 ("주소 선택" 항목 제외)
        crawler_index = index - 1

        # 인덱스 경계 검증 (규칙23: 인덱스/컬렉션 미검증 금지)
        if crawler_index < 0 or crawler_index >= len(self.current_addresses):
            self.update_status("잘못된 주소 선택입니다.")
            return

        if self.select_building_uc:
            with self.wait_cursor():
                self.select_building_uc.execute(crawler_index)

    def _handle_building_selection(self, index: int) -> None:
        """
        목적: 건물 선택 콤보박스 핸들러
        이유: 건물 여러 개일 때 플레이스홀더(index=0) 제외하고 처리
        """
        if index < 0 or not self.building_combo.isEnabled():
            return

        # 건물 1개일 때는 _auto_crawl_single_building에서 처리하므로 스킵
        if len(self.current_buildings) == 1:
            return

        # 건물 여러 개: 플레이스홀더(index=0) 선택 시 무시
        if index == 0:
            return

        # 선택한 건물 저장
        if self.building_combo.currentData():
            building = self.building_combo.currentData()
            self.selected_building = building.display

        # 플레이스홀더 제외한 실제 건물 인덱스 (index - 1)
        crawler_index = index - 1

        # 인덱스 경계 검증 (규칙23: 인덱스/컬렉션 미검증 금지)
        if crawler_index < 0 or crawler_index >= len(self.current_buildings):
            self.update_status("잘못된 건물 선택입니다.")
            return

        if self.crawl_uc:
            with self.wait_cursor():
                self.crawl_uc.execute(crawler_index)

        # 다시 가져오기 버튼 활성화
        self.refresh_button.setEnabled(True)

    def _handle_refresh_crawl(self) -> None:
        """
        목적: 다시 가져오기 버튼 핸들러
        """
        # 현재 선택된 건물 인덱스로 다시 크롤링
        combo_index = self.building_combo.currentIndex()

        # 건물 1개: 인덱스 그대로 사용
        # 건물 여러 개: 플레이스홀더 제외 (combo_index - 1)
        if len(self.current_buildings) == 1:
            crawler_index = combo_index
        else:
            crawler_index = combo_index - 1

        if crawler_index >= 0 and self.crawl_uc:
            with self.wait_cursor():
                self.crawl_uc.execute(crawler_index)

    def _add_crawling_row(self) -> None:
        """
        목적: 크롤링 행 추가
        """
        row = CrawlingItemResultRow(parent=self.scroll_content)

        # 시그널 연결
        row.move_up_requested.connect(self._move_row_up)
        row.move_down_requested.connect(self._move_row_down)
        row.delete_requested.connect(self._delete_row)

        self.crawling_rows.append(row)
        self.scroll_layout.addWidget(row)

        LOGGER.info("크롤링 행 추가 (총 %d개)", len(self.crawling_rows))

    def _move_row_up(self, row: CrawlingItemResultRow) -> None:
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

    def _move_row_down(self, row: CrawlingItemResultRow) -> None:
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

    def _delete_row(self, row: CrawlingItemResultRow) -> None:
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
        titles = []
        for row in self.crawling_rows:
            title = row.get_title()
            if title:
                titles.append(title)

        if not titles:
            self.update_status("저장할 제목이 없습니다.")
            return

        if self.save_preset_uc:
            try:
                self.save_preset_uc.execute(titles)
                self.update_status(f"프리셋 저장 완료: {len(titles)}개 항목")
            except Exception as exc:
                self.update_status(f"프리셋 저장 실패: {exc}")

    def _load_preset(self) -> None:
        """
        목적: 프리셋 불러오기
        """
        if not self.load_preset_uc:
            self.update_status("프리셋 로드 유즈케이스가 없습니다.")
            return

        try:
            titles = self.load_preset_uc.execute()

            if not titles:
                self.update_status("프리셋이 비어 있습니다.")
                return

            # 기존 행 모두 삭제
            for row in self.crawling_rows[:]:
                self._delete_row(row)

            # 프리셋 데이터로 행 추가
            for title in titles:
                self._add_crawling_row()
                row = self.crawling_rows[-1]
                row.set_preset(title)

            self.update_status(f"프리셋 불러오기 완료: {len(titles)}개 항목")

        except Exception as exc:
            self.update_status(f"프리셋 불러오기 실패: {exc}")

    def closeEvent(self, event) -> None:
        """
        목적: 위젯 종료 시 정리
        """
        # 위젯 종료 시 특별한 정리 필요 없음 (크롤러는 __main__.py에서 관리)
        event.accept()