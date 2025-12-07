"""
목적: 이벤트 발행/구독 시스템
단순 딕셔너리 기반으로 이벤트를 발행하고 핸들러를 호출한다.
이벤트 발행자와 구독자를 느슨하게 연결하여 확장성을 확보한다.
"""

from typing import Callable, Any, Dict, List


class EventBus:
    """
    이벤트 버스
    목적: 이벤트 발행자와 구독자를 느슨하게 연결한다.
    """

    def __init__(self):
        """
        목적: 이벤트 버스 초기화
        """
        self._subscribers: Dict[type, List[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        """
        목적: 이벤트 타입에 대한 핸들러 등록

        Args:
            event_type: 구독할 이벤트 타입 (클래스)
            handler: 이벤트 발생 시 호출될 핸들러 함수
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: Any) -> None:
        """
        목적: 이벤트 발행 및 모든 구독자 호출

        Args:
            event: 발행할 이벤트 객체
        """
        event_type = type(event)
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(event)
                except Exception as exc:
                    # 핸들러 에러가 다른 핸들러 실행을 막지 않도록 한다
                    print(f"이벤트 핸들러 에러: {exc}")