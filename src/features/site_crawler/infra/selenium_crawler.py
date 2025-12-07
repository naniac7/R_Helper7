"""
레이어: infra
역할: Selenium 기반 크롤러 구현
의존: domain/models, infra/chrome_driver_manager
외부: time, typing, selenium, src.shared.logging.app_logger

목적: 기존 core/site_crawler.py의 Selenium 로직을 이동하되,
- 콜백 제거 → 순수 반환값으로 변경
- 인스턴스 변수(address_list, building_list) 제거 → 지역 변수 사용
- 메서드 분리: select_address() + get_buildings()
"""

import time
from typing import Optional
from selenium import webdriver
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.features.site_crawler.infra.chrome_driver_manager import get_chrome_driver
from src.features.site_crawler.domain.models import Address, Building, CrawlItem
from src.shared.logging.app_logger import get_logger

LOGGER = get_logger()


class SeleniumCrawler:
    """
    Selenium 기반 크롤러
    목적: 상태 없는 순수 크롤링 로직 제공
    """

    def __init__(self):
        """
        목적: 크롤러 초기화
        """
        self.driver: Optional[webdriver.Chrome] = None

    def init_driver(self, headless: bool = False) -> bool:
        """
        목적: Chrome 드라이버 초기화 및 disco.re 접속

        Args:
            headless: 헤드리스 모드 사용 여부

        Returns:
            초기화 성공 여부
        """
        try:
            LOGGER.info("Chrome 드라이버 초기화 중...")
            self.driver = get_chrome_driver(headless=headless)

            # disco.re 사이트로 이동
            self.driver.get("https://disco.re")
            LOGGER.info("disco.re 사이트 접속 완료")

            # 웰컴 팝업 처리
            self._handle_welcome_popup()

            LOGGER.info("크롤링용 Chrome 창 준비 완료")
            return True

        except WebDriverException as exc:
            LOGGER.error("Chrome 드라이버 초기화 실패: %s", exc)
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
                time.sleep(0.5)
            else:
                LOGGER.warning("예상치 못한 버튼 텍스트: %s", button_text)

        except TimeoutException:
            LOGGER.info("웰컴 팝업이 나타나지 않음 (이미 처리됨 또는 쿠키 존재)")
        except NoSuchElementException:
            LOGGER.info("웰컴 팝업 요소를 찾을 수 없음")
        except Exception as exc:
            LOGGER.warning("웰컴 팝업 처리 중 예외 발생: %s", exc)

    def search_address(self, address: str) -> list[Address]:
        """
        목적: 주소 검색 및 자동완성 목록 반환 (상태 저장 안 함)

        Args:
            address: 검색할 주소

        Returns:
            Address 엔티티 리스트

        Raises:
            RuntimeError: 크롤러가 초기화되지 않았을 때
            TimeoutException: 요소를 찾을 수 없을 때
        """
        if not self.driver:
            raise RuntimeError("크롤러가 초기화되지 않았습니다.")

        LOGGER.info("주소 검색 시작: %s", address)

        # 뒤로가기 버튼 순차 확인 및 처리
        self._handle_back_buttons()

        # 주소검색 버튼 찾기 및 클릭
        wait = WebDriverWait(self.driver, 4)
        dsv_search_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "dsv_search_btn"))
        )
        self.driver.execute_script("arguments[0].click();", dsv_search_btn)
        LOGGER.info("dsv_search_btn 클릭 완료")

        # 주소 입력 필드에 입력
        address_input = wait.until(
            EC.element_to_be_clickable((By.ID, "top_search_ds_input"))
        )
        address_input.clear()
        address_input.send_keys(address)
        LOGGER.info("주소 입력 완료: %s", address)

        # 자동완성 생성 대기
        # 이유: 동적 대기(wait.until)만으로는 자동완성 데이터 바인딩 완료를 보장할 수 없음
        # 요소가 DOM에 나타나도 내부 데이터가 아직 렌더링 중일 수 있어 sleep 유지
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

        # Address 엔티티 생성 (지역 변수)
        addresses = []
        for elem in suggestion_elements:
            try:
                full_text = elem.text.strip()
                sub_value_elem = elem.find_element(By.CLASS_NAME, "sub-value")
                sub_value_text = sub_value_elem.text.strip()
                main_address = full_text.replace(sub_value_text, "").strip()

                data_index = elem.get_attribute("data-index")
                addresses.append(
                    Address(
                        data_index=data_index,
                        main=main_address,
                        sub=sub_value_text,
                        display=f"{main_address} / {sub_value_text}",
                    )
                )

            except NoSuchElementException:
                # sub-value 없는 경우
                main_address = elem.text.strip()
                data_index = elem.get_attribute("data-index")
                addresses.append(
                    Address(
                        data_index=data_index,
                        main=main_address,
                        sub="",
                        display=main_address,
                    )
                )

        LOGGER.info("주소 목록 파싱 완료: %d개", len(addresses))
        return addresses

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
                LOGGER.info("일반 뒤로가기 버튼 클릭 완료")
            except TimeoutException:
                pass

    def select_address(self, index: int) -> None:
        """
        목적: 주소 선택만 수행 (건물 목록 조회는 get_buildings 사용)

        Args:
            index: 선택할 주소의 인덱스 (search_address 결과 기준)

        Raises:
            RuntimeError: 크롤러가 초기화되지 않았을 때
            ValueError: 잘못된 인덱스일 때
        """
        if not self.driver:
            raise RuntimeError("크롤러가 초기화되지 않았습니다.")

        # 현재 페이지의 자동완성 항목들을 다시 가져옴
        wait = WebDriverWait(self.driver, 4)
        suggestions_container = wait.until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "ds-autocomplete-suggestions")
            )
        )

        suggestion_elements = suggestions_container.find_elements(
            By.CLASS_NAME, "autocomplete-suggestion"
        )

        if index < 0 or index >= len(suggestion_elements):
            raise ValueError(f"잘못된 주소 인덱스: {index}")

        # 선택한 항목 클릭
        target_elem = suggestion_elements[index]
        self.driver.execute_script("arguments[0].click();", target_elem)
        LOGGER.info("주소 선택 완료 (인덱스: %d)", index)

    def get_buildings(self) -> list[Building]:
        """
        목적: 현재 페이지의 건물 목록 파싱 및 반환

        Returns:
            Building 엔티티 리스트

        Raises:
            RuntimeError: 크롤러가 초기화되지 않았거나 건물 탭 클릭 실패
        """
        if not self.driver:
            raise RuntimeError("크롤러가 초기화되지 않았습니다.")

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
                break
            except TimeoutException:
                LOGGER.warning("건물 탭 요소를 찾을 수 없음 (시도 %d)", attempt + 1)
                if attempt == 0:
                    time.sleep(1)  # 재시도 전 대기
                else:
                    raise RuntimeError("건물 탭 클릭 최종 실패")
            except Exception as exc:
                LOGGER.warning("건물 탭 클릭 실패 (시도 %d): %s", attempt + 1, exc)
                if attempt == 0:
                    time.sleep(1)
                else:
                    raise RuntimeError(f"건물 탭 클릭 최종 실패: {exc}")

        # 건물 목록 요소 대기
        wait = WebDriverWait(self.driver, 2)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ddiv-build-content")))
        # 이유: 동적 대기 후에도 건물 목록 내부 데이터 렌더링 시간 필요
        # 요소 존재 확인과 데이터 바인딩 완료는 다름
        time.sleep(0.5)

        # 건물 요소들 가져오기
        building_elements = self.driver.find_elements(By.CLASS_NAME, "ddiv-build-content")

        if not building_elements:
            LOGGER.warning("건물 목록이 없음")
            return []

        # Building 엔티티 생성 (지역 변수)
        buildings = []

        for idx, element in enumerate(building_elements):
            try:
                top_elem = element.find_element(By.CLASS_NAME, "ddiv-build-content-top")
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
                buildings.append(
                    Building(
                        index=idx,
                        top=top_text,
                        bottom=bottom_text,
                        title=title_text,
                        display=display_text,
                    )
                )

                LOGGER.info("건물 파싱 #%d: %s", idx, display_text)

            except NoSuchElementException:
                LOGGER.warning("건물 요소 파싱 실패 (인덱스: %d)", idx)
                continue
            except Exception as exc:
                LOGGER.warning("건물 정보 추출 실패 (인덱스: %d): %s", idx, exc)
                continue

        LOGGER.info("건물 목록 파싱 완료: 총 %d개", len(buildings))
        return buildings

    def select_building(self, index: int) -> None:
        """
        목적: 건물 선택 및 상세 페이지 전환 대기

        Args:
            index: 선택할 건물의 인덱스 (get_buildings 결과 기준)

        Raises:
            RuntimeError: 크롤러가 초기화되지 않았을 때
            ValueError: 잘못된 인덱스일 때
            TimeoutException: 상세 페이지 로딩 타임아웃 (5초)
        """
        if not self.driver:
            raise RuntimeError("크롤러가 초기화되지 않았습니다.")

        # 현재 페이지의 건물 요소들 다시 가져오기
        building_elements = self.driver.find_elements(By.CLASS_NAME, "ddiv-build-content")

        if index < 0 or index >= len(building_elements):
            raise ValueError(f"잘못된 건물 인덱스: {index}")

        # 선택된 건물 클릭
        target_element = building_elements[index]
        self.driver.execute_script("arguments[0].click();", target_element)
        LOGGER.info("건물 선택 완료 (인덱스: %d)", index)

        # 상세 페이지 전환 대기 (동적 대기)
        wait = WebDriverWait(self.driver, 5)
        wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "mfs-agent-main-tab-div"))
        )
        LOGGER.info("상세 페이지 로딩 완료")

    def perform_crawling(self) -> list[CrawlItem]:
        """
        목적: 건물 상세 정보 크롤링

        Returns:
            CrawlItem 엔티티 리스트

        Raises:
            RuntimeError: 크롤러가 초기화되지 않았을 때
            TimeoutException: 크롤링 대상 요소 로딩 타임아웃 (5초)
        """
        if not self.driver:
            raise RuntimeError("크롤러가 초기화되지 않았습니다.")

        LOGGER.info("크롤링 시작")

        # 동적 대기: 크롤링 대상 요소가 로드될 때까지 대기 (최대 5초)
        # 이유: select_building에서 이미 대기했지만, 직접 호출 시에도 안전하게 처리
        wait = WebDriverWait(self.driver, 5)
        wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "mfs-agent-main-tab-div"))
        )

        # JavaScript로 크롤링
        script = """
            return Array.from(document.querySelectorAll('.mfs-agent-main-tab-div'))
                .map(div => {
                    const titleElem = div.querySelector('.ifs-tab-txt');

                    // 오른쪽 div 찾기 - 방법1: rfc-dusk 클래스
                    let rightDiv = div.querySelector('.ifs-tab-txt.rfc-dusk');

                    // 방법2: rfc-dusk가 없으면 두 번째 ifs-tab-txt 요소
                    if (!rightDiv) {
                        const allTabTxts = div.querySelectorAll('.ifs-tab-txt');
                        if (allTabTxts.length >= 2) {
                            rightDiv = allTabTxts[1];
                        }
                    }

                    let content = '';

                    if (rightDiv) {
                        const contentElem = rightDiv.querySelector('span[id]') ||
                                           rightDiv.querySelector('span');

                        if (contentElem && contentElem.textContent.trim()) {
                            content = contentElem.textContent.trim();
                        } else {
                            content = '값 없음';
                        }
                    } else {
                        content = '값 없음';
                    }

                    return {
                        title: titleElem ? titleElem.textContent.trim() : '',
                        content: content
                    };
                })
                .filter(item => item.title);
        """

        crawled_data = self.driver.execute_script(script)

        # CrawlItem 엔티티 생성
        items = [
            CrawlItem(title=item["title"], content=item["content"]) for item in crawled_data
        ]

        # 크롤링 결과 로깅
        LOGGER.info("크롤링 완료: %d개 항목", len(items))
        for item in items:
            LOGGER.info("  - %s: %s", item.title, item.content)
            # 값이 없는 경우 경고
            if item.content == "값 없음":
                LOGGER.warning("    ⚠️ '%s' 항목: 값을 찾을 수 없음", item.title)

        return items

    def close(self) -> None:
        """
        목적: 드라이버 종료 및 리소스 정리
        """
        if self.driver:
            try:
                self.driver.quit()
                LOGGER.info("드라이버 종료 완료")
            except Exception as exc:
                LOGGER.warning("드라이버 종료 중 예외: %s", exc)
            finally:
                self.driver = None