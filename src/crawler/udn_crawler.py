"""
UDN News Scraper Module

This module provides the UDNCrawler class for fetching, parsing, and saving news articles from the UDN website.
The class extends the NewsCrawlerBase and includes functionalities to search for news articles based on a search term,
parse the details of individual articles, and save them to a database using SQLAlchemy ORM.

Classes:
    UDNCrawler: A class to scrape news from UDN.

Exceptions:
    DomainMismatchException: Raised when the URL domain does not match the expected domain for the crawler.

Usage Example:
    crawler = UDNCrawler(timeout=10)
    headlines = crawler.startup("technology")
    for headline in headlines:
        news = crawler.parse(headline.url)
        crawler.save(news, db_session)

UDNCrawler Methods:
    __init__(self, timeout: int = 5): Initializes the crawler with a default timeout for HTTP requests.
    startup(self, search_term: str) -> list[Headline]: Fetches news headlines for a given search term across multiple pages.
    get_headline(self, search_term: str, page: int | tuple[int, int]) -> list[Headline]: Fetches news headlines for specified pages.
    _fetch_news(self, page: int, search_term: str) -> list[Headline]: Helper method to fetch news headlines for a specific page.
    _create_search_params(self, page: int, search_term: str): Creates the parameters for the search request.
    _perform_request(self, params: dict): Performs the HTTP request to fetch news data.
    _parse_headlines(response): Parses the response to extract headlines.
    parse(self, url: str) -> News: Parses a news article from a given URL.
    _extract_news(soup, url: str) -> News: Extracts news details from the BeautifulSoup object.
    save(self, news: News, db: Session): Saves a news article to the database.
    _commit_changes(db: Session): Commits the changes to the database with error handling.
"""

from urllib.parse import quote
import requests
from requests import Response
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.models import NewsArticle
from .base import NewsCrawlerBase, Headline, News, NewsWithSummary
from .exceptions import DomainMismatchException


class UDNCrawler(NewsCrawlerBase):
    CHANNEL_ID = 2

    def __init__(self, timeout: int = 5) -> None:
        self.news_website_url = "https://udn.com/api/more"
        self.timeout = timeout

    def startup(self, search_term: str) -> list[Headline]:
        """
        Initializes the application by fetching news headlines for a given search term across multiple pages.
        This method is typically called at the beginning of the program when there is no data available,
        hence it fetches headlines from the first 10 pages.

        :param search_term: The term to search for in news headlines.
        :return: A list of Headline namedtuples containing the title and URL of news articles.
        :rtype: list[Headline]
        """
        return self.get_headline(search_term, page=(1, 10))

    def get_headline(
        self, search_term: str, page: int | tuple[int, int]
    ) -> list[Headline]:

        # Calculate the range of pages to fetch news from.
        # If 'page' is a tuple, unpack it and create a range representing those pages (inclusive).
        # If 'page' is an int, create a list containing only that single page number.
        page_range = range(*page) if isinstance(page, tuple) else [page]
        headlines = [
            headline
            for p in page_range
            for headline in self._fetch_news(p, search_term)
        ]
        return headlines

    def _fetch_news(self, page: int, search_term: str) -> list[Headline]:
        params = self._create_search_params(page, search_term)
        response = self._perform_request(params=params)
        return self._parse_headlines(response) if response else []

    def _create_search_params(self, page: int, search_term: str) -> dict:
        quote_search_term = quote(search_term)
        return {
            "page": page,
            "id": f"search:{quote_search_term}",
            "channelId": self.CHANNEL_ID,
            "type": "searchword",
        }

    def _perform_request(self, url: str | None = None, params: dict | None = None) -> Response:
        if not url:
            url = self.news_website_url

        if not params:
            params = {}


        try:
            response = requests.get(
                url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise ConnectionError(f"Error fetching news: {e}") from e

    @staticmethod
    def _parse_headlines(response: Response) -> list[Headline]:
        data = response.json().get("lists", [])
        return [
            Headline(title=article["title"], url=article["titleLink"])
            for article in data
        ]

    def parse(self, url: str) -> News:
        if not self._is_valid_url(url):
            raise DomainMismatchException(url)
        response = self._perform_request(url=url)
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_news(soup, url)

    @staticmethod
    def _extract_news(soup: BeautifulSoup, url: str) -> News:
        title = soup.select_one("h1.article-content__title").text
        time = soup.select_one("time.article-content__time").text
        content = " ".join(
            p.text
            for p in soup.select("section.article-content__editor p")
            if p.text.strip()
        )
        return News(url=url, title=title, time=time, content=content, reason="", summary="")

    def save(self, news: NewsWithSummary, db: Session):
        existing_news = db.query(NewsArticle).filter_by(url=news.url).first()
        if not existing_news:
            new_article = NewsArticle(
                url=news.url, title=news.title, time=news.time, content=news.content, summary=news.summary, reason=news.reason
            )
            db.add(new_article)
            self._commit_changes(db)

    @staticmethod
    def _commit_changes(db: Session):
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Error saving news to database: {e}") from e
        finally:
            db.close()