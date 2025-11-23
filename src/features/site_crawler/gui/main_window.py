"""
목적: Site Crawler 메인 윈도우

SiteCrawlerMainWindow: 독립 실행용 QMainWindow
메뉴바와 설정 관리 기능 포함
"""

import json
from pathlib import Path

from PyQt5.QtWidgets import QMainWindow, QAction
from PyQt5.QtCore import Qt

from src.features.site_crawler.gui.site_crawler_widget import SiteCrawlerWidget
from src2.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class SiteCrawlerMainWindow(QMainWindow):
    """
    Site Crawler 메인 윈도우
    목적: 독립 실행 시 메뉴바와 설정 관리 제공
    """

    def __init__(self):
        """
        생성자
        목적: 윈도우 초기화 및 설정 로드
        """
        super().__init__()

        self.settings_path = self._get_settings_path()
        self.settings = self._load_settings()

        # 윈도우 설정
        self.setWindowTitle("Site Crawler")
        self.resize(900, 700)

        # 중앙 위젯 설정
        headless_mode = self.settings.get("headless_mode", False)
        self.crawler_widget = SiteCrawlerWidget(
            parent=self, headless=headless_mode
        )
        self.setCentralWidget(self.crawler_widget)

        # 메뉴바 설정
        self._init_menu_bar()

        LOGGER.info("Site Crawler 메인 윈도우 초기화 완료")

    def _get_settings_path(self) -> Path:
        """
        목적: 설정 파일 경로 반환
        """
        feature_dir = Path(__file__).parent.parent
        settings_dir = feature_dir / "data"
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / "settings.json"

    def _load_settings(self) -> dict:
        """
        목적: 설정 파일 로드
        """
        if not self.settings_path.exists():
            default_settings = {"headless_mode": False}
            self._save_settings(default_settings)
            return default_settings

        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            LOGGER.info("설정 로드 완료: %s", self.settings_path)
            return settings
        except Exception as exc:
            LOGGER.exception("설정 로드 실패", exc_info=exc)
            return {"headless_mode": False}

    def _save_settings(self, settings: dict) -> None:
        """
        목적: 설정 파일 저장
        """
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            LOGGER.info("설정 저장 완료: %s", self.settings_path)
        except Exception as exc:
            LOGGER.exception("설정 저장 실패", exc_info=exc)

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
        self._save_settings(self.settings)

        LOGGER.info("헤드리스 모드 변경: %s", checked)

        # 크롤러 재시작 안내
        if self.crawler_widget and self.crawler_widget.crawler:
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
