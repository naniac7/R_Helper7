"""
목적: 프리셋 저장 유즈케이스
크롤링 행 제목을 프리셋으로 저장한다.
"""

from typing import Protocol, List, Dict, Any
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class IPresetRepository(Protocol):
    """프리셋 저장소 인터페이스"""

    def save(self, preset_data: List[Dict[str, Any]]) -> None:
        """프리셋 저장"""
        ...


class SavePresetUseCase:
    """
    프리셋 저장 유즈케이스
    목적: 크롤링 행 제목들을 프리셋으로 저장한다.
    """

    def __init__(self, preset_repo: IPresetRepository):
        """
        목적: 유즈케이스 초기화

        Args:
            preset_repo: 프리셋 저장소
        """
        self.preset_repo = preset_repo

    def execute(self, titles: List[str]) -> None:
        """
        목적: 프리셋 저장

        Args:
            titles: 저장할 제목 리스트
        """
        # 빈 제목은 제외하고 딕셔너리 형태로 변환
        preset_data = [{"title": title} for title in titles if title]

        if not preset_data:
            LOGGER.warning("저장할 프리셋이 없음")
            return

        self.preset_repo.save(preset_data)
        LOGGER.info("프리셋 저장 완료: %d개", len(preset_data))