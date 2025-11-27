"""
목적: 도메인 이벤트 정의
이벤트는 "무슨 일이 일어났는지"를 나타낸다.
각 이벤트는 발생한 일과 관련 데이터를 담는다.
"""

from dataclasses import dataclass
from src.features.site_crawler.domain.models import Address, Building, CrawlItem


@dataclass
class StatusEvent:
    """
    상태 메시지 이벤트
    목적: 크롤링 진행 상태를 알린다.
    """

    message: str  # 상태 메시지


@dataclass
class AddressesFoundEvent:
    """
    주소 검색 완료 이벤트
    목적: 주소 검색 결과를 알린다.
    """

    addresses: list[Address]  # 검색된 주소 목록


@dataclass
class BuildingsFoundEvent:
    """
    건물 목록 조회 완료 이벤트
    목적: 건물 목록 조회 결과를 알린다.
    """

    buildings: list[Building]  # 조회된 건물 목록


@dataclass
class CrawlingCompleteEvent:
    """
    크롤링 완료 이벤트
    목적: 상세 정보 크롤링 완료를 알린다.
    """

    items: list[CrawlItem]  # 크롤링된 항목 목록


@dataclass
class ErrorEvent:
    """
    에러 발생 이벤트
    목적: 작업 중 에러 발생을 알린다.
    """

    message: str  # 에러 메시지