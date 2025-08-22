from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import asyncio
import aiohttp
from aiohttp import ClientTimeout, ClientSession
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..models import Contest, Service_status, ScrapingResult

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """기본 스크래퍼 클래스

    모든 스크래퍼가 상속받아야 하는 추상 클래스로,
    공통 기능들을 제공합니다.
    """

    def __init__(self,
                 name: str,
                 base_url: str,
                 timeout: int = 30,
                 max_retries: int = 3,
                 delay_between_requests: float = 1.0):
        """
        Args:
            name: 스크래퍼 이름 (예: "wevity", "linkareer")
            base_url: 기본 URL
            timeout: HTTP 요청 타임아웃 (초)
            max_retries: 재시도 횟수
            delay_between_requests: 요청 간 지연시간 (초)
        """
        self.name = name
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay_between_requests = delay_between_requests
        self.session: Optional[ClientSession] = None

        # 통계 정보
        self.stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'contests_found': 0,
            'contests_parsed': 0,
            'parsing_errors': 0,
        }

        # 기본 헤더
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/138.0.7204.169 Safari/537.36"
        }

        logger.info(f"[Scrap] Initialized {self.name} scraper")

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close_session()

    async def start_session(self) -> None:
        """HTTP 세션 시작"""
        if self.session is None or self.session.closed:
            timeout = ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=10,  # 전체 연결 수 제한
                limit_per_host=5,  # 호스트별 연결 수 제한
                ttl_dns_cache=300,  # DNS 캐시 TTL
                use_dns_cache=True
            )

            self.session = ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self.header,
                trust_env=True
            )

            logger.debug(f"[Scrap] {self.name}: HTTP session started")

    async def close_session(self) -> None:
        """HTTP 세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug(f"[Scrap] {self.name}: HTTP session closed")

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def fetch_page(self, url: str, **kwargs) -> tuple[str, int]:
        """

        웹 페이지 가져오기

        Args:
            url: 요청할 URL
            **kwargs: aiohttp 요청에 전달할 추가 인자

        Returns:
            tuple[str, int]: (페이지 내용, HTTP 상태코드)

        """
        if not self.session:
            await self.start_session()

        self.stats['requests_made'] += 1

        try:
            logger.debug(f"[Scrap] {self.name}: Fetching {url}")

            async with self.session.get(url, **kwargs) as response:
                content = await response.text()
                status = response.status

                if status == 200:
                    self.stats['successful_requests'] += 1
                    logger.debug(f"[Scrap] {self.name}: Successfully fetched {url}")
                else:
                    self.stats['failed_requests'] += 1
                    logger.warning(f"[Scrap] {self.name}: HTTP {status} for {url}")

                # 요청 간 지연
                if self.delay_between_requests > 0:
                    await asyncio.sleep(self.delay_between_requests)

                return content, status

        except asyncio.TimeoutError:
            self.stats['failed_requests'] += 1
            error_msg = f"Timeout fetching {url}"
            logger.error(f"[Scrap] {self.name}: {error_msg}")
            raise TimeoutError(error_msg)

        except aiohttp.ClientError as e:
            self.stats['failed_requests'] += 1
            error_msg = f"Network error fetching {url}: {e}"
            logger.error(f"[Scrap] {self.name}: {error_msg}")
            raise TimeoutError(error_msg)

        except Exception as e:
            self.stats['failed_requests'] += 1
            error_msg = f"Unexpected error fetching {url}: {e}"
            logger.error(f"[Scrap] {self.name}: {error_msg}")
            raise TimeoutError(error_msg)

    async def scrape_with_retry(self) -> ScrapingResult:
        """재시도 로직이 포함된 스크래핑 실행

        Returns:
            ScrapingResult
        """
        start_time = datetime.now()
        error_message = None
        contests = []

        try:
            logger.info(f"[Scrap] {self.name}: Starting scraping")

            async for contest in self.scrape():
                contests.append(contest)
                self.stats['contests_found'] += 1

            logger.info(f"[Scrap] {self.name}: Scraping completed. Found {len(contests)} contests")
            success = True

        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"[Scrap] {self.name}: Scraping failed: {e}", exc_info=True)

        duration = (datetime.now() - start_time).total_seconds()

        return ScrapingResult(
            site_name=self.name,
            success=success,
            scraped_count=len(contests),
            saved_count=0,  # 저장은 상위 서비스에서 처리
            duration_seconds=duration,
            error_message=error_message
        )

    def parse_contest_safely(self, raw_data: Any, context: str = "") -> Optional[Contest]:
        """안전한 공모전 데이터 파싱

        Args:
            raw_data: 파싱할 원시 데이터
            context: 디버깅용 컨텍스트 정보

        Returns:
            Optional[Contest]: 파싱된 공모전 정보 또는 None
        """
        try:
            contest = self.parse_contest(raw_data)
            if contest:
                self.stats['contests_parsed'] += 1
                logger.debug(f"[Scrap] {self.name}: Parsed contest: {contest.title[:50]}...")
            return contest

        # except ParseError as e:
        #     self.stats['parsing_errors'] += 1
        #     logger.warning(f"{self.name}: Parse error {context}: {e}")
        #     return None

        except Exception as e:
            self.stats['parsing_errors'] += 1
            logger.error(f"[Scrap] {self.name}: parse error {context}: {e}")
            return None

    def get_full_url(self, relative_url: str) -> str:
        """상대 URL을 절대 URL로 변환

        Args:
            relative_url: 상대 URL

        Returns:
            str: 절대 URL
        """
        if not relative_url:
            return ""

        if relative_url.startswith(('http://', 'https://')):
            return relative_url

        if relative_url.startswith('//'):
            return f"https:{relative_url}"

        if relative_url.startswith('/'):
            return f"{self.base_url.rstrip('/')}{relative_url}"

        return f"{self.base_url.rstrip('/')}/{relative_url}"

    def get_stats(self) -> Dict[str, Any]:
        """스크래핑 통계 정보 반환"""
        return {
            'scraper_name': self.name,
            'requests': {
                'total': self.stats['requests_made'],
                'successful': self.stats['successful_requests'],
                'failed': self.stats['failed_requests'],
                'success_rate': (
                        self.stats['successful_requests'] / max(1, self.stats['requests_made']) * 100
                )
            },
            'contests': {
                'found': self.stats['contests_found'],
                'parsed': self.stats['contests_parsed'],
                'parsing_errors': self.stats['parsing_errors'],
                'parse_success_rate': (
                        self.stats['contests_parsed'] / max(1, self.stats['contests_found']) * 100
                )
            }
        }

    def reset_stats(self) -> None:
        """통계 정보 초기화"""
        for key in self.stats:
            self.stats[key] = 0

    # 추상 메서드들 - 각 스크래퍼에서 구현해야 함

    @abstractmethod
    async def scrape(self):
        """공모전 정보 스크래핑

        Contest 객체들을 비동기적으로 yield

        Yields:
            Contest: 스크래핑된 공모전 정보

        Raises:
            ScrapingError: 스크래핑 중 오류 발생 시
        """

        page_urls = self.get_page_urls()

        tasks = [self._scrape_page(url) for url in page_urls]
        page_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in page_results:
            if isinstance(result, Exception):
                logger.error(f"[Scrap] {self.name}: Page scraping failed: {result}")
                continue

            for contest in result:
                yield contest

    @abstractmethod
    async def _scrape_page(self, page_url: str):
        """

            Wevity : OK

            allforyoung:
                for update ver 3.0
                we will not using other organizer page

        """
        pass

    @abstractmethod
    def parse_contest(self, raw_data: Any):
        """원시 데이터를 ContestModel 객체로 파싱

        Args:
            raw_data: 파싱할 원시 데이터 (BeautifulSoup 요소, dict 등)

        Returns:
            Optional[Contest]: 파싱된 Contest 객체 또는 None

        Raises:
            ParseError: 파싱 중 오류 발생 시
        """
        pass

    @abstractmethod
    def get_page_urls(self) -> List[str]:
        """스크래핑할 페이지 URL 목록 반환

        Returns:
            List[str]: 스크래핑할 URL 리스트
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', base_url='{self.base_url}')>"