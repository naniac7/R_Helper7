"""
목적: 건물 선택 유즈케이스
주소를 선택하고 건물 목록을 이벤트로 발행한다.
"""

from typing import Protocol
from src.features.site_crawler.app.event_bus import EventBus
from src.features.site_crawler.domain.models import Building
from src.features.site_crawler.domain.events import (
    StatusEvent,
    BuildingsFoundEvent,
    ErrorEvent,
)
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class ICrawler(Protocol):
    """크롤러 인터페이스 (필요한 메서드만 정의)"""

    def select_address(self, index: int) -> None:
        """주소 선택"""
        ...

    def get_buildings(self) -> list[Building]:
        """건물 목록 조회"""
        ...


class SelectBuildingUseCase:
    """
    건물 선택 유즈케이스
    목적: 주소를 선택하고 건물 목록을 조회하여 이벤트로 발행한다.
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

    def execute(self, address_index: int) -> None:
        """
        목적: 주소 선택 후 건물 목록 조회

        Args:
            address_index: 선택한 주소의 인덱스
        """
        self.event_bus.publish(StatusEvent(message="건물 목록 조회 중..."))

        try:
            # 2단계 분리: 주소 선택 → 건물 목록 조회
            self.crawler.select_address(address_index)
            buildings = self.crawler.get_buildings()

            LOGGER.info("건물 목록 조회 완료: %d개", len(buildings))
            self.event_bus.publish(BuildingsFoundEvent(buildings=buildings))
        except Exception as exc:
            LOGGER.exception("건물 목록 조회 중 예외 발생", exc_info=exc)
            self.event_bus.publish(ErrorEvent(message=f"건물 목록 조회 실패: {exc}"))