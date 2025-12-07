"""
레이어: infra
역할: 크롤링 결과 저장
의존: domain/models
외부: json, pathlib

목적: 크롤링 결과를 JSON 파일로 저장한다.
"""

import json
from pathlib import Path
from src.features.site_crawler.domain.models import CrawlResult


class ResultRepository:
    """
    결과 저장소
    목적: 크롤링 결과를 파일로 저장한다.
    """

    def __init__(self):
        """
        목적: 저장소 초기화
        """
        self.results_dir = self._get_results_dir()

    def _get_results_dir(self) -> Path:
        """
        목적: 결과 저장 디렉토리 경로 반환

        Returns:
            결과 저장 디렉토리 경로
        """
        feature_dir = Path(__file__).parent.parent  # infra 폴더에서 한 단계 위로
        results_dir = feature_dir / "data" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        return results_dir

    def save(self, result: CrawlResult) -> Path:
        """
        목적: 크롤링 결과를 JSON 파일로 저장

        Args:
            result: 저장할 크롤링 결과

        Returns:
            저장된 파일 경로
        """
        # CrawlResult를 딕셔너리로 변환
        result_data = {
            "timestamp": result.timestamp,
            "address": result.address,
            "building": result.building,
            "items": [
                {"title": item.title, "content": item.content} for item in result.items
            ],
        }

        # 파일 경로 생성
        file_path = self.results_dir / "latest_crawl.json"

        # JSON 파일로 저장
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        return file_path