from typing import List
import asyncio
from bs4 import BeautifulSoup
import logging

from ..models.Contest import ContestModel
from .base import BaseScraper

logger = logging.getLogger(__name__)


class WevityScraper(BaseScraper):
    """

        위비티(Wevity)

    """

    def __init__(self):
        super().__init__(
            name="wevity",
            base_url="https://www.wevity.com",
            timeout=30,
            max_retries=3,
            delay_between_requests=1.5  # 위비티는 좀 더 여유있게
        )

    def get_page_urls(self) -> List[str]:
        """스크래핑할 페이지 URL 목록"""
        base_urls = [
            "https://www.wevity.com/index.php?c=find&s=1&gub=1&cidx=21",
            "https://www.wevity.com/index.php?c=find&s=1&gub=1&cidx=20",
            "https://www.wevity.com/index.php?c=find&s=1&gub=1&cidx=22",
        ]

        urls = []
        for base_url in base_urls:
            urls.append(base_url)
            urls.append(f"{base_url}&gp=2")

        return urls

    # async def scrape(self):
    #     """위비티 공모전 스크래핑"""
    #     page_urls = self.get_page_urls()
    #
    #     # 모든 페이지 동시 요청
    #     tasks = [self._scrape_page(url) for url in page_urls]
    #     page_results = await asyncio.gather(*tasks, return_exceptions=True)
    #
    #     for result in page_results:
    #         if isinstance(result, Exception):
    #             logger.error(f"[Scrap] {self.name}: Page scraping failed: {result}")
    #             continue
    #
    #         # 각 페이지에서 가져온 공모전들을 yield
    #         for contest in result:
    #             yield contest

    async def _scrape_page(self, page_url: str):
        """개별 페이지 스크래핑"""
        contests = []

        try:
            # 목록 페이지 가져오기
            content, status = await self.fetch_page(page_url)
            if status != 200:
                raise Exception(f"HTTP {status}", self.name, page_url)

            soup = BeautifulSoup(content, 'html.parser')

            # 상세 페이지 링크들 추출
            detail_links = soup.select(
                "body > div > div:nth-child(2) > main > section > div.main-responsive > div > div.space-y-20 > ul > a"
            )
            if not detail_links:
                detail_links = soup.select("ul.list > li > div.tit > a")

            detail_urls = [
                self.get_full_url(link.get("href"))
                for link in detail_links
            ]

            logger.info(f"[Scrap] {self.name}: Found {len(detail_urls)} contests in {page_url}")

            # 상세 페이지들 병렬 처리 (배치 크기 제한)
            batch_size = 10
            for i in range(0, len(detail_urls), batch_size):
                batch = detail_urls[i:i + batch_size]
                batch_tasks = [self._scrape_detail_page(url) for url in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"[Scrap] {self.name}: Detail page failed: {result}")
                        continue
                    if result:
                        contests.append(result)

                # 배치 간 잠시 대기
                if i + batch_size < len(detail_urls):
                    await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"[Scrap] {self.name}: Error scraping page {page_url}: {e}")
            raise

        return contests

    async def _scrape_detail_page(self, detail_url: str):
        """상세 페이지에서 공모전 정보 추출"""
        try:
            content, status = await self.fetch_page(detail_url)
            if status != 200:
                return None

            soup = BeautifulSoup(content, 'html.parser')
            return self.parse_contest(soup)

        except Exception as e:
            logger.debug(f"[Scrap] {self.name}: Failed to parse detail page {detail_url}: {e}")
            return None

    def parse_contest(self, soup: BeautifulSoup):
        """BeautifulSoup으로 파싱된 상세 페이지에서 공모전 정보 추출"""
        try:
            # 이미지
            img_elem = soup.select_one("div.thumb > img")
            image_url = ""
            if img_elem and img_elem.get("src"):
                image_url = self.get_full_url(img_elem.get("src"))

            # 제목
            title_elem = soup.select_one("div.tit-area > h6.tit")
            if not title_elem:
                raise Exception("Title not found", self.name)
            title = title_elem.get_text(strip=True)

            # 상세 정보 카드들
            cards = soup.select("ul.cd-info-list > li")
            if len(cards) < 8:
                raise Exception("Insufficient detail cards", self.name)

            # 분야 확인 (영상/UCC/사진, 예체능/미술/음악 제외)
            field_text = cards[0].get_text().replace(",", "").split()
            excluded_fields = ["영상/UCC/사진", "예체능/미술/음악"]
            if any(excluded in field_text for excluded in excluded_fields):
                return None

            # 참가자격 확인 (일반인 포함 여부)
            eligibility_text = cards[1].get_text()
            if "일반인" not in eligibility_text and "제한없음" not in eligibility_text:
                return None

            # 주최/주관
            organizer_parts = cards[2].get_text(strip=True).split("\n")
            organization = ""
            if len(organizer_parts) > 1:
                organization = organizer_parts[1].replace("\t", "").strip()

            # 마감일
            d_day_parts = cards[4].get_text(strip=True).split()
            deadline = ""
            if d_day_parts:
                deadline = d_day_parts[-1]

            # 홈페이지/링크
            link_parts = cards[7].get_text(strip=True).split()
            contest_url = ""
            if link_parts:
                contest_url = link_parts[-1]
                if not contest_url.startswith(('http://', 'https://')):
                    contest_url = f"https://{contest_url}"

            # 필수 정보 검증
            if not all([title, organization, deadline, contest_url]):
                raise Exception("Missing required fields", self.name)

            # Contest 객체 생성
            contest = ContestModel(
                title=title,
                organization=organization,
                img_url=image_url,
                detail_url=contest_url,
                deadline=deadline,
                d_day=int(deadline[2:]),
                site=self.name
            )
            return contest

        except Exception as e:
            raise Exception(f"Parse error: {e}", self.name)
