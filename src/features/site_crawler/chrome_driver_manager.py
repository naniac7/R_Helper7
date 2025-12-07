"""
목적: ChromeDriver를 자동으로 다운로드하고 설정된 옵션으로 반환

webdriver-manager 라이브러리를 사용해 feature 내부 drivers/ 폴더에 ChromeDriver를 저장한다.
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
    # 프로필 디렉토리 경로 설정
    feature_dir = Path(__file__).parent
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
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 추가 안정성 옵션
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # ChromeDriver 자동 다운로드 및 설치
    # webdriver-manager는 기본 캐시 디렉토리에 저장됨 (~/.wdm/)
    LOGGER.info("ChromeDriver 다운로드 시작")
    driver_path = ChromeDriverManager().install()
    LOGGER.info("ChromeDriver 준비 완료: %s", driver_path)

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    LOGGER.info("Chrome WebDriver 인스턴스 생성 완료")
    return driver
