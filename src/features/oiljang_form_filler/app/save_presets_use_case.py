"""
레이어: app
역할: 프리셋 저장 유즈케이스
의존: infra/preset_repository.py, domain/models.py
외부: 없음

목적: 프리셋 목록을 파일로 저장하는 비즈니스 로직
"""
from src.features.oiljang_form_filler.domain.models import FormPreset
from src.features.oiljang_form_filler.infra.preset_repository import PresetRepository
from src.shared.logging.app_logger import get_logger

logger = get_logger()


class SavePresetsUseCase:
    """
    프리셋 저장 유즈케이스

    프리셋 목록을 JSON 파일로 저장
    """

    def __init__(self, repository: PresetRepository):
        """
        유즈케이스 초기화

        Args:
            repository: 프리셋 레포지토리 (DI)
        """
        self._repository = repository

    def execute(self, presets: list[FormPreset]) -> tuple[bool, str]:
        """
        프리셋 저장 실행

        Args:
            presets: 저장할 프리셋 목록

        Returns:
            tuple[bool, str]: (성공 여부, 메시지)
        """
        if not presets:
            logger.info("저장할 프리셋 없음")
            return False, "저장할 프리셋이 없어!"

        try:
            self._repository.save(presets)
            msg = f"{len(presets)}건 저장 완료"
            logger.info(msg)
            return True, msg
        except OSError as e:
            error_msg = f"저장 실패: {e}"
            logger.exception(error_msg, exc_info=e)
            return False, error_msg
