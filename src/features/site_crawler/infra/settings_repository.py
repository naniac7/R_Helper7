"""
목적: 설정 저장/로드
JSON 파일로 설정을 관리한다.
"""

import json
from pathlib import Path
from typing import Dict, Any


class SettingsRepository:
    """
    설정 저장소
    목적: 애플리케이션 설정을 JSON 파일로 관리한다.
    """

    def __init__(self):
        """
        목적: 저장소 초기화
        """
        self.settings_path = self._get_settings_path()

    def _get_settings_path(self) -> Path:
        """
        목적: 설정 파일 경로 반환

        Returns:
            설정 파일 경로
        """
        feature_dir = Path(__file__).parent.parent  # infra 폴더에서 한 단계 위로
        settings_dir = feature_dir / "data"
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / "settings.json"

    def load(self) -> Dict[str, Any]:
        """
        목적: 설정 로드

        Returns:
            설정 딕셔너리 (파일이 없으면 기본값 반환)
        """
        if not self.settings_path.exists():
            default_settings = {"headless_mode": False}
            return default_settings

        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            # 파일이 손상되었거나 읽을 수 없는 경우 기본값 반환
            print(f"설정 파일 로드 실패: {exc}")
            return {"headless_mode": False}

    def save(self, settings: Dict[str, Any]) -> None:
        """
        목적: 설정 저장

        Args:
            settings: 저장할 설정 딕셔너리
        """
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)