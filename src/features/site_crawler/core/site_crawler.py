"""
목적: disco.re 크롤링 로직 (GUI 독립적)

콜백 패턴을 사용하여 GUI와 완전히 분리된 크롤링 로직을 제공한다.
생성자에서 콜백 함수들을 받아 이벤트가 발생할 때 호출한다.
"""

import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any

from selenium import webdriver
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src2.shared.logging.app_logger import get_logger
from src.features.site_crawler.chrome_driver_manager import get_chrome_driver

LOGGER = get_logger()


class SiteCrawler:
    """
    범용 부동산 사이트 크롤러 (disco.re)
    목적: GUI 독립적인 크롤링 로직 제공 (콜백 패턴 기반)
    """

    def __init__(
        self,
        on_status: Optional[Callable[[str], None]] = None,
        on_addresses_found: Optional[Callable[[List[Dict[str, str]]], None]] = None,
        on_buildings_found: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        on_complete: Optional[Callable[[List[Dict[str, str]]], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        생성자
        목적: 크롤러 초기화 및 콜백 함수 설정

        Args:
            on_status: 상태 메시지 전달 콜백
            on_addresses_found: 주소 검색 결과 전달 콜백
            on_buildings_found: 건물 목록 전달 콜백
            on_complete: 크롤링 완료 시 결과 전달 콜백
            on_error: 에러 발생 시 전달 콜백
        """
        self.on_status = on_status
        self.on_addresses_found = on_addresses_found
        self.on_buildings_found = on_buildings_found
        self.on_complete = on_complete
        self.on_error = on_error

        self.driver: Optional[webdriver.Chrome] = None
        self.address_list: List[Dict[str, str]] = []
        self.building_list: List[Dict[str, Any]] = []
        self.crawled_data: List[Dict[str, str]] = []

    def _notify(self, message: str) -> None:
        """
        목적: 상태 메시지를 콜백으로 전달
        """
        LOGGER.info(message)
        if self.on_status:
            self.on_status(message)

    def _notify_error(self, error_msg: str) -> None:
        """
        목적: 에러 메시지를 콜백으로 전달
        """
        LOGGER.error(error_msg)
        if self.on_error:
            self.on_error(error_msg)

    def init_driver(self, headless: bool = False) -> bool:
        """
        목적: Chrome 드라이버 초기화 및 disco.re 접속

        Args:
            headless: 헤드리스 모드 사용 여부

        Returns:
            초기화 성공 여부
        """
        try:
            self._notify("Chrome 드라이버 초기화 중...")
            self.driver = get_chrome_driver(headless=headless)

            # disco.re 사이트로 이동
            self.driver.get("https://disco.re")
            self._notify("disco.re 사이트 접속 완료")

            # 웰컴 팝업 처리
            self._handle_welcome_popup()

            self._notify("크롤링용 Chrome 창이 준비되었어.")
            return True

        except WebDriverException as exc:
            error_msg = f"Chrome 드라이버 초기화 실패: {exc}"
            self._notify_error(error_msg)
            self.driver = None
            return False

    def _handle_welcome_popup(self) -> None:
        """
        목적: disco.re 웰컴 팝업 처리 (오늘 하루 안볼래요 클릭)
        """
        if not self.driver:
            return

        try:
            # 최대 2초 동안 웰컴 팝업 버튼 대기
            wait = WebDriverWait(self.driver, 2)
            welcome_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".disco-welcome-button.disco-welcome-block")
                )
            )

            # 버튼 텍스트 확인
            button_text = welcome_button.text.strip()
            if "오늘 하루 안볼래요" in button_text or "오늘" in button_text:
                # JavaScript로 클릭
                self.driver.execute_script("arguments[0].click();", welcome_button)
                LOGGER.info("웰컴 팝업 '오늘 하루 안볼래요' 클릭 완료")
                self._notify("웰컴 팝업을 닫았어.")
                time.sleep(0.5)
            else:
                LOGGER.warning("예상치 못한 버튼 텍스트: %s", button_text)

        except TimeoutException:
            LOGGER.info("웰컴 팝업이 나타나지 않음 (이미 처리됨 또는 쿠키 존재)")
        except NoSuchElementException:
            LOGGER.info("웰컴 팝업 요소를 찾을 수 없음")
        except Exception as exc:
            LOGGER.warning("웰컴 팝업 처리 중 예외 발생: %s", exc)

    def search_address(self, address: str) -> bool:
        """
        목적: 주소 검색 및 자동완성 목록 가져오기

        Args:
            address: 검색할 주소 문자열

        Returns:
            검색 성공 여부
        """
        if not address:
            self._notify_error("검색할 주소를 입력해주세요.")
            return False

        if not self.driver:
            self._notify_error("크롤러가 초기화되지 않았습니다.")
            return False

        LOGGER.info("검색 시작: %s", address)
        self._notify("주소를 검색하는 중...")

        try:
            # 뒤로가기 버튼 순차 확인 및 처리
            self._handle_back_buttons()

            # 주소검색 버튼 찾기 및 클릭
            wait = WebDriverWait(self.driver, 4)
            dsv_search_btn = wait.until(
                EC.element_to_be_clickable((By.ID, "dsv_search_btn"))
            )
            self.driver.execute_script("arguments[0].click();", dsv_search_btn)
            LOGGER.info("dsv_search_btn 클릭 완료")
            self._notify("검색 버튼 클릭 완료")

            # 주소 입력 필드에 입력
            address_input = wait.until(
                EC.element_to_be_clickable((By.ID, "top_search_ds_input"))
            )
            address_input.clear()
            address_input.send_keys(address)
            LOGGER.info("주소 입력 완료: %s", address)
            self._notify(f"주소 입력 완료: {address}")

            # 자동완성 생성 대기
            time.sleep(0.5)

            # 자동완성 목록 파싱
            suggestions_container = wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "ds-autocomplete-suggestions")
                )
            )

            suggestion_elements = suggestions_container.find_elements(
                By.CLASS_NAME, "autocomplete-suggestion"
            )
            LOGGER.info("자동완성 항목 %d개 발견", len(suggestion_elements))

            if not suggestion_elements:
                self._notify("자동완성 목록이 비어 있습니다.")
                self.address_list = []
                if self.on_addresses_found:
                    self.on_addresses_found([])
                return False

            # 주소 목록 파싱
            self.address_list = []
            for elem in suggestion_elements:
                try:
                    full_text = elem.text.strip()
                    sub_value_elem = elem.find_element(By.CLASS_NAME, "sub-value")
                    sub_value_text = sub_value_elem.text.strip()
                    main_address = full_text.replace(sub_value_text, "").strip()

                    data_index = elem.get_attribute("data-index")
                    self.address_list.append(
                        {
                            "data_index": data_index,
                            "main": main_address,
                            "sub": sub_value_text,
                            "display": f"{main_address} / {sub_value_text}",
                        }
                    )

                except NoSuchElementException:
                    # sub-value 없는 경우
                    main_address = elem.text.strip()
                    data_index = elem.get_attribute("data-index")
                    self.address_list.append(
                        {
                            "data_index": data_index,
                            "main": main_address,
                            "sub": "",
                            "display": main_address,
                        }
                    )

            LOGGER.info("자동완성 목록 파싱 완료: %d개", len(self.address_list))
            self._notify(f"자동완성 목록 {len(self.address_list)}개 발견")

            # 콜백으로 주소 목록 전달
            if self.on_addresses_found:
                self.on_addresses_found(self.address_list)

            return True

        except TimeoutException:
            self._notify_error("요소를 찾을 수 없음")
            return False
        except Exception as exc:
            self._notify_error(f"검색 중 예외 발생: {exc}")
            return False

    def _handle_back_buttons(self) -> None:
        """
        목적: 뒤로가기 버튼 순차 확인 및 처리
        """
        if not self.driver:
            return

        back_clicked = False

        # 1. foot_back_btn 확인 (상세 페이지 뒤로가기)
        try:
            short_wait = WebDriverWait(self.driver, 0.3)
            foot_back_btn = short_wait.until(
                EC.element_to_be_clickable((By.ID, "foot_back_btn"))
            )
            self.driver.execute_script("arguments[0].click();", foot_back_btn)
            self._notify("상세 페이지에서 메인으로 돌아갔어.")
            back_clicked = True
            LOGGER.info("foot_back_btn 클릭 완료")
        except TimeoutException:
            pass

        # 2. 일반 뒤로가기 버튼 확인
        if not back_clicked:
            try:
                short_wait = WebDriverWait(self.driver, 0.3)
                back_image = short_wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//img[contains(@src, 'back')]")
                    )
                )
                self.driver.execute_script("arguments[0].click();", back_image)
                self._notify("이전 화면으로 돌아갔어.")
                LOGGER.info("일반 뒤로가기 버튼 클릭 완료")
            except TimeoutException:
                pass

    def select_address(self, index: int) -> bool:
        """
        목적: 주소 선택 및 건물 목록 가져오기

        Args:
            index: 선택할 주소의 인덱스 (address_list 기준)

        Returns:
            선택 성공 여부
        """
        if not self.driver:
            self._notify_error("크롤러가 초기화되지 않았습니다.")
            return False

        if index < 0 or index >= len(self.address_list):
            LOGGER.warning("잘못된 인덱스: %d", index)
            self._notify_error(f"잘못된 주소 인덱스: {index}")
            return False

        address_data = self.address_list[index]
        data_index = address_data["data_index"]
        main_address = address_data["main"]

        LOGGER.info("주소 선택: %s (data-index=%s)", main_address, data_index)
        self._notify("선택한 주소를 불러오는 중...")

        try:
            # 웹 페이지에서 해당 data-index 항목 클릭
            wait = WebDriverWait(self.driver, 4)
            suggestion_elem = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        f'.autocomplete-suggestion[data-index="{data_index}"]',
                    )
                )
            )
            self.driver.execute_script("arguments[0].click();", suggestion_elem)
            LOGGER.info("웹 페이지 자동완성 항목 클릭 완료 (data-index=%s)", data_index)
            self._notify(f"주소 선택 완료: {main_address}")

            # 건물 탭 클릭 및 목록 파싱
            return self._load_buildings()

        except TimeoutException:
            error_msg = f"자동완성 항목을 찾을 수 없음 (data-index={data_index})"
            self._notify_error(error_msg)
            return False
        except Exception as exc:
            error_msg = f"주소 선택 중 예외: {exc}"
            self._notify_error(error_msg)
            return False

    def _load_buildings(self) -> bool:
        """
        목적: 건물 탭 클릭 및 건물 목록 파싱

        Returns:
            건물 목록 로드 성공 여부
        """
        if not self.driver:
            LOGGER.warning("크롤러 드라이버가 초기화되지 않음")
            return False

        # 건물 탭 클릭 (재시도 로직 포함)
        for attempt in range(2):
            try:
                LOGGER.info("건물 탭 클릭 시도 중... (시도 %d)", attempt + 1)
                wait = WebDriverWait(self.driver, 5)
                building_tab = wait.until(
                    EC.element_to_be_clickable((By.ID, "dp_navi_4"))
                )
                self.driver.execute_script("arguments[0].click();", building_tab)
                LOGGER.info("건물 탭 클릭 성공")

                # 건물 목록 파싱
                return self._parse_building_list()

            except TimeoutException:
                LOGGER.warning("건물 탭 요소를 찾을 수 없음 (시도 %d)", attempt + 1)
                if attempt == 0:
                    time.sleep(1)  # 재시도 전 대기
            except Exception as exc:
                LOGGER.warning("건물 탭 클릭 실패 (시도 %d): %s", attempt + 1, exc)
                if attempt == 0:
                    time.sleep(1)

        self._notify_error("건물 탭 클릭 최종 실패")
        return False

    def _parse_building_list(self) -> bool:
        """
        목적: 건물 목록 파싱 및 콜백 전달

        Returns:
            파싱 성공 여부
        """
        if not self.driver:
            LOGGER.warning("크롤러 드라이버가 초기화되지 않음")
            return False

        self._notify("건물 목록을 불러오는 중...")

        try:
            # 건물 목록 요소 대기
            wait = WebDriverWait(self.driver, 2)
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "ddiv-build-content"))
            )
            time.sleep(0.5)

            # 건물 요소들 가져오기
            building_elements = self.driver.find_elements(
                By.CLASS_NAME, "ddiv-build-content"
            )

            if not building_elements:
                LOGGER.warning("건물 목록이 없음")
                self._notify("건물 목록이 없습니다.")
                self.building_list = []
                if self.on_buildings_found:
                    self.on_buildings_found([])
                return False

            # 건물 목록 초기화 및 파싱
            self.building_list = []

            for idx, element in enumerate(building_elements):
                try:
                    top_elem = element.find_element(
                        By.CLASS_NAME, "ddiv-build-content-top"
                    )
                    bottom_elem = element.find_element(
                        By.CLASS_NAME, "ddiv-build-content-bottom"
                    )

                    # JavaScript로 텍스트 가져오기
                    top_text = self.driver.execute_script(
                        "return arguments[0].textContent || arguments[0].innerText || '';",
                        top_elem,
                    ).strip()

                    bottom_text = self.driver.execute_script(
                        "return arguments[0].textContent || arguments[0].innerText || '';",
                        bottom_elem,
                    ).strip()

                    # 비어있으면 일반 .text 시도
                    if not top_text:
                        top_text = top_elem.text.strip()
                    if not bottom_text:
                        bottom_text = bottom_elem.text.strip()

                    # 타이틀 요소 가져오기 (선택적)
                    title_text = ""
                    try:
                        title_elem = element.find_element(
                            By.CLASS_NAME, "ddiv-build-content-title"
                        )
                        title_text = self.driver.execute_script(
                            "return arguments[0].textContent || arguments[0].innerText || '';",
                            title_elem,
                        ).strip()
                        if not title_text:
                            title_text = title_elem.text.strip()
                    except NoSuchElementException:
                        pass

                    # 표시 형식 결정
                    if title_text:
                        display_text = f"{top_text}({bottom_text}) [{title_text}]"
                    else:
                        display_text = f"{top_text}({bottom_text})"

                    # 건물 정보 저장
                    building_info = {
                        "index": idx,
                        "top": top_text,
                        "bottom": bottom_text,
                        "title": title_text,
                        "display": display_text,
                    }
                    self.building_list.append(building_info)

                    LOGGER.info("건물 파싱 #%d: %s", idx, display_text)

                except NoSuchElementException:
                    LOGGER.warning("건물 요소 파싱 실패 (인덱스: %d)", idx)
                    continue
                except Exception as exc:
                    LOGGER.warning("건물 정보 추출 실패 (인덱스: %d): %s", idx, exc)
                    continue

            LOGGER.info("건물 목록 파싱 완료: 총 %d개", len(self.building_list))
            self._notify(f"건물 {len(self.building_list)}개를 불러왔습니다.")

            # 콜백으로 건물 목록 전달
            if self.on_buildings_found:
                self.on_buildings_found(self.building_list)

            return True

        except TimeoutException:
            LOGGER.warning("건물 목록 로드 타임아웃")
            self._notify_error("건물 목록을 불러올 수 없습니다.")
            self.building_list = []
            if self.on_buildings_found:
                self.on_buildings_found([])
            return False

        except Exception as exc:
            LOGGER.exception("건물 목록 파싱 중 예외 발생", exc_info=exc)
            self._notify_error("건물 목록 파싱 중 오류가 발생했습니다.")
            self.building_list = []
            if self.on_buildings_found:
                self.on_buildings_found([])
            return False

    def select_building(self, index: int) -> bool:
        """
        목적: 건물 선택 및 상세 정보 크롤링 시작

        Args:
            index: 선택할 건물의 인덱스 (building_list 기준)

        Returns:
            선택 성공 여부
        """
        if not self.driver:
            LOGGER.warning("크롤러 드라이버가 초기화되지 않음")
            self._notify_error("크롤러가 초기화되지 않았습니다.")
            return False

        if index < 0 or index >= len(self.building_list):
            LOGGER.warning("잘못된 건물 인덱스: %d", index)
            self._notify_error(f"잘못된 건물 인덱스: {index}")
            return False

        building_info = self.building_list[index]
        original_index = building_info["index"]

        try:
            # 현재 페이지의 건물 요소들 다시 가져오기
            building_elements = self.driver.find_elements(
                By.CLASS_NAME, "ddiv-build-content"
            )

            if original_index >= len(building_elements):
                LOGGER.error(
                    "인덱스 범위 초과: %d (전체: %d)",
                    original_index,
                    len(building_elements),
                )
                self._notify_error("건물 인덱스 범위 초과")
                return False

            # 선택된 건물 클릭
            target_element = building_elements[original_index]
            self.driver.execute_script("arguments[0].click();", target_element)

            selected_building = building_info["display"]
            LOGGER.info("건물 선택 완료: %s (인덱스: %d)", selected_building, original_index)
            self._notify(f"건물 선택: {selected_building}")

            # 자동으로 크롤링 실행
            return self.perform_crawling()

        except Exception as exc:
            LOGGER.exception("건물 선택 중 예외 발생", exc_info=exc)
            self._notify_error("건물 선택 중 오류가 발생했습니다.")
            return False

    def perform_crawling(self) -> bool:
        """
        목적: 건물 상세 정보 크롤링 실행

        Returns:
            크롤링 성공 여부
        """
        if not self.driver:
            LOGGER.error("크롤러 드라이버가 None 상태")
            self._notify_error("크롤러가 초기화되지 않았습니다.")
            return False

        LOGGER.info("크롤링 시작")
        self._notify("크롤링 중...")

        try:
            # 페이지 로딩 대기
            time.sleep(2)

            # JavaScript로 크롤링
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
                                rightDiv = allTabTxts[1];
                                rightDivMethod = 'second-element';
                            }
                        }

                        let content = '';
                        let usedSelector = '';

                        if (rightDiv) {
                            const contentElem = rightDiv.querySelector('span[id]') ||
                                               rightDiv.querySelector('span');

                            if (contentElem && contentElem.textContent.trim()) {
                                content = contentElem.textContent.trim();
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
                            selector: usedSelector,
                            method: rightDivMethod
                        };
                    })
                    .filter(item => item.title);
            """

            wait = WebDriverWait(self.driver, 5)
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "mfs-agent-main-tab-div"))
            )

            self.crawled_data = self.driver.execute_script(script)

            # 크롤링 결과 로깅
            LOGGER.info("크롤링 완료: %d개 항목", len(self.crawled_data))
            for item in self.crawled_data:
                LOGGER.info("  - %s: %s", item["title"], item["content"])
                LOGGER.debug(
                    "    [디버깅] 선택자: %s, 오른쪽div 탐색: %s",
                    item.get("selector", "unknown"),
                    item.get("method", "unknown"),
                )

                # 값이 없는 경우 경고
                if item["content"] == "값 없음":
                    if item.get("selector") == "no_right_div":
                        LOGGER.warning(
                            "    ⚠️ '%s' 항목: 오른쪽 div를 찾을 수 없음", item["title"]
                        )
                    elif item.get("selector") == "span_empty":
                        LOGGER.warning(
                            "    ⚠️ '%s' 항목: span은 있지만 텍스트가 비어있음",
                            item["title"],
                        )

            self._notify(f"크롤링 완료: {len(self.crawled_data)}개 항목")

            # 콜백으로 크롤링 결과 전달
            if self.on_complete:
                self.on_complete(self.crawled_data)

            return True

        except TimeoutException:
            error_msg = "크롤링 대기 시간 초과"
            self._notify_error(error_msg)
            return False
        except Exception as exc:
            error_msg = f"크롤링 중 예외 발생: {exc}"
            self._notify_error(error_msg)
            return False

    def save_results_to_json(
        self, address: str = "", building: str = ""
    ) -> Optional[Path]:
        """
        목적: 크롤링 결과를 JSON 파일로 저장

        Args:
            address: 선택한 주소
            building: 선택한 건물

        Returns:
            저장된 파일 경로 (실패 시 None)
        """
        if not self.crawled_data:
            LOGGER.warning("저장할 크롤링 데이터가 없음")
            self._notify("저장할 데이터가 없습니다.")
            return None

        try:
            # 결과 저장 경로
            feature_dir = Path(__file__).parent.parent
            results_dir = feature_dir / "data" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)

            # JSON 데이터 구성
            result_data = {
                "timestamp": datetime.now().isoformat(),
                "address": address,
                "building": building,
                "items": [
                    {"title": item["title"], "content": item["content"]}
                    for item in self.crawled_data
                ],
            }

            # 파일 저장
            file_path = results_dir / "latest_crawl.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)

            LOGGER.info("크롤링 결과 저장 완료: %s", file_path)
            self._notify(f"결과를 저장했어: {file_path.name}")

            return file_path

        except Exception as exc:
            error_msg = f"JSON 저장 중 예외 발생: {exc}"
            LOGGER.exception(error_msg)
            self._notify_error(error_msg)
            return None

    def close(self) -> None:
        """
        목적: 드라이버 종료 및 리소스 정리
        """
        if self.driver:
            try:
                self.driver.quit()
                LOGGER.info("드라이버 종료 완료")
                self._notify("크롤러를 종료했어.")
            except Exception as exc:
                LOGGER.warning("드라이버 종료 중 예외: %s", exc)
            finally:
                self.driver = None
