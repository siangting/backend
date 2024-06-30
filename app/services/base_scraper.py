from abc import ABC, abstractmethod
from .openai_client import openai_client
from ..models import NewsArticle, Session

class BaseScraper(ABC):
    def __init__(self, base_url):
        self.base_url = base_url

    @abstractmethod
    def fetch_news_data(self, search_term):
        pass

    @abstractmethod
    def news_parser(self, news_url):
        pass
    
    def save_news_content(self, news_data):
        session = Session()
        exists = session.query(NewsArticle).filter_by(url=news_data['url']).first() is not None
        if not exists:
            new_article = NewsArticle(
                url=news_data['url'],
                title=news_data['title'],
                time=news_data['time'],
                content=' '.join(news_data['content'])  # 將內容list轉換為字串
            )
            session.add(new_article)
            session.commit()
        session.close()

    def evaluate_relevance(self, title):
        messages=[
            {"role": "system", "content":"你是一個關聯度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)"},
            {"role": "user", "content": f"{title}"}
        ]
        return openai_client.generate_text(messages=messages)
        
