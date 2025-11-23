"""
애플리케이션 로깅 시스템 모듈

목적:
- 애플리케이션 전역에서 사용할 파일 로거 제공
- shared/logging 디렉토리에 app.log 파일로 로그 기록
- 싱글톤 패턴으로 로거 인스턴스 재사용

사용법:
    from src.shared.logging.app_logger import get_logger

    logger = get_logger()
    logger.info("정보 메시지")
    logger.warning("경고 메시지")
    logger.error("에러 메시지")

주의:
- UI 콘솔 로그와는 완전히 분리됨 (파일 로깅 전용)
- 기술 공통 영역(shared)에 위치 (Vertical Slice 규칙 준수)
"""

import logging
from pathlib import Path


# 로깅 시스템의 중앙화된 로그 파일 경로
# shared는 기술 공통 영역으로, 여러 feature에서 재사용 가능한 인프라 코드 위치
# app.log는 app_logger.py와 같은 디렉토리에 생성됨
LOG_FILE = Path(__file__).parent / "app.log"


def get_logger() -> logging.Logger:
    """
    애플리케이션 전역에서 사용할 로거를 반환 (싱글톤 패턴)

    동작:
    - 처음 호출 시: 로거를 생성하고 FileHandler를 설정
    - 이후 호출 시: 기존에 생성된 로거를 재사용 (핸들러 중복 방지)
    - 파일 생성 실패 시 콘솔(StreamHandler)로 폴백

    로그 설정:
    - 레벨: INFO
    - 포맷: "%(asctime)s %(levelname)s %(message)s"
    - 파일 모드: "w" (매 실행마다 덮어쓰기)
    - 인코딩: UTF-8

    Returns:
        logging.Logger: app.log에 기록하는 로거 인스턴스

    Examples:
        >>> logger = get_logger()
        >>> logger.info("애플리케이션 시작")
        >>> logger.warning("경고 발생")
    """
    # 싱글톤 패턴: 이미 초기화된 로거가 있으면 재사용
    logger = logging.getLogger("test_app")

    # 핸들러가 이미 있으면 재사용 (중복 초기화 방지)
    if logger.handlers:
        return logger

    # 로그 레벨 설정 (INFO 이상만 기록)
    logger.setLevel(logging.INFO)

    # 로그 메시지 포맷 설정 (시간, 레벨, 메시지)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    try:
        # 파일 핸들러 생성 (매 실행마다 덮어쓰기 모드)
        # app.log 파일은 app_logger.py와 같은 폴더(shared/logging)에 생성됨
        handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    except OSError:
        # 파일 생성 실패 시 콘솔로 폴백 (권한 문제, 디스크 full 등)
        handler = logging.StreamHandler()

    # 핸들러에 포맷터 적용
    handler.setFormatter(formatter)

    # 로거에 핸들러 추가
    logger.addHandler(handler)

    # 로거 초기화 완료 로그 기록
    logger.info("로거 초기화 완료")

    return logger
