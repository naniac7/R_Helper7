"""
레이어: domain
역할: 폼 프리셋 도메인 모델 정의
의존: domain/value_objects.py
외부: 없음

목적: 프리셋 데이터의 구조를 타입 안전하게 정의
"""
from dataclasses import dataclass

from src.features.oiljang_form_filler.domain.value_objects import (
    FieldMode,
    LocatorType,
)


@dataclass
class FormPreset:
    """
    폼 필드 프리셋 설정

    하나의 폼 필드에 대한 설정을 담는 데이터 클래스

    Attributes:
        item: 항목 이름 (예: "전용면적", "층수")
        locator_type: 요소 찾기 방식 (id, name, class 등)
        locator_value: 찾을 값 (예: "floor", "area")
        mode: 입력 방식 (일반 텍스트 또는 셀렉트)

    예:
        preset = FormPreset(
            item="전용면적",
            locator_type=LocatorType.ID,
            locator_value="floor",
            mode=FieldMode.SELECT,
        )
    """

    item: str
    locator_type: LocatorType
    locator_value: str
    mode: FieldMode = FieldMode.NORMAL

    def to_dict(self) -> dict:
        """
        딕셔너리로 변환 (JSON 저장용)

        Returns:
            dict: 프리셋 정보를 담은 딕셔너리
        """
        return {
            "item": self.item,
            "locator_type": self.locator_type.value,
            "locator_value": self.locator_value,
            "mode": self.mode.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FormPreset":
        """
        딕셔너리에서 생성 (JSON 로드용)

        Args:
            data: 프리셋 정보를 담은 딕셔너리

        Returns:
            FormPreset: 생성된 프리셋 인스턴스
        """
        return cls(
            item=data.get("item", ""),
            locator_type=LocatorType(data.get("locator_type", "id")),
            locator_value=data.get("locator_value", ""),
            mode=FieldMode(data.get("mode", "normal")),
        )
