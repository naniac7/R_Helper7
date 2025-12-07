"""
레이어: app
역할: 단일 필드 채우기 유즈케이스
의존: infra/form_filler.py, domain/value_objects.py
외부: 없음

목적: 하나의 폼 필드를 채우는 비즈니스 로직 (재시도 포함)
"""
import time

from src.features.oiljang_form_filler.domain.value_objects import (
    FieldMode,
    LocatorType,
)
from src.features.oiljang_form_filler.infra.form_filler import OiljangFormFiller
from src.shared.logging.app_logger import get_logger

logger = get_logger()


class FillFieldUseCase:
    """
    단일 필드 채우기 유즈케이스

    폼 필러를 사용하여 하나의 필드를 채움
    실패 시 최대 3회 재시도
    """

    MAX_RETRY = 3
    RETRY_DELAY = 1  # 초

    def __init__(self, form_filler: OiljangFormFiller):
        """
        유즈케이스 초기화

        Args:
            form_filler: 폼 필러 (DI)
        """
        self._form_filler = form_filler

    def execute(
        self,
        locator_type: LocatorType,
        locator_value: str,
        input_value: str,
        mode: FieldMode = FieldMode.NORMAL,
    ) -> tuple[bool, str]:
        """
        필드 채우기 실행

        Args:
            locator_type: 요소 찾기 방식
            locator_value: 찾을 값
            input_value: 입력할 값
            mode: 입력 방식

        Returns:
            tuple[bool, str]: (성공 여부, 메시지)

        예:
            success, msg = use_case.execute(
                LocatorType.ID, "floor", "1층", FieldMode.SELECT
            )
        """
        last_error = None

        for attempt in range(1, self.MAX_RETRY + 1):
            try:
                self._form_filler.fill_field(
                    locator_type, locator_value, input_value, mode
                )
                logger.info("필드 채우기 성공: %s", locator_value)
                return True, "입력 성공"
            except Exception as e:
                last_error = e
                logger.exception(
                    "필드 채우기 실패 (시도 %s/%s)",
                    attempt, self.MAX_RETRY,
                )
                if attempt < self.MAX_RETRY:
                    time.sleep(self.RETRY_DELAY)

        error_msg = f"입력 실패: {last_error}"
        logger.error(error_msg)
        return False, error_msg
