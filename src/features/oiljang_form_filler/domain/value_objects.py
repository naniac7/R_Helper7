"""
레이어: domain
역할: 폼 필드 관련 값 객체 (Enum) 정의
의존: 없음
외부: 없음

목적: 폼 필드의 찾기 방식과 입력 방식을 타입 안전하게 정의
"""
from enum import Enum


class LocatorType(Enum):
    """
    요소 찾기 방식

    Selenium의 By 클래스에 대응하는 값
    """

    ID = "id"
    NAME = "name"
    CLASS_NAME = "class name"
    CSS_SELECTOR = "css selector"
    XPATH = "xpath"


class FieldMode(Enum):
    """
    필드 입력 방식

    - NORMAL: 일반 텍스트 입력 (input, textarea)
    - SELECT: 드롭다운 선택 (select)
    """

    NORMAL = "normal"
    SELECT = "select"
