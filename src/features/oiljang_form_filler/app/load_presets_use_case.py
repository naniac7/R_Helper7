"""
레이어: app
역할: 프리셋 불러오기 유즈케이스
의존: infra/preset_repository.py, domain/models.py
외부: 없음

목적: 파일에서 프리셋 목록을 불러오는 비즈니스 로직
"""
import json

from src.features.oiljang_form_filler.domain.models import FormPreset
from src.features.oiljang_form_filler.infra.preset_repository import PresetRepository
from src.shared.logging.app_logger import get_logger

logger = get_logger()


class LoadPresetsUseCase:
    """
    프리셋 불러오기 유즈케이스

    JSON 파일에서 프리셋 목록 로드
    """

    def __init__(self, repository: PresetRepository):
        """
        유즈케이스 초기화

        Args:
            repository: 프리셋 레포지토리 (DI)
        """
        self._repository = repository

    def execute(self) -> tuple[list[FormPreset], str]:
        """
        프리셋 로드 실행

        Returns:
            tuple[list[FormPreset], str]: (프리셋 목록, 메시지)
        """
        try:
            presets = self._repository.load()

            if not presets:
                msg = "저장된 프리셋이 없어"
                logger.info(msg)
                return [], msg

            msg = f"{len(presets)}건 로드 완료"
            logger.info(msg)
            return presets, msg

        except json.JSONDecodeError as e:
            error_msg = f"프리셋 파일 형식 오류: {e}"
            logger.exception(error_msg, exc_info=e)
            return [], error_msg
        except OSError as e:
            error_msg = f"로드 실패: {e}"
            logger.exception(error_msg, exc_info=e)
            return [], error_msg
