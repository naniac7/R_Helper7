"""
레이어: shared
역할: 크롬 브라우저 자동 실행 및 연결 관리
의존: 없음
외부: selenium, subprocess

목적: 여러 feature에서 공통으로 사용하는 크롬 브라우저 제어

사용법:
    from src.shared.browser.chrome_controller import ChromeController

    controller = ChromeController()
    driver = controller.get_driver()
    controller.focus_active_tab()
"""
import os
import socket
import subprocess
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from src.shared.logging.app_logger import get_logger

logger = get_logger()


class ChromeController:
    """
    크롬 브라우저 자동 실행 및 연결 관리

    - 크롬이 실행 중이면 기존 크롬에 연결
    - 실행 중이 아니면 자동으로 크롬 실행 후 연결
    - 모든 feature가 동일한 프로필(캐시) 공유
    """

    DEFAULT_DEBUGGER_ADDRESS = "127.0.0.1:2578"
    DEFAULT_DEBUGGER_PORT = 2578
    STARTUP_WAIT_SECONDS = 3
    DEFAULT_START_URL = "https://www.jejuall.com/"

    def __init__(self, debugger_address: str = None, start_url: str = None):
        """
        크롬 컨트롤러 초기화

        Args:
            debugger_address: 디버거 주소 (기본: 127.0.0.1:2578)
            start_url: 크롬 실행 시 열 URL (기본: jejuall.com)
        """
        self._address = debugger_address or self.DEFAULT_DEBUGGER_ADDRESS
        self._start_url = start_url or self.DEFAULT_START_URL
        self._driver = None
        self._main_handle = None
        self._launch_or_connect()

    def _get_profile_dir(self) -> Path:
        """
        AppData에 크롬 프로필 경로 반환 (없으면 생성)

        Returns:
            Path: 프로필 디렉토리 경로

        예: C:/Users/DY/AppData/Local/RHelper/chrome-profile/
        """
        app_data = Path(os.environ.get(
            "LOCALAPPDATA",
            Path.home() / "AppData" / "Local"
        ))
        profile_dir = app_data / "RHelper" / "chrome-profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        logger.info("크롬 프로필 경로: %s", profile_dir)
        return profile_dir

    def _get_chrome_path(self) -> str:
        """
        크롬 실행 경로 반환

        환경변수 CHROME_PATH로 오버라이드 가능

        Returns:
            str: 크롬 실행 파일 경로
        """
        return os.environ.get(
            "CHROME_PATH",
            "C:/Program Files/Google/Chrome/Application/chrome.exe"
        )

    def _launch_chrome(self) -> None:
        """
        크롬을 디버깅 모드로 실행

        --remote-debugging-port와 --user-data-dir 옵션으로 실행
        """
        chrome_path = self._get_chrome_path()
        profile_dir = self._get_profile_dir()

        logger.info("크롬 실행 시도: %s", chrome_path)
        logger.info("디버깅 포트: %s", self.DEFAULT_DEBUGGER_PORT)

        try:
            subprocess.Popen([
                chrome_path,
                f"--remote-debugging-port={self.DEFAULT_DEBUGGER_PORT}",
                f"--user-data-dir={profile_dir}",
                self._start_url,
            ])
            logger.info("크롬 실행 완료, %s초 대기", self.STARTUP_WAIT_SECONDS)
            time.sleep(self.STARTUP_WAIT_SECONDS)
        except FileNotFoundError:
            logger.error("크롬 실행 파일을 찾을 수 없음: %s", chrome_path)
            raise RuntimeError(
                f"크롬을 찾을 수 없어: {chrome_path}\n"
                "CHROME_PATH 환경변수로 크롬 경로를 지정해줘!"
            )
        except Exception as e:
            logger.exception("크롬 실행 중 오류", exc_info=e)
            raise RuntimeError(f"크롬 실행 실패: {e}")

    def _launch_or_connect(self) -> None:
        """
        크롬에 연결 시도, 실패하면 실행 후 재연결
        """
        # 먼저 기존 크롬에 연결 시도
        if self._try_connect():
            logger.info("기존 크롬에 연결 성공")
            return

        # 연결 실패 시 크롬 실행
        logger.info("기존 크롬 없음, 새로 실행")
        self._launch_chrome()

        # 재연결 시도
        if not self._try_connect():
            raise RuntimeError(
                "크롬 연결 실패! 크롬이 제대로 실행됐는지 확인해줘."
            )

        logger.info("크롬 연결 성공")

    def _is_port_open(self) -> bool:
        """포트 열려있는지 빠르게 체크 (1초 타임아웃)"""
        host, port = self._address.split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        try:
            sock.connect((host, int(port)))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
        finally:
            sock.close()

    def _try_connect(self) -> bool:
        """
        기존 크롬에 연결 시도

        Returns:
            bool: 연결 성공 여부
        """
        # 포트 체크 먼저
        if not self._is_port_open():
            logger.debug("포트 닫힘, 연결 스킵")
            return False

        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", self._address)

        try:
            self._driver = webdriver.Chrome(options=options)
            self._log_versions()

            try:
                self._main_handle = self._driver.current_window_handle
                logger.info("메인 핸들 저장: %s", self._main_handle)
            except WebDriverException:
                logger.warning("메인 핸들을 가져오지 못함")
                self._main_handle = None

            return True
        except WebDriverException as e:
            logger.debug("크롬 연결 실패: %s", e)
            return False

    def _log_versions(self) -> None:
        """브라우저와 ChromeDriver 버전 로깅"""
        caps = getattr(self._driver, "capabilities", {}) or {}
        browser_version = caps.get("browserVersion") or caps.get("version") or "unknown"
        chrome_info = caps.get("chrome") or {}
        chromedriver_version_raw = chrome_info.get("chromedriverVersion") or "unknown"
        chromedriver_version = chromedriver_version_raw.split(" ")[0]

        logger.info("브라우저 버전: %s", browser_version)
        logger.info("ChromeDriver 버전: %s", chromedriver_version)

        def _major(ver: str) -> str:
            return ver.split(".")[0] if ver and ver != "unknown" else ""

        if _major(browser_version) and _major(chromedriver_version):
            if _major(browser_version) != _major(chromedriver_version):
                logger.warning(
                    "브라우저와 ChromeDriver 메이저 버전이 다름! 문제가 생길 수 있어."
                )
            else:
                logger.info("브라우저와 ChromeDriver 버전 호환 확인됨")

    def get_driver(self) -> webdriver.Chrome:
        """
        WebDriver 인스턴스 반환

        Returns:
            webdriver.Chrome: 크롬 드라이버
        """
        return self._driver

    def focus_active_tab(self) -> None:
        """
        메인 탭으로 포커스 전환

        devtools:// 탭이 아닌 실제 웹 페이지 탭으로 전환
        """
        try:
            handles = self._driver.window_handles
        except WebDriverException:
            logger.warning("윈도우 핸들을 가져오지 못함")
            return

        if not handles:
            logger.warning("열린 탭이 없음")
            return

        current = self._driver.current_window_handle

        # 저장된 메인 핸들이 있으면 그쪽으로 전환
        if self._main_handle and self._main_handle in handles:
            if current != self._main_handle:
                logger.info("탭 전환: %s -> %s (메인)", current, self._main_handle)
                try:
                    self._driver.switch_to.window(self._main_handle)
                except WebDriverException:
                    logger.warning("메인 핸들 전환 실패")
            return

        # 메인 핸들이 없으면 devtools가 아닌 첫 번째 탭 찾기
        fallback = None
        for handle in handles:
            if handle == current:
                continue
            try:
                self._driver.switch_to.window(handle)
                url = self._driver.current_url
            except WebDriverException:
                continue

            logger.info("탭 검사: %s -> %s", handle, url)
            if not url.startswith("devtools://"):
                fallback = handle
                break

        # 원래 탭으로 복귀
        try:
            self._driver.switch_to.window(current)
        except WebDriverException:
            logger.warning("원래 탭으로 복귀 실패")

        # 찾은 탭으로 전환
        if fallback:
            self._main_handle = fallback
            if current != fallback:
                logger.info("탭 전환: %s -> %s (대체)", current, fallback)
                try:
                    self._driver.switch_to.window(fallback)
                except WebDriverException:
                    logger.warning("대체 핸들 전환 실패")
