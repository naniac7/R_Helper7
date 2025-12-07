"""
레이어: app
역할: 모두 전송 유즈케이스
의존: app/fill_field_use_case.py, domain/value_objects.py
외부: 없음

목적: 여러 폼 필드를 순차적으로 채우는 비즈니스 로직
"""
from src.features.oiljang_form_filler.app.fill_field_use_case import FillFieldUseCase
from src.features.oiljang_form_filler.domain.value_objects import (
    FieldMode,
    LocatorType,
)
from src.shared.logging.app_logger import get_logger

logger = get_logger()


class SendAllUseCase:
    """
    모두 전송 유즈케이스

    여러 필드를 순차적으로 채움
    실패 시 즉시 중단
    """

    def __init__(self, fill_field_use_case: FillFieldUseCase):
        """
        유즈케이스 초기화

        Args:
            fill_field_use_case: 단일 필드 채우기 유즈케이스 (DI)
        """
        self._fill_field = fill_field_use_case

    def execute(
        self, fields: list[dict]
    ) -> tuple[int, int, list[str]]:
        """
        모든 필드 순차 전송

        Args:
            fields: 필드 정보 목록
                각 필드는 다음 키를 포함:
                - locator_type: LocatorType
                - locator_value: str
                - input_value: str
                - mode: FieldMode
                - item: str (표시용 이름, 선택)

        Returns:
            tuple[int, int, list[str]]: (성공 수, 스킵 수, 실패 항목 목록)
        """
        success = 0
        skipped = 0
        failures = []

        total = len(fields)
        logger.info("모두 전송 시작: %d건", total)

        for idx, field in enumerate(fields, start=1):
            locator_value = field.get("locator_value", "").strip()
            item_name = field.get("item") or locator_value or f"{idx}번째"

            # locator_value가 비어있으면 스킵
            if not locator_value:
                skipped += 1
                logger.info("스킵 (%d/%d): %s (locator 비어있음)", idx, total, item_name)
                continue

            logger.info("전송 중 (%d/%d): %s", idx, total, item_name)

            # 필드 채우기 시도
            ok, msg = self._fill_field.execute(
                locator_type=field.get("locator_type", LocatorType.ID),
                locator_value=locator_value,
                input_value=field.get("input_value", ""),
                mode=field.get("mode", FieldMode.NORMAL),
            )

            if ok:
                success += 1
                logger.info("성공 (%d/%d): %s", idx, total, item_name)
            else:
                failures.append(item_name)
                logger.warning("실패로 중단 (%d/%d): %s - %s", idx, total, item_name, msg)
                break  # 실패 시 즉시 중단

        logger.info(
            "모두 전송 완료: 성공=%d, 스킵=%d, 실패=%d",
            success, skipped, len(failures)
        )

        return success, skipped, failures
