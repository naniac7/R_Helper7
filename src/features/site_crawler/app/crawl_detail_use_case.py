"""
레이어: app
역할: 상세 정보 크롤링 유즈케이스
의존: app/event_bus, domain/models, domain/events
외부: typing, src.shared.logging.app_logger

목적: 건물을 선택하고 상세 정보를 크롤링하여 이벤트로 발행한다.
"""

from typing import Protocol
from src.features.site_crawler.app.event_bus import EventBus
from src.features.site_crawler.domain.models import CrawlItem
from src.features.site_crawler.domain.events import (
    StatusEvent,
    CrawlingCompleteEvent,
    ErrorEvent,
)
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class ICrawler(Protocol):
    """크롤러 인터페이스 (필요한 메서드만 정의)"""

    def select_building(self, index: int) -> None:
        """건물 선택"""
        ...

    def perform_crawling(self) -> list[CrawlItem]:
        """상세 정보 크롤링"""
        ...


class CrawlDetailUseCase:
    """
    상세 정보 크롤링 유즈케이스
    목적: 건물을 선택하고 상세 정보를 크롤링한다.
    """

    def __init__(self, crawler: ICrawler, event_bus: EventBus):
        """
        목적: 유즈케이스 초기화

        Args:
            crawler: 크롤러 구현체
            event_bus: 이벤트 버스
        """
        self.crawler = crawler
        self.event_bus = event_bus

    def execute(self, building_index: int) -> None:
        """
        목적: 건물 선택 후 상세 정보 크롤링

        Args:
            building_index: 선택한 건물의 인덱스
        """
        self.event_bus.publish(StatusEvent(message="크롤링 시작..."))

        try:
            # 건물 선택
            self.crawler.select_building(building_index)

            # 상세 정보 크롤링
            items = self.crawler.perform_crawling()

            LOGGER.info("크롤링 완료: %d개 항목", len(items))
            self.event_bus.publish(CrawlingCompleteEvent(items=items))
        except Exception as exc:
            LOGGER.exception("크롤링 중 예외 발생", exc_info=exc)
            self.event_bus.publish(ErrorEvent(message=f"크롤링 실패: {exc}"))