"""
레이어: app
역할: 주소 검색 유즈케이스
의존: app/event_bus, domain/models, domain/events
외부: typing, src.shared.logging.app_logger

목적: 주소를 검색하고 자동완성 목록을 이벤트로 발행한다.
"""

from typing import Protocol
from src.features.site_crawler.app.event_bus import EventBus
from src.features.site_crawler.domain.models import Address
from src.features.site_crawler.domain.events import (
    StatusEvent,
    AddressesFoundEvent,
    ErrorEvent,
)
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class ICrawler(Protocol):
    """크롤러 인터페이스 (필요한 메서드만 정의)"""

    def search_address(self, address: str) -> list[Address]:
        """주소 검색"""
        ...


class SearchAddressUseCase:
    """
    주소 검색 유즈케이스
    목적: 주소를 검색하고 결과를 이벤트로 발행한다.
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

    def execute(self, address: str) -> None:
        """
        목적: 주소 검색 실행

        Args:
            address: 검색할 주소
        """
        if not address:
            self.event_bus.publish(ErrorEvent(message="검색할 주소를 입력해주세요."))
            return

        self.event_bus.publish(StatusEvent(message=f"주소 검색 중: {address}"))

        try:
            addresses = self.crawler.search_address(address)
            LOGGER.info("주소 검색 완료: %d개", len(addresses))
            self.event_bus.publish(AddressesFoundEvent(addresses=addresses))
        except Exception as exc:
            LOGGER.exception("주소 검색 중 예외 발생", exc_info=exc)
            self.event_bus.publish(ErrorEvent(message=f"주소 검색 실패: {exc}"))