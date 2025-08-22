from typing import List
import asyncio
from bs4 import BeautifulSoup
import logging

from ..models.Contest import ContestModel
from .base import BaseScraper

logger = logging.getLogger(__name__)


class AllforyoungScraper(BaseScraper):
    """

        요즘것들(Allforyoung)

    """

    def __init__(self):
        super().__init__(
            name="Allforyoung",
            base_url="https://www.allforyoung.com"
        )


    def get_page_urls(self) -> List[str]:
        base_url = "https://www.allforyoung.com/posts/contest?tags=20"
        urls = [base_url+f"&page={i}" for i in range(1, 4)]

        return urls


    async def _scrape_page(self, page_url: str):
        """

            for update ver 3.0
            we will not using other organizer page
            this is temporary code

        """

        contests = []

        try:
            content, status = await self.fetch_page(page_url)
            if status != 200:
                raise Exception(f"HTTP {status}", self.name, page_url)

            soup = BeautifulSoup(content, 'html.parser')

            result = self.parse_contest(soup)
            if result:
                contests.append(result)

        except Exception as e:
            logger.error(f"[Scrap] {self.name}: Error scraping page {page_url}: {e}")
            raise


    async def _scrape_detail_page(self, contest: ContestModel):
        """

            for update ver 3.0
            we will not using other organizer page

        """
        pass


    def parse_contest(self, soup: BeautifulSoup):
        try:
            cards = soup.select(
                "body > div > div:nth-child(2) > main > section > div.main-responsive > div > div.space-y-20 > ul > a > div > div"
            )


            for card in cards:
                image = card.select_one("figure > img")

        except Exception as e:
            raise Exception(f"Parse error: {e}", self.name)
