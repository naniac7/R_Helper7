"""
목적: Site Crawler feature 독립 실행 엔트리 포인트

실행 방법:
    python -m src.features.site_crawler
"""

import sys
from PyQt5.QtWidgets import QApplication

from src.features.site_crawler.gui.main_window import SiteCrawlerMainWindow
from src2.shared.logging.app_logger import get_logger

LOGGER = get_logger()


def main():
    """
    목적: Site Crawler 애플리케이션 실행
    """
    LOGGER.info("Site Crawler 애플리케이션 시작")

    app = QApplication(sys.argv)
    app.setApplicationName("Site Crawler")

    window = SiteCrawlerMainWindow()
    window.show()

    LOGGER.info("Site Crawler 윈도우 표시 완료")

    exit_code = app.exec_()
    LOGGER.info("Site Crawler 애플리케이션 종료 (exit_code=%d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
