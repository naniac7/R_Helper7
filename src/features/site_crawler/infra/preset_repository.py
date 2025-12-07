"""
레이어: infra
역할: 프리셋 저장/로드
의존: 없음
외부: json, pathlib, typing, src.shared.logging.app_logger

목적: 크롤링 행 제목 프리셋을 JSON 파일로 관리한다.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class PresetRepository:
    """
    프리셋 저장소
    목적: 크롤링 행 제목 프리셋을 파일로 관리한다.
    """

    def __init__(self):
        """
        목적: 저장소 초기화
        """
        self.preset_path = self._get_preset_path()

    def _get_preset_path(self) -> Path:
        """
        목적: 프리셋 파일 경로 반환

        Returns:
            프리셋 파일 경로
        """
        feature_dir = Path(__file__).parent.parent  # infra 폴더에서 한 단계 위로
        presets_dir = feature_dir / "data" / "presets"
        presets_dir.mkdir(parents=True, exist_ok=True)
        return presets_dir / "crawl_presets.json"

    def load(self) -> List[Dict[str, Any]]:
        """
        목적: 프리셋 불러오기

        Returns:
            프리셋 데이터 리스트 (파일이 없으면 빈 리스트)
        """
        if not self.preset_path.exists():
            return []

        try:
            with open(self.preset_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            # 파일이 손상되었거나 읽을 수 없는 경우 빈 리스트 반환
            LOGGER.warning("프리셋 파일 로드 실패: %s", exc)
            return []

    def save(self, preset_data: List[Dict[str, Any]]) -> None:
        """
        목적: 프리셋 저장

        Args:
            preset_data: 저장할 프리셋 데이터 리스트
        """
        with open(self.preset_path, "w", encoding="utf-8") as f:
            json.dump(preset_data, f, ensure_ascii=False, indent=2)