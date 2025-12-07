"""
레이어: app
역할: 크롤링 결과 저장 유즈케이스
의존: domain/models
외부: pathlib, typing, src.shared.logging.app_logger

목적: 크롤링 결과를 JSON 파일로 저장한다.
"""

from pathlib import Path
from typing import Protocol
from src.features.site_crawler.domain.models import CrawlResult
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class IResultRepository(Protocol):
    """결과 저장소 인터페이스"""

    def save(self, result: CrawlResult) -> Path:
        """결과 저장"""
        ...


class SaveResultUseCase:
    """
    결과 저장 유즈케이스
    목적: 크롤링 결과를 파일로 저장한다.
    """

    def __init__(self, result_repo: IResultRepository):
        """
        목적: 유즈케이스 초기화

        Args:
            result_repo: 결과 저장소
        """
        self.result_repo = result_repo

    def execute(self, result: CrawlResult) -> Path:
        """
        목적: 크롤링 결과 저장

        Args:
            result: 저장할 크롤링 결과

        Returns:
            저장된 파일 경로
        """
        file_path = self.result_repo.save(result)
        LOGGER.info("크롤링 결과 저장 완료: %s", file_path)
        return file_path