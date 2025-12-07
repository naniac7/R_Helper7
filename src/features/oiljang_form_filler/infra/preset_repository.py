"""
레이어: infra
역할: 프리셋 JSON 파일 저장/로드
의존: domain/models.py
외부: json

목적: 프리셋 데이터를 JSON 파일로 영속화

사용법:
    from src.features.oiljang_form_filler.infra.preset_repository import PresetRepository

    repo = PresetRepository()
    repo.save(presets)
    loaded = repo.load()
"""
import json
from pathlib import Path

from src.features.oiljang_form_filler.domain.models import FormPreset
from src.shared.logging.app_logger import get_logger

logger = get_logger()


class PresetRepository:
    """
    프리셋 JSON 파일 저장/로드

    기본 경로: feature/data/oiljang_presets.json
    """

    DEFAULT_PATH = Path(__file__).parent.parent / "data" / "oiljang_presets.json"

    def __init__(self, file_path: Path = None):
        """
        프리셋 레포지토리 초기화

        Args:
            file_path: 프리셋 파일 경로 (기본: data/oiljang_presets.json)
        """
        self._path = file_path or self.DEFAULT_PATH

    def save(self, presets: list[FormPreset]) -> None:
        """
        프리셋 목록을 JSON으로 저장

        Args:
            presets: 저장할 프리셋 목록

        Raises:
            OSError: 파일 저장 실패 시
        """
        # data 폴더 생성
        self._path.parent.mkdir(parents=True, exist_ok=True)

        entries = [preset.to_dict() for preset in presets]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

        logger.info("프리셋 저장 완료: %s (%d건)", self._path, len(presets))

    def load(self) -> list[FormPreset]:
        """
        JSON에서 프리셋 목록 로드

        Returns:
            list[FormPreset]: 로드된 프리셋 목록 (파일 없으면 빈 리스트)

        Raises:
            json.JSONDecodeError: JSON 파싱 실패 시
        """
        if not self._path.exists():
            logger.info("프리셋 파일 없음: %s", self._path)
            return []

        with self._path.open("r", encoding="utf-8") as f:
            entries = json.load(f)

        presets = [FormPreset.from_dict(e) for e in entries]
        logger.info("프리셋 로드 완료: %s (%d건)", self._path, len(presets))

        return presets

    def exists(self) -> bool:
        """프리셋 파일 존재 여부"""
        return self._path.exists()
