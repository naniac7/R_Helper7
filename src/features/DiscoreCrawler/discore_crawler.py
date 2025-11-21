"""
disco.re 크롤링 feature
목적: disco.re 웹사이트에서 건물 정보를 크롤링하는 기능을 담당
"""

import time
from pathlib import Path
import os

from selenium import webdriver
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyQt5.QtCore import Qt

from shared.logging.app_logger import get_logger

# 로거 - disco.re 크롤링 전용 로거
LOGGER = get_logger()

# 프로필 디렉토리 설정 - 크롤러 쿠키 및 설정 저장용
DEFAULT_PROFILE_DIR = Path.home() / "Documents" / "chrome-automation-profile"
PROFILE_DIR = Path(os.environ.get("CHROME_AUTOMATION_PROFILE", str(DEFAULT_PROFILE_DIR)))


class DiscoreCrawler:
    """
    disco.re 크롤링 컨트롤러
    목적: disco.re 웹사이트에서 건물 정보를 검색하고 크롤링
    """

    def __init__(self, gui_ref, headless_mode=False):
        """
        생성자
        목적: 크롤러 초기화 및 GUI 참조 설정

        Args:
            gui_ref: 메인 GUI 윈도우 참조 (상태 업데이트 및 위젯 접근용)
            headless_mode: 헤드리스 모드 사용 여부
        """
        self.gui = gui_ref  # GUI 참조 - 상태 업데이트 및 위젯 접근용
        self.headless_mode = headless_mode  # 헤드리스 모드 플래그
        self.crawler_driver = None  # Selenium 드라이버 인스턴스

    def init_crawler_driver(self):
        """
        disco.re 크롤링용 Chrome 드라이버 초기화
        목적: Selenium 드라이버를 생성하고 disco.re 접속
        """
        try:
            options = webdriver.ChromeOptions()
            # 크롤러용 프로필 디렉토리 설정 (쿠키 유지를 위해)
            crawler_profile_dir = PROFILE_DIR / "crawler-profile"
            crawler_profile_dir.mkdir(parents=True, exist_ok=True)
            options.add_argument(f"--user-data-dir={str(crawler_profile_dir)}")
            options.add_argument("--profile-directory=Default")

            # 헤드리스 모드 설정
            if self.headless_mode:
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                LOGGER.info("헤드리스 모드로 실행")
            else:
                LOGGER.info("풀모드로 실행")

            self.crawler_driver = webdriver.Chrome(options=options)
            mode_text = "헤드리스" if self.headless_mode else "풀"
            LOGGER.info("크롤러 드라이버 초기화 완료 (%s 모드, 프로필: %s)", mode_text, crawler_profile_dir)

            # disco.re 사이트로 이동
            self.crawler_driver.get("https://disco.re")
            LOGGER.info("disco.re 사이트 접속 완료")

            # 웰컴 팝업 처리
            self._handle_welcome_popup()

            self.gui.update_status("크롤링용 Chrome 창이 준비되었어.")
        except WebDriverException as exc:
            LOGGER.exception("크롤러 드라이버 초기화 실패", exc_info=exc)
            self.gui.update_status(f"크롤링용 Chrome 초기화 실패: {exc}")
            self.crawler_driver = None

    def _handle_welcome_popup(self):
        """
        disco.re 웰컴 팝업 처리 (오늘 하루 안볼래요 클릭)
        목적: 첫 방문 시 나타나는 웰컴 팝업 자동으로 닫기
        """
        if not self.crawler_driver:
            return

        try:
            # 최대 2초 동안 웰컴 팝업 버튼 대기
            wait = WebDriverWait(self.crawler_driver, 2)
            welcome_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".disco-welcome-button.disco-welcome-block")
                )
            )

            # 버튼 텍스트 확인 (안전성을 위해)
            button_text = welcome_button.text.strip()
            if "오늘 하루 안볼래요" in button_text or "오늘" in button_text:
                # JavaScript로 클릭 (더 안정적)
                self.crawler_driver.execute_script("arguments[0].click();", welcome_button)
                LOGGER.info("웰컴 팝업 '오늘 하루 안볼래요' 클릭 완료")
                self.gui.update_status("웰컴 팝업을 닫았어.")

                # 팝업이 사라질 때까지 짧게 대기
                time.sleep(0.5)
            else:
                LOGGER.warning("예상치 못한 버튼 텍스트: %s", button_text)

        except TimeoutException:
            # 팝업이 없는 경우 (이미 이전에 클릭했거나, 쿠키가 있는 경우)
            LOGGER.info("웰컴 팝업이 나타나지 않음 (이미 처리됨 또는 쿠키 존재)")
        except NoSuchElementException:
            LOGGER.info("웰컴 팝업 요소를 찾을 수 없음")
        except Exception as exc:
            # 다른 예외 발생시 로그만 남기고 계속 진행
            LOGGER.warning("웰컴 팝업 처리 중 예외 발생: %s", exc)

    def handle_search(self, address):
        """
        검색 버튼 클릭 및 주소 입력 핸들러
        목적: 사용자가 입력한 주소를 disco.re에서 검색하고 자동완성 목록 표시

        Args:
            address: 검색할 주소 문자열
        """
        if not address:
            self.gui.update_status("검색할 주소를 입력해주세요.")
            return

        if not self.crawler_driver:
            self.gui.update_status("크롤러가 초기화되지 않았습니다.")
            LOGGER.error("크롤러 드라이버가 None 상태")
            return

        LOGGER.info("검색 시작: %s", address)
        self.gui.update_status("주소를 검색하는 중...")

        with self.gui.wait_cursor():
            try:
                # 뒤로가기 버튼 순차 확인 및 처리
                back_clicked = False

                # 1. foot_back_btn 확인 (상세 페이지 뒤로가기)
                try:
                    short_wait = WebDriverWait(self.crawler_driver, 0.3)
                    foot_back_btn = short_wait.until(
                        EC.element_to_be_clickable((By.ID, "foot_back_btn"))
                    )
                    # 클릭 가능한 상태면 클릭
                    self.crawler_driver.execute_script("arguments[0].click();", foot_back_btn)
                    self.gui.update_status("상세 페이지에서 메인으로 돌아갔어.")
                    back_clicked = True
                    LOGGER.info("foot_back_btn 클릭 완료")
                except TimeoutException:
                    # foot_back_btn이 없거나 클릭 불가능
                    pass

                # 2. foot_back_btn이 없으면 일반 뒤로가기 버튼 확인
                if not back_clicked:
                    try:
                        short_wait = WebDriverWait(self.crawler_driver, 0.3)
                        back_image = short_wait.until(
                            EC.element_to_be_clickable((By.XPATH, "//img[contains(@src, 'back')]"))
                        )
                        # 클릭 가능한 상태면 클릭
                        self.crawler_driver.execute_script("arguments[0].click();", back_image)
                        self.gui.update_status("이전 화면으로 돌아갔어.")
                        back_clicked = True
                        LOGGER.info("일반 뒤로가기 버튼 클릭 완료")
                    except TimeoutException:
                        # 일반 뒤로가기도 없거나 클릭 불가능
                        pass

                # 3. 주소검색 버튼 찾기 및 대기
                wait = WebDriverWait(self.crawler_driver, 4)
                dsv_search_btn = wait.until(
                    EC.element_to_be_clickable((By.ID, "dsv_search_btn"))
                )
                LOGGER.info("주소검색 버튼 발견")

                # 주소검색 버튼 클릭
                self.crawler_driver.execute_script("arguments[0].click();", dsv_search_btn)
                LOGGER.info("dsv_search_btn 클릭 완료")
                self.gui.update_status("검색 버튼 클릭 완료")

                # 2. top_search_ds_input 대기 후 주소 입력
                address_input = wait.until(
                    EC.element_to_be_clickable((By.ID, "top_search_ds_input"))
                )
                address_input.clear()
                address_input.send_keys(address)
                LOGGER.info("주소 입력 완료: %s", address)
                self.gui.update_status(f"주소 입력 완료: {address}")

                # 자동완성 생성 대기 (0.5초)
                time.sleep(0.5)

                # 3. 자동완성 목록 대기 및 파싱
                try:
                    suggestions_container = wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ds-autocomplete-suggestions"))
                    )

                    suggestion_elements = suggestions_container.find_elements(
                        By.CLASS_NAME, "autocomplete-suggestion"
                    )
                    LOGGER.info("자동완성 항목 %d개 발견", len(suggestion_elements))

                    if not suggestion_elements:
                        self.gui.update_status("자동완성 목록이 비어 있습니다.")
                        self.gui.crawling_select_area.clear()
                        self.gui.crawling_select_area.addItem("주소 선택")
                        return

                    # 목록 파싱 및 UI 업데이트 (콤보박스)
                    # 목적: 검색 결과를 콤보박스에 추가하고 자동으로 펼치기
                    self.gui.crawling_select_area.clear()
                    self.gui.crawling_select_area.addItem("주소 선택")
                    self.gui.address_data_list = []

                    for elem in suggestion_elements:
                        try:
                            full_text = elem.text.strip()
                            sub_value_elem = elem.find_element(By.CLASS_NAME, "sub-value")
                            sub_value_text = sub_value_elem.text.strip()
                            main_address = full_text.replace(sub_value_text, "").strip()

                            # data-index 저장
                            data_index = elem.get_attribute("data-index")
                            self.gui.address_data_list.append({
                                "data_index": data_index,
                                "main": main_address,
                                "sub": sub_value_text
                            })

                            # 콤보박스에 항목 추가
                            # 1줄 형식: "주소1 / 주소2"
                            # UserRole(itemData): data_index (selenium 클릭용)
                            display_text = f"{main_address} / {sub_value_text}"
                            self.gui.crawling_select_area.addItem(display_text)
                            idx = self.gui.crawling_select_area.count() - 1
                            self.gui.crawling_select_area.setItemData(idx, data_index, Qt.UserRole)

                        except NoSuchElementException:
                            # sub-value 없는 경우
                            main_address = elem.text.strip()
                            data_index = elem.get_attribute("data-index")
                            self.gui.address_data_list.append({
                                "data_index": data_index,
                                "main": main_address,
                                "sub": ""
                            })

                            # 콤보박스에 항목 추가 (sub 없는 경우)
                            # 1줄 형식: 주소만 표시
                            self.gui.crawling_select_area.addItem(main_address)
                            idx = self.gui.crawling_select_area.count() - 1
                            self.gui.crawling_select_area.setItemData(idx, data_index, Qt.UserRole)

                    LOGGER.info("자동완성 목록 표시 완료")
                    self.gui.update_status(f"자동완성 목록 {len(self.gui.address_data_list)}개 표시 완료")

                    # 콤보박스 자동 펼치기
                    # 목적: 사용자가 바로 선택할 수 있도록
                    self.gui.crawling_select_area.showPopup()

                except TimeoutException:
                    error_msg = "자동완성 목록을 찾을 수 없음"
                    LOGGER.warning(error_msg)
                    self.gui.update_status(error_msg)
                    self.gui.crawling_select_area.clear()
                    self.gui.crawling_select_area.addItem("주소 선택")
                    self.gui.address_data_list = []
                except Exception as e:
                    error_msg = f"자동완성 파싱 중 예외: {e}"
                    LOGGER.exception(error_msg)
                    self.gui.update_status(error_msg)
                    self.gui.crawling_select_area.clear()
                    self.gui.crawling_select_area.addItem("주소 선택")
                    self.gui.address_data_list = []

                # 검색 완료 메시지
                self.gui.update_status("검색 완료")

            except TimeoutException:
                error_msg = "요소를 찾을 수 없음"
                LOGGER.error(error_msg)
                self.gui.update_status(error_msg)
            except Exception as exc:
                error_msg = f"검색 중 예외 발생: {exc}"
                LOGGER.exception(error_msg)
                self.gui.update_status(error_msg)

    def handle_address_click(self, index):
        """
        주소 콤보박스 선택 핸들러
        목적: 사용자가 선택한 주소를 disco.re에서 클릭하고 건물 목록 표시

        Args:
            index: 선택된 주소의 인덱스 (address_data_list 기준)
        """
        if not self.crawler_driver:
            self.gui.update_status("크롤러가 초기화되지 않았습니다.")
            return

        # 인덱스 유효성 검사
        if index < 0 or index >= len(self.gui.address_data_list):
            LOGGER.warning("잘못된 인덱스: %d", index)
            return

        address_data = self.gui.address_data_list[index]
        data_index = address_data["data_index"]
        main_address = address_data["main"]

        LOGGER.info("주소 선택: %s (data-index=%s)", main_address, data_index)
        self.gui.update_status("선택한 주소를 불러오는 중...")

        with self.gui.wait_cursor():
            try:
                # 웹 페이지에서 해당 data-index 항목 클릭
                wait = WebDriverWait(self.crawler_driver, 4)
                suggestion_elem = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, f'.autocomplete-suggestion[data-index="{data_index}"]'))
                )
                self.crawler_driver.execute_script("arguments[0].click();", suggestion_elem)
                LOGGER.info("웹 페이지 자동완성 항목 클릭 완료 (data-index=%s)", data_index)
                self.gui.update_status(f"주소 선택 완료: {main_address}")

                # 건물 탭 클릭
                self._crawl_building()

            except TimeoutException:
                error_msg = f"자동완성 항목을 찾을 수 없음 (data-index={data_index})"
                LOGGER.error(error_msg)
                self.gui.update_status(error_msg)
            except Exception as exc:
                error_msg = f"주소 선택 중 예외: {exc}"
                LOGGER.exception(error_msg)
                self.gui.update_status(error_msg)

    def _crawl_building(self):
        """
        건물 탭 클릭 메서드
        목적: disco.re에서 건물 탭을 클릭하여 건물 목록 표시
        """
        if not self.crawler_driver:
            LOGGER.warning("크롤러 드라이버가 초기화되지 않음")
            return

        # 첫 번째 시도
        try:
            LOGGER.info("건물 탭 클릭 시도 중...")
            wait = WebDriverWait(self.crawler_driver, 5)
            building_tab = wait.until(
                EC.element_to_be_clickable((By.ID, "dp_navi_4"))
            )

            # JavaScript로 클릭
            self.crawler_driver.execute_script("arguments[0].click();", building_tab)
            LOGGER.info("건물 탭 클릭 성공")

            # 건물 목록 파싱
            self._parse_building_list()
            return

        except TimeoutException:
            LOGGER.warning("건물 탭 요소를 찾을 수 없음 (첫 번째 시도)")

        except Exception as exc:
            LOGGER.warning("건물 탭 클릭 실패 (첫 번째 시도): %s", exc)

        # 1초 대기 후 재시도
        time.sleep(1)

        try:
            LOGGER.info("건물 탭 클릭 재시도 중...")
            wait = WebDriverWait(self.crawler_driver, 5)
            building_tab = wait.until(
                EC.element_to_be_clickable((By.ID, "dp_navi_4"))
            )

            # JavaScript로 클릭
            self.crawler_driver.execute_script("arguments[0].click();", building_tab)
            LOGGER.info("건물 탭 클릭 성공 (재시도)")

            # 건물 목록 파싱
            self._parse_building_list()

        except TimeoutException:
            LOGGER.warning("건물 탭 요소를 찾을 수 없음 (재시도). 건물 탭 클릭 실패")

        except Exception as exc:
            LOGGER.warning("건물 탭 클릭 최종 실패: %s", exc)

    def _parse_building_list(self):
        """
        건물 목록 파싱 및 UI 업데이트
        목적: disco.re의 건물 목록을 파싱하여 GUI에 표시
        """
        if not self.crawler_driver:
            LOGGER.warning("크롤러 드라이버가 초기화되지 않음")
            return

        self.gui.update_status("건물 목록을 불러오는 중...")

        try:
            # 건물 목록 요소 대기 (최대 2초)
            wait = WebDriverWait(self.crawler_driver, 2)
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "ddiv-build-content"))
            )

            # 요소들이 완전히 로드되도록 짧은 대기
            time.sleep(0.5)

            # 건물 요소들 가져오기
            building_elements = self.crawler_driver.find_elements(By.CLASS_NAME, "ddiv-build-content")

            if not building_elements:
                LOGGER.warning("건물 목록이 없음")
                self.gui.update_status("건물 목록이 없습니다.")
                self._set_no_buildings()
                return

            # 건물 목록 초기화
            self.gui.building_list = []
            self.gui.building_combo.clear()

            # 건물 정보 파싱
            for idx, element in enumerate(building_elements):
                try:
                    top_elem = element.find_element(By.CLASS_NAME, "ddiv-build-content-top")
                    bottom_elem = element.find_element(By.CLASS_NAME, "ddiv-build-content-bottom")

                    # JavaScript로 텍스트 가져오기 (숨겨진 요소도 텍스트 추출 가능)
                    top_text = self.crawler_driver.execute_script(
                        "return arguments[0].textContent || arguments[0].innerText || '';",
                        top_elem
                    ).strip()

                    bottom_text = self.crawler_driver.execute_script(
                        "return arguments[0].textContent || arguments[0].innerText || '';",
                        bottom_elem
                    ).strip()

                    # 텍스트가 비어있으면 일반 .text 시도
                    if not top_text:
                        top_text = top_elem.text.strip()
                    if not bottom_text:
                        bottom_text = bottom_elem.text.strip()

                    # 타이틀 요소 가져오기 (있을 경우)
                    title_text = ""
                    try:
                        title_elem = element.find_element(By.CLASS_NAME, "ddiv-build-content-title")
                        title_text = self.crawler_driver.execute_script(
                            "return arguments[0].textContent || arguments[0].innerText || '';",
                            title_elem
                        ).strip()
                        if not title_text:
                            title_text = title_elem.text.strip()
                    except NoSuchElementException:
                        # 타이틀 요소가 없는 경우
                        pass

                    # 표시 형식 결정
                    if title_text:
                        display_text = f"{top_text}({bottom_text}) [{title_text}]"
                    else:
                        display_text = f"{top_text}({bottom_text})"

                    # 건물 정보 저장 (원본 인덱스 포함)
                    building_info = {
                        "index": idx,
                        "top": top_text,
                        "bottom": bottom_text,
                        "title": title_text,
                        "display": display_text
                    }
                    self.gui.building_list.append(building_info)

                    LOGGER.info("건물 파싱 #%d: %s", idx, display_text)

                except NoSuchElementException:
                    LOGGER.warning("건물 요소 파싱 실패 (인덱스: %d)", idx)
                    continue
                except Exception as exc:
                    LOGGER.warning("건물 정보 추출 실패 (인덱스: %d): %s", idx, exc)
                    continue

            # 표시할 건물 목록 결정
            if len(self.gui.building_list) == 0:
                LOGGER.warning("파싱된 건물이 없음")
                self._set_no_buildings()
                return

            # 모든 건물을 표시 (개수와 무관하게)
            display_buildings = self.gui.building_list

            # QComboBox에 건물 추가
            for building in display_buildings:
                self.gui.building_combo.addItem(building["display"], building["index"])

            # QComboBox 활성화
            self.gui.building_combo.setEnabled(True)

            LOGGER.info("건물 목록 파싱 완료: 총 %d개", len(self.gui.building_list))
            self.gui.update_status(f"건물 {len(display_buildings)}개를 불러왔습니다.")

        except TimeoutException:
            LOGGER.warning("건물 목록 로드 타임아웃")
            self.gui.update_status("건물 목록을 불러올 수 없습니다.")
            self._set_no_buildings()

        except Exception as exc:
            LOGGER.exception("건물 목록 파싱 중 예외 발생", exc_info=exc)
            self.gui.update_status("건물 목록 파싱 중 오류가 발생했습니다.")
            self._set_no_buildings()

    def _set_no_buildings(self):
        """
        건물이 없을 때 UI 설정
        목적: 건물 목록이 비어있을 때 GUI 상태 설정
        """
        self.gui.building_combo.clear()
        self.gui.building_combo.addItem("건물 없음")
        self.gui.building_combo.setEnabled(False)
        self.gui.building_list = []

    def handle_building_selection(self, index):
        """
        건물 선택 이벤트 처리
        목적: 사용자가 선택한 건물을 disco.re에서 클릭하고 상세 정보 크롤링

        Args:
            index: 선택된 건물의 콤보박스 인덱스
        """
        if not self.crawler_driver:
            LOGGER.warning("크롤러 드라이버가 초기화되지 않음")
            return

        # 초기 상태나 "건물 없음" 선택 시 무시
        if index < 0 or not self.gui.building_combo.isEnabled():
            return

        # 선택된 건물의 원본 인덱스 가져오기
        original_index = self.gui.building_combo.itemData(index)
        if original_index is None:
            LOGGER.warning("선택된 건물의 인덱스 정보가 없음")
            return

        try:
            # 현재 페이지의 건물 요소들 다시 가져오기
            building_elements = self.crawler_driver.find_elements(By.CLASS_NAME, "ddiv-build-content")

            if original_index >= len(building_elements):
                LOGGER.error("인덱스 범위 초과: %d (전체: %d)", original_index, len(building_elements))
                return

            # 선택된 건물 클릭
            target_element = building_elements[original_index]
            self.crawler_driver.execute_script("arguments[0].click();", target_element)

            selected_building = self.gui.building_combo.currentText()
            LOGGER.info("건물 선택 완료: %s (인덱스: %d)", selected_building, original_index)
            self.gui.update_status(f"건물 선택: {selected_building}")

            # 다시 가져오기 버튼 활성화
            self.gui.refresh_crawl_button.setEnabled(True)

            # 건물 선택 직후 자동 크롤링 실행
            self.perform_crawling()

        except Exception as exc:
            LOGGER.exception("건물 선택 중 예외 발생", exc_info=exc)
            self.gui.update_status("건물 선택 중 오류가 발생했습니다.")

    def refresh_crawling(self):
        """
        다시 가져오기 버튼 핸들러
        목적: 건물 상세 정보를 다시 크롤링
        """
        self.perform_crawling()

    def perform_crawling(self):
        """
        건물 상세 정보 크롤링 실행
        목적: disco.re의 건물 상세 페이지에서 정보를 크롤링하여 GUI에 표시
        """
        if not self.crawler_driver:
            LOGGER.error("크롤러 드라이버가 None 상태")
            self.gui.update_status("크롤러가 초기화되지 않았습니다.")
            return

        LOGGER.info("크롤링 시작")
        self.gui.update_status("크롤링 중...")

        with self.gui.wait_cursor():
            try:
                # 2초 대기 (페이지 로딩)
                time.sleep(2)

                # JavaScript로 크롤링 (부모-자식 구조 기반)
                # 왼쪽 div는 제목, 오른쪽 div는 내용을 담고 있음
                # rfc-dusk 클래스 우선, 실패시 두 번째 ifs-tab-txt 사용
                script = """
                    return Array.from(document.querySelectorAll('.mfs-agent-main-tab-div'))
                        .map(div => {
                            const titleElem = div.querySelector('.ifs-tab-txt');

                            // 오른쪽 div 찾기 - 방법1: rfc-dusk 클래스
                            let rightDiv = div.querySelector('.ifs-tab-txt.rfc-dusk');
                            let rightDivMethod = 'rfc-dusk';

                            // 방법2: rfc-dusk가 없으면 두 번째 ifs-tab-txt 요소
                            if (!rightDiv) {
                                const allTabTxts = div.querySelectorAll('.ifs-tab-txt');
                                if (allTabTxts.length >= 2) {
                                    rightDiv = allTabTxts[1];  // 두 번째 요소 (오른쪽)
                                    rightDivMethod = 'second-element';
                                }
                            }

                            let content = '';
                            let usedSelector = '';

                            if (rightDiv) {
                                // span 요소 찾기 (id가 있는 span 우선)
                                const contentElem = rightDiv.querySelector('span[id]') ||
                                                   rightDiv.querySelector('span');

                                if (contentElem && contentElem.textContent.trim()) {
                                    content = contentElem.textContent.trim();
                                    // 사용된 선택자 기록 (디버깅용)
                                    if (contentElem.id) {
                                        usedSelector = `span#${contentElem.id}`;
                                    } else if (contentElem.className) {
                                        usedSelector = `span.${contentElem.className}`;
                                    } else {
                                        usedSelector = 'span';
                                    }
                                } else {
                                    content = '값 없음';
                                    usedSelector = 'span_empty';
                                }
                            } else {
                                content = '값 없음';
                                usedSelector = 'no_right_div';
                            }

                            return {
                                title: titleElem ? titleElem.textContent.trim() : '',
                                content: content,
                                selector: usedSelector,  // 디버깅용: 어떤 선택자가 사용되었는지
                                method: rightDivMethod   // 디버깅용: 오른쪽 div를 어떻게 찾았는지
                            };
                        })
                        .filter(item => item.title);  // 제목이 있는 것만 (내용이 "값 없음"이어도 포함)
                """

                wait = WebDriverWait(self.crawler_driver, 5)
                # 요소가 로딩될 때까지 대기
                wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "mfs-agent-main-tab-div"))
                )

                self.gui.crawled_data = self.crawler_driver.execute_script(script)

                # 크롤링 결과 로깅 - 디버깅 정보 포함
                # selector와 method 정보로 어떤 방식으로 데이터를 가져왔는지 추적 가능
                LOGGER.info("크롤링 완료: %d개 항목", len(self.gui.crawled_data))
                for item in self.gui.crawled_data:
                    # 기본 정보 로깅
                    LOGGER.info("  - %s: %s", item['title'], item['content'])
                    # 디버깅 정보 로깅 (선택자와 메서드)
                    LOGGER.debug("    [디버깅] 선택자: %s, 오른쪽div 탐색: %s",
                                 item.get('selector', 'unknown'),
                                 item.get('method', 'unknown'))

                    # 값이 없는 경우 경고 로깅
                    if item['content'] == '값 없음':
                        if item.get('selector') == 'no_right_div':
                            LOGGER.warning("    ⚠️ '%s' 항목: 오른쪽 div를 찾을 수 없음", item['title'])
                        elif item.get('selector') == 'span_empty':
                            LOGGER.warning("    ⚠️ '%s' 항목: span은 있지만 텍스트가 비어있음", item['title'])
                        else:
                            LOGGER.warning("    ⚠️ '%s' 항목: 값을 찾을 수 없음", item['title'])

                # 각 크롤 행의 내용 업데이트
                # 크롤링 데이터와 UI 행을 제목으로 매칭
                # "값 없음"도 정상적인 크롤링 결과로 처리
                for crawl_row in self.gui.crawling_rows:
                    title = crawl_row.get_title()
                    if not title:
                        continue

                    # 정확히 일치하는 제목 찾기
                    found = False
                    for data in self.gui.crawled_data:
                        if data['title'] == title:
                            crawl_row.set_content(data['content'])
                            # 값 상태에 따른 로깅
                            if data['content'] == '값 없음':
                                LOGGER.info("크롤 행 '%s': 크롤링 성공 (값 없음)", title)
                            else:
                                LOGGER.info("크롤 행 '%s' 내용 설정: %s", title, data['content'])
                            found = True
                            break

                    if not found:
                        # 크롤링 데이터에서 제목을 찾을 수 없는 경우
                        crawl_row.set_content("항목 없음")
                        LOGGER.warning("크롤 행 '%s': 크롤링 데이터에서 매칭되는 항목을 찾을 수 없음", title)

                self.gui.update_status(f"크롤링 완료: {len(self.gui.crawled_data)}개 항목")

            except TimeoutException:
                error_msg = "크롤링 대기 시간 초과"
                LOGGER.error(error_msg)
                self.gui.update_status(error_msg)
            except Exception as exc:
                error_msg = f"크롤링 중 예외 발생: {exc}"
                LOGGER.exception(error_msg)
                self.gui.update_status(error_msg)
