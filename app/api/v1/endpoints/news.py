from fastapi import APIRouter
from ....schemas import NewsArticleSchema
from sqlalchemy.orm import Session
from ....models import NewsArticle, engine

router = APIRouter()

@router.get("/news", response_model=list[NewsArticleSchema])  # 使用 Pydantic 模型
def read_news():
    session = Session(bind=engine)
    try:
        news_list = session.query(NewsArticle).all()
        return news_list
    finally:
        session.close()
