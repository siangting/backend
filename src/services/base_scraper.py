from abc import ABC, abstractmethod

from ..models import NewsArticle, Session


class BaseScraper(ABC):
    def __init__(self, base_url):
        self.base_url = base_url

    @abstractmethod
    def fetch_news_data(self, search_term, is_initial=False):
        raise NotImplementedError()

    @abstractmethod
    def news_parser(self, news_url):
        raise NotImplementedError()

    def save_news_content(self, news_data):
        session = Session()
        exists = (
            session.query(NewsArticle).filter_by(url=news_data["url"]).first()
            is not None
        )
        if not exists:
            new_article = NewsArticle(
                url=news_data["url"],
                title=news_data["title"],
                time=news_data["time"],
                content=" ".join(news_data["content"]),  # 將內容list轉換為字串
                summary=news_data["summary"],
                reason=news_data["reason"],
            )
            session.add(new_article)
            session.commit()
        session.close()
