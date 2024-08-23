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
    perform_request(self, params: dict): Performs the HTTP request to fetch news data.
    parse_headlines(response): Parses the response to extract headlines.
    parse(self, url: str) -> News: Parses a news article from a given URL.
    extract_news(soup, url: str) -> News: Extracts news details from the BeautifulSoup object.
    save(self, news: News, db: Session): Saves a news article to the database.
    commit_changes(db: Session): Commits the changes to the database with error handling.
"""

from urllib.parse import quote
import requests
from requests import Response
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.models import NewsArticle
from .base import Headline, News, NewsWithSummary


class UDNCrawler():
    CHANNEL_ID = 2

    def __init__(self, timeout = 5):
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
        headlines = []
        for p in range(1, 10):
            params = {
                "page": p,
                "id": f"search:{quote(search_term)}",
                "channelId": self.CHANNEL_ID,
                "type": "searchword",
            }
            response = self.perform_request(params=params)
            headline_list = self.parse_headlines(response) if response else []
            for headline in headline_list:
                headlines.append(headline)
        return headlines

    def get_headline(self, search_term, page):
        headlines = []
        page_range = range(*page) if isinstance(page, tuple) else [page]
        for p in page_range:
            params = {
                "page": p,
                "id": f"search:{quote(search_term)}",
                "channelId": self.CHANNEL_ID,
                "type": "searchword",
            }
            response = self.perform_request(params=params)
            headline_list = self.parse_headlines(response) if response else []
            for headline in headline_list:
                headlines.append(headline)
        return headlines

    def perform_request(self, url = None, params = None) -> Response:
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
    def parse_headlines(response: Response):
        data = response.json().get("lists", [])
        return [
            Headline(title=article["title"], url=article["titleLink"])
            for article in data
        ]

    def parse(self, url):
        response = self.perform_request(url=url)
        soup = BeautifulSoup(response.text, "html.parser")
        return self.extract_news(soup, url)

    @staticmethod
    def extract_news(soup: BeautifulSoup, url):
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
            self.commit_changes(db)

    @staticmethod
    def commit_changes(db: Session):
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Error saving news to database: {e}") from e
        finally:
            db.close()

