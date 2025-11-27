"""
레이어: shared
역할: 애플리케이션 전역 로거 제공 (타임스탬프 기반 파일 로깅 + 로테이션)
의존: 없음
외부: 없음

목적: 여러 feature에서 일관된 로깅을 위해

사용법:
    from src.shared.logging.app_logger import get_logger

    logger = get_logger()
    logger.debug("디버그 메시지")
    logger.info("정보 메시지")
    logger.warning("경고 메시지")
    logger.error("에러 메시지")
    logger.exception("예외 발생")  # 스택트레이스 포함

주의:
- UI 콘솔 로그와는 별개로 파일에만 기록됨
- 실행마다 새 로그 파일 생성 (app_YYYY-MM-DD_HH-MM-SS.log)
- 최대 5개 파일 유지, 초과 시 가장 오래된 파일 자동 삭제
"""

import logging
from datetime import datetime
from pathlib import Path


# 로그 파일 저장 경로: shared/logging/logs/
LOGS_DIR = Path(__file__).parent / "logs"

# 로테이션 설정: 최대 유지할 로그 파일 개수
MAX_LOG_FILES = 5

# 로그 포맷: CLAUDE.md 19번 규칙 준수
LOG_FORMAT = "%(asctime)s %(levelname)s [%(pathname)s:%(lineno)d %(funcName)s] %(message)s"


def _cleanup_old_logs() -> None:
    """
    오래된 로그 파일 삭제 (최대 MAX_LOG_FILES개 유지)

    동작:
    - logs 폴더 내 app_*.log 파일을 수정 시간 기준 정렬
    - MAX_LOG_FILES개 초과 시 오래된 파일부터 삭제
    """
    if not LOGS_DIR.exists():
        return

    # app_*.log 패턴의 파일만 수집
    log_files = sorted(
        LOGS_DIR.glob("app_*.log"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,  # 최신 파일이 앞에 오도록
    )

    # MAX_LOG_FILES개 초과 시 오래된 파일 삭제
    for old_file in log_files[MAX_LOG_FILES:]:
        old_file.unlink()


def _create_log_file_path() -> Path:
    """
    타임스탬프 기반 로그 파일 경로 생성

    Returns:
        Path: app_YYYY-MM-DD_HH-MM-SS.log 형식의 파일 경로

    예: app_2025-11-27_14-30-25.log
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return LOGS_DIR / f"app_{timestamp}.log"


def get_logger() -> logging.Logger:
    """
    애플리케이션 전역에서 사용할 로거를 반환 (싱글톤 패턴)

    동작:
    - 처음 호출 시: logs 폴더 생성, 오래된 로그 정리, 새 로그 파일 생성
    - 이후 호출 시: 기존 로거 재사용 (핸들러 중복 방지)
    - 파일 생성 실패 시 콘솔(StreamHandler)로 폴백

    로그 설정:
    - 레벨: DEBUG (모든 레벨 기록)
    - 포맷: "%(asctime)s %(levelname)s [%(pathname)s:%(lineno)d %(funcName)s] %(message)s"
    - 파일명: app_YYYY-MM-DD_HH-MM-SS.log
    - 인코딩: UTF-8

    Returns:
        logging.Logger: 파일에 기록하는 로거 인스턴스

    Examples:
        >>> logger = get_logger()
        >>> logger.info("애플리케이션 시작")
        # 출력: 2025-11-27 14:30:25 INFO [d:\...\main.py:10 main] 애플리케이션 시작
    """
    # 싱글톤 패턴: 이미 초기화된 로거가 있으면 재사용
    logger = logging.getLogger("app")

    # 핸들러가 이미 있으면 재사용 (중복 초기화 방지)
    if logger.handlers:
        return logger

    # 로그 레벨 설정 (DEBUG 이상 모두 기록)
    logger.setLevel(logging.DEBUG)

    # 로그 메시지 포맷 설정
    formatter = logging.Formatter(LOG_FORMAT)

    try:
        # logs 폴더 자동 생성
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # 오래된 로그 파일 정리 (5개 초과 시 삭제)
        _cleanup_old_logs()

        # 새 로그 파일 경로 생성
        log_file_path = _create_log_file_path()

        # 파일 핸들러 생성
        handler = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
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
