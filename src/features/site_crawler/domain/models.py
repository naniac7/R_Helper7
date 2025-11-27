"""
목적: 비즈니스 엔티티 정의
도메인 모델은 외부 의존성 없이 순수 데이터 구조로만 구성한다.
"""

from dataclasses import dataclass


@dataclass
class Address:
    """
    주소 엔티티
    목적: 주소 검색 결과를 표현한다.
    """

    data_index: str  # HTML 요소의 data-index 속성값
    main: str  # 주 주소 (예: 서울시 강남구 테헤란로)
    sub: str  # 부 주소 (예: 역삼동)
    display: str  # 표시용 문자열 (예: 서울시 강남구 테헤란로 / 역삼동)


@dataclass
class Building:
    """
    건물 엔티티
    목적: 건물 목록 항목을 표현한다.
    """

    index: int  # 목록에서의 순서 인덱스
    top: str  # 상단 텍스트 (예: 강남빌딩)
    bottom: str  # 하단 텍스트 (예: 테헤란로 123)
    title: str  # 타이틀 텍스트 (선택적)
    display: str  # 표시용 문자열 (예: 강남빌딩(테헤란로 123))


@dataclass
class CrawlItem:
    """
    크롤링 항목 엔티티
    목적: 크롤링한 개별 정보 항목을 표현한다.
    """

    title: str  # 항목 제목 (예: 전용면적)
    content: str  # 항목 내용 (예: 84.5㎡)


@dataclass
class CrawlResult:
    """
    크롤링 결과 집합
    목적: 완전한 크롤링 결과를 표현한다.
    """

    timestamp: str  # 크롤링 시각 (ISO 8601 형식)
    address: str  # 선택한 주소
    building: str  # 선택한 건물
    items: list[CrawlItem]  # 크롤링 항목 리스트