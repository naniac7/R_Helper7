"""
레이어: infra
역할: ChromeDriver 자동 다운로드 및 설정
의존: 없음
외부: pathlib, selenium, webdriver_manager, src.shared.logging.app_logger

목적: webdriver-manager 라이브러리를 사용해 feature 내부 drivers/ 폴더에 ChromeDriver를 저장한다.
다른 feature와 driver를 공유하지 않으며, 시스템 PATH 설정이 불필요하다.
"""

from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


def get_chrome_driver(headless: bool = False) -> webdriver.Chrome:
    """
    목적: ChromeDriver를 자동으로 다운로드하고 설정된 옵션으로 반환

    Args:
        headless: 헤드리스 모드 활성화 여부 (기본값: False)

    Returns:
        설정이 완료된 Chrome WebDriver 인스턴스
    """
    # 프로필 디렉토리 경로 설정 (feature 폴더 기준으로 상대 경로 조정)
    feature_dir = Path(__file__).parent.parent  # infra 폴더에서 한 단계 위로
    profile_dir = feature_dir / "data" / "profiles" / "crawler-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Chrome 프로필 디렉토리: %s", profile_dir)

    # Chrome 옵션 설정
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={profile_dir}")

    if headless:
        LOGGER.info("헤드리스 모드 활성화")
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
    else:
        LOGGER.info("일반 모드 (브라우저 창 표시)")

    # 자동화 감지 우회 옵션
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    # 추가 안정성 옵션
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")  # Chrome 내부 로그 최소화 (치명적 에러만)

    # ChromeDriver 자동 다운로드 및 설치
    # webdriver-manager는 기본 캐시 디렉토리에 저장됨 (~/.wdm/)
    LOGGER.info("ChromeDriver 다운로드 시작")

    try:
        # 캐시 디렉토리 수동 삭제 (Windows용)
        import os
        import shutil
        wdm_dir = Path.home() / ".wdm"
        if wdm_dir.exists():
            LOGGER.info("기존 ChromeDriver 캐시 삭제 중: %s", wdm_dir)
            try:
                shutil.rmtree(wdm_dir)
            except Exception as e:
                LOGGER.warning("캐시 삭제 실패 (사용 중일 수 있음): %s", e)

        # ChromeDriver 자동 다운로드
        driver_path = ChromeDriverManager().install()
        LOGGER.info("ChromeDriver 경로: %s", driver_path)

        # 경로 검증
        if not Path(driver_path).exists():
            raise FileNotFoundError(f"ChromeDriver 파일을 찾을 수 없음: {driver_path}")

        # Windows에서 실행 파일 확인
        if os.name == 'nt' and not driver_path.endswith('.exe'):
            # .exe 확장자 확인
            exe_path = driver_path + '.exe'
            if Path(exe_path).exists():
                driver_path = exe_path
                LOGGER.info("Windows용 ChromeDriver 경로 수정: %s", driver_path)
            else:
                # chromedriver.exe 파일 직접 찾기
                parent_dir = Path(driver_path).parent
                for file in parent_dir.glob("chromedriver*.exe"):
                    driver_path = str(file)
                    LOGGER.info("ChromeDriver 실행 파일 발견: %s", driver_path)
                    break
    except Exception as exc:
        LOGGER.error("ChromeDriver 설정 중 에러: %s", exc)
        raise

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    LOGGER.info("Chrome WebDriver 인스턴스 생성 완료")
    return driver