"""
레이어: api
역할: Site Crawler 메인 윈도우
의존: api/gui/site_crawler_widget, app/*_use_case, infra/settings_repository
외부: json, pathlib, typing, PyQt5

목적: SiteCrawlerMainWindow - 독립 실행용 QMainWindow
메뉴바와 설정 관리 기능 포함
"""

import json
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import QMainWindow, QAction
from PyQt5.QtCore import Qt

from src.features.site_crawler.api.gui.site_crawler_widget import SiteCrawlerWidget
from src.features.site_crawler.app.search_address_use_case import SearchAddressUseCase
from src.features.site_crawler.app.select_building_use_case import (
    SelectBuildingUseCase,
)
from src.features.site_crawler.app.crawl_detail_use_case import CrawlDetailUseCase
from src.features.site_crawler.app.save_preset_use_case import SavePresetUseCase
from src.features.site_crawler.app.load_preset_use_case import LoadPresetUseCase
from src.features.site_crawler.app.save_result_use_case import SaveResultUseCase
from src.features.site_crawler.infra.settings_repository import SettingsRepository
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class SiteCrawlerMainWindow(QMainWindow):
    """
    Site Crawler 메인 윈도우
    목적: 독립 실행 시 메뉴바와 설정 관리 제공
    """

    def __init__(
        self,
        search_uc: Optional[SearchAddressUseCase] = None,
        select_building_uc: Optional[SelectBuildingUseCase] = None,
        crawl_uc: Optional[CrawlDetailUseCase] = None,
        save_preset_uc: Optional[SavePresetUseCase] = None,
        load_preset_uc: Optional[LoadPresetUseCase] = None,
        save_result_uc: Optional[SaveResultUseCase] = None,
        settings_repo: Optional[SettingsRepository] = None,
    ):
        """
        생성자
        목적: 윈도우 초기화 및 유즈케이스 주입

        Args:
            search_uc: 주소 검색 유즈케이스
            select_building_uc: 건물 선택 유즈케이스
            crawl_uc: 상세 크롤링 유즈케이스
            save_preset_uc: 프리셋 저장 유즈케이스
            load_preset_uc: 프리셋 로드 유즈케이스
            save_result_uc: 결과 저장 유즈케이스
            settings_repo: 설정 저장소
        """
        super().__init__()

        # 유즈케이스 및 저장소 주입
        self.settings_repo = settings_repo or SettingsRepository()
        self.settings = self.settings_repo.load()

        # 윈도우 설정
        self.setWindowTitle("Site Crawler")
        self.resize(900, 700)

        # 중앙 위젯 설정 (유즈케이스들을 전달)
        self.crawler_widget = SiteCrawlerWidget(
            parent=self,
            search_uc=search_uc,
            select_building_uc=select_building_uc,
            crawl_uc=crawl_uc,
            save_preset_uc=save_preset_uc,
            load_preset_uc=load_preset_uc,
            save_result_uc=save_result_uc,
        )
        self.setCentralWidget(self.crawler_widget)

        # 메뉴바 설정
        self._init_menu_bar()

        LOGGER.info("Site Crawler 메인 윈도우 초기화 완료")

    def _init_menu_bar(self) -> None:
        """
        목적: 메뉴바 초기화
        """
        menu_bar = self.menuBar()

        # 설정 메뉴
        settings_menu = menu_bar.addMenu("설정")

        # 헤드리스 모드 토글
        self.headless_action = QAction("헤드리스 모드", self)
        self.headless_action.setCheckable(True)
        self.headless_action.setChecked(self.settings.get("headless_mode", False))
        self.headless_action.triggered.connect(self._toggle_headless_mode)
        settings_menu.addAction(self.headless_action)

        # 구분선
        settings_menu.addSeparator()

        # 프리셋 불러오기
        load_preset_action = QAction("프리셋 불러오기", self)
        load_preset_action.triggered.connect(self._load_preset)
        settings_menu.addAction(load_preset_action)

        # 프리셋 저장하기
        save_preset_action = QAction("프리셋 저장하기", self)
        save_preset_action.triggered.connect(self._save_preset)
        settings_menu.addAction(save_preset_action)

        LOGGER.info("메뉴바 초기화 완료")

    def _toggle_headless_mode(self, checked: bool) -> None:
        """
        목적: 헤드리스 모드 토글 핸들러
        """
        self.settings["headless_mode"] = checked
        self.settings_repo.save(self.settings)

        LOGGER.info("헤드리스 모드 변경: %s", checked)

        # 크롤러 재시작 안내
        self.crawler_widget.update_status(
            f"헤드리스 모드가 {'활성화' if checked else '비활성화'}되었습니다. "
            "변경 사항은 다음 실행부터 적용됩니다."
        )

    def _load_preset(self) -> None:
        """
        목적: 프리셋 불러오기 메뉴 핸들러
        """
        if self.crawler_widget:
            self.crawler_widget._load_preset()
            LOGGER.info("메뉴에서 프리셋 불러오기 실행")

    def _save_preset(self) -> None:
        """
        목적: 프리셋 저장하기 메뉴 핸들러
        """
        if self.crawler_widget:
            self.crawler_widget._save_preset()
            LOGGER.info("메뉴에서 프리셋 저장하기 실행")

    def closeEvent(self, event) -> None:
        """
        목적: 윈도우 종료 시 정리
        """
        LOGGER.info("Site Crawler 메인 윈도우 종료")
        event.accept()