from fastapi import APIRouter
from sqlalchemy.orm import Session
from ....models import NewsArticle, Session, engine

router = APIRouter()

@router.get("/news", response_model=list)
def read_news():
    session = Session(bind=engine)
    try:
        news_list = session.query(NewsArticle).all()
        return [{'id': news.id, 'url': news.url, 'title': news.title, 'time': news.time, 'content': news.content} for news in news_list]
    finally:
        session.close()
