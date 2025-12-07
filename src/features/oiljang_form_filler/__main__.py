"""
레이어: api (엔트리포인트)
역할: 오일장 폼 자동 채우기 앱 실행
의존: 모든 레이어
외부: PyQt5

목적: 의존성 조립(Composition Root) 및 앱 실행

실행:
    python -m src.features.oiljang_form_filler
"""
import sys

from PyQt5.QtWidgets import QApplication, QMessageBox

from src.shared.logging.app_logger import get_logger

logger = get_logger()


def main():
    """
    메인 함수

    1. 의존성 조립 (Composition Root)
    2. 크롬 연결
    3. GUI 실행
    """
    logger.info("=" * 50)
    logger.info("오일장 폼 자동 채우기 시작")
    logger.info("=" * 50)

    # QApplication 먼저 생성 (에러 다이얼로그 표시용)
    app = QApplication(sys.argv)

    try:
        # 크롬 컨트롤러 생성 (크롬 자동 실행)
        from src.shared.browser.chrome_controller import ChromeController

        logger.info("크롬 연결 중...")
        chrome_controller = ChromeController()
        logger.info("크롬 연결 성공")

    except RuntimeError as e:
        logger.exception("크롬 연결 실패", exc_info=e)
        QMessageBox.critical(None, "연결 실패", str(e))
        sys.exit(1)

    try:
        # 인프라 레이어 생성
        from src.features.oiljang_form_filler.infra.form_filler import OiljangFormFiller
        from src.features.oiljang_form_filler.infra.preset_repository import PresetRepository

        form_filler = OiljangFormFiller(chrome_controller)
        preset_repository = PresetRepository()

        # 앱 레이어 생성 (유즈케이스)
        from src.features.oiljang_form_filler.app.fill_field_use_case import FillFieldUseCase
        from src.features.oiljang_form_filler.app.load_presets_use_case import LoadPresetsUseCase
        from src.features.oiljang_form_filler.app.save_presets_use_case import SavePresetsUseCase
        from src.features.oiljang_form_filler.app.send_all_use_case import SendAllUseCase

        fill_field_uc = FillFieldUseCase(form_filler)
        save_presets_uc = SavePresetsUseCase(preset_repository)
        load_presets_uc = LoadPresetsUseCase(preset_repository)
        send_all_uc = SendAllUseCase(fill_field_uc)

        # GUI 생성
        from src.features.oiljang_form_filler.api.gui.main_window import MainWindow

        window = MainWindow(
            fill_field_use_case=fill_field_uc,
            save_presets_use_case=save_presets_uc,
            load_presets_use_case=load_presets_uc,
            send_all_use_case=send_all_uc,
        )

        logger.info("GUI 초기화 완료")
        window.show()

        # 이벤트 루프 실행
        exit_code = app.exec_()
        logger.info("앱 종료: %s", exit_code)
        sys.exit(exit_code)

    except Exception as e:
        logger.exception("앱 실행 중 오류", exc_info=e)
        QMessageBox.critical(None, "오류", f"앱 실행 중 오류 발생:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
