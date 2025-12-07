"""
레이어: app
역할: 프리셋 불러오기 유즈케이스
의존: 없음
외부: typing, src.shared.logging.app_logger

목적: 저장된 프리셋을 불러온다.
"""

from typing import Protocol, List, Dict, Any
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class IPresetRepository(Protocol):
    """프리셋 저장소 인터페이스"""

    def load(self) -> List[Dict[str, Any]]:
        """프리셋 불러오기"""
        ...


class LoadPresetUseCase:
    """
    프리셋 불러오기 유즈케이스
    목적: 저장된 프리셋을 불러와서 제목 리스트로 반환한다.
    """

    def __init__(self, preset_repo: IPresetRepository):
        """
        목적: 유즈케이스 초기화

        Args:
            preset_repo: 프리셋 저장소
        """
        self.preset_repo = preset_repo

    def execute(self) -> List[str]:
        """
        목적: 프리셋 불러오기

        Returns:
            제목 리스트
        """
        preset_data = self.preset_repo.load()

        # 딕셔너리 리스트에서 제목만 추출
        titles = [item["title"] for item in preset_data if "title" in item]

        LOGGER.info("프리셋 불러오기 완료: %d개", len(titles))
        return titles