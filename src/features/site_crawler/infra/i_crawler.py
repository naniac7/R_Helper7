"""
목적: 크롤러 인터페이스 정의
Protocol을 사용하여 구현체와 유즈케이스를 분리한다.
"""

from typing import Protocol
from src.features.site_crawler.domain.models import Address, Building, CrawlItem


class ICrawler(Protocol):
    """
    크롤러 인터페이스
    목적: 크롤링 기능의 추상 인터페이스를 정의한다.
    """

    def init_driver(self, headless: bool) -> bool:
        """
        목적: 드라이버 초기화

        Args:
            headless: 헤드리스 모드 사용 여부

        Returns:
            초기화 성공 여부
        """
        ...

    def search_address(self, address: str) -> list[Address]:
        """
        목적: 주소 검색 및 자동완성 목록 반환 (상태 저장 안 함)

        Args:
            address: 검색할 주소

        Returns:
            Address 엔티티 리스트
        """
        ...

    def select_address(self, index: int) -> None:
        """
        목적: 주소 선택만 수행 (건물 목록 조회는 get_buildings 사용)

        Args:
            index: 선택할 주소의 인덱스
        """
        ...

    def get_buildings(self) -> list[Building]:
        """
        목적: 현재 페이지의 건물 목록 파싱 및 반환

        Returns:
            Building 엔티티 리스트
        """
        ...

    def select_building(self, index: int) -> None:
        """
        목적: 건물 선택

        Args:
            index: 선택할 건물의 인덱스
        """
        ...

    def perform_crawling(self) -> list[CrawlItem]:
        """
        목적: 상세 정보 크롤링

        Returns:
            CrawlItem 엔티티 리스트
        """
        ...

    def close(self) -> None:
        """
        목적: 드라이버 종료
        """
        ...