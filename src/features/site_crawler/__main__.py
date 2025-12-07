"""
레이어: api (엔트리 포인트)
역할: Site Crawler feature 독립 실행 및 DI 컨테이너
의존: app/event_bus, app/*_use_case, infra/*, api/gui/main_window, domain/events
외부: sys, PyQt5.QtWidgets, src.shared.logging.app_logger

목적: 모든 의존성을 여기서 조립하고 이벤트 구독을 설정한다.

실행 방법:
    python -m src.features.site_crawler
"""

import sys
from PyQt5.QtWidgets import QApplication

# === 이벤트 시스템 ===
from src.features.site_crawler.app.event_bus import EventBus

# === 인프라 계층 ===
from src.features.site_crawler.infra.selenium_crawler import SeleniumCrawler
from src.features.site_crawler.infra.settings_repository import SettingsRepository
from src.features.site_crawler.infra.preset_repository import PresetRepository
from src.features.site_crawler.infra.result_repository import ResultRepository

# === 유즈케이스 ===
from src.features.site_crawler.app.search_address_use_case import SearchAddressUseCase
from src.features.site_crawler.app.select_building_use_case import (
    SelectBuildingUseCase,
)
from src.features.site_crawler.app.crawl_detail_use_case import CrawlDetailUseCase
from src.features.site_crawler.app.save_preset_use_case import SavePresetUseCase
from src.features.site_crawler.app.load_preset_use_case import LoadPresetUseCase
from src.features.site_crawler.app.save_result_use_case import SaveResultUseCase

# === GUI ===
from src.features.site_crawler.api.gui.main_window import SiteCrawlerMainWindow

# === 이벤트 타입 ===
from src.features.site_crawler.domain.events import (
    StatusEvent,
    AddressesFoundEvent,
    BuildingsFoundEvent,
    CrawlingCompleteEvent,
    ErrorEvent,
)

# === 로거 ===
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


def main():
    """
    목적: Site Crawler 애플리케이션 실행 및 DI 설정
    모든 의존성을 여기서 조립하고 이벤트 구독을 설정한다.
    """
    LOGGER.info("Site Crawler 애플리케이션 시작")

    app = QApplication(sys.argv)
    app.setApplicationName("Site Crawler")

    # === 1. 이벤트 버스 생성 ===
    event_bus = EventBus()

    # === 2. 인프라 계층 생성 ===
    crawler = SeleniumCrawler()
    settings_repo = SettingsRepository()
    preset_repo = PresetRepository()
    result_repo = ResultRepository()

    # === 3. 설정 로드 ===
    settings = settings_repo.load()
    headless_mode = settings.get("headless_mode", False)

    # === 4. 크롤러 초기화 (첫 실행 시 한 번만) ===
    if not crawler.init_driver(headless=headless_mode):
        LOGGER.error("Chrome 드라이버 초기화 실패")
        sys.exit(1)

    # === 5. 유즈케이스 생성 (DI) ===
    search_uc = SearchAddressUseCase(crawler, event_bus)
    select_building_uc = SelectBuildingUseCase(crawler, event_bus)
    crawl_uc = CrawlDetailUseCase(crawler, event_bus)
    save_preset_uc = SavePresetUseCase(preset_repo)
    load_preset_uc = LoadPresetUseCase(preset_repo)
    save_result_uc = SaveResultUseCase(result_repo)

    # === 6. GUI 생성 (유즈케이스 주입) ===
    window = SiteCrawlerMainWindow(
        search_uc=search_uc,
        select_building_uc=select_building_uc,
        crawl_uc=crawl_uc,
        save_preset_uc=save_preset_uc,
        load_preset_uc=load_preset_uc,
        save_result_uc=save_result_uc,
        settings_repo=settings_repo,
    )

    # === 7. 이벤트 구독 설정 (중앙 관리) ===
    # 위젯의 이벤트 핸들러를 이벤트 버스에 등록
    widget = window.crawler_widget
    event_bus.subscribe(StatusEvent, widget.on_status_event)
    event_bus.subscribe(AddressesFoundEvent, widget.on_addresses_found_event)
    event_bus.subscribe(BuildingsFoundEvent, widget.on_buildings_found_event)
    event_bus.subscribe(CrawlingCompleteEvent, widget.on_crawling_complete_event)
    event_bus.subscribe(ErrorEvent, widget.on_error_event)

    LOGGER.info("이벤트 구독 설정 완료")

    # === 8. GUI 표시 ===
    window.show()
    LOGGER.info("Site Crawler 윈도우 표시 완료")

    # === 9. 앱 실행 ===
    exit_code = app.exec_()

    # === 10. 정리 (앱 종료 시 드라이버 삭제) ===
    try:
        crawler.close()
    except Exception as exc:
        LOGGER.warning("크롤러 종료 중 예외: %s", exc)

    LOGGER.info("Site Crawler 애플리케이션 종료 (exit_code=%d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()