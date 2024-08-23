import itertools
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from src.models import NewsArticle, User, engine, user_news_association_table
from src.schemas import (NewsArticleSchema, NewsSumaryRequestSchema,
                 NewsSummarySchema, PromptRequest,
                 SearchNewsArticleSchema)
from src.crawler import UDNCrawler
from src.services.openai_client import openai_client
from .users import authenticate_user_token

router = APIRouter()

udn_crawler = UDNCrawler()

_id_counter = itertools.count(start=1000000)

def session_opener():
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


def get_article_upvote_details(article_id, uid, db):
    cnt = (
        db.query(user_news_association_table)
        .filter_by(news_articles_id=article_id)
        .count()
    )
    voted = False
    if uid:
        voted = (
            db.query(user_news_association_table)
            .filter_by(news_articles_id=article_id, user_id=uid)
            .first()
            is not None
        )
    return cnt, voted


@router.get("/news", response_model=list[NewsArticleSchema])
def read_news(db: Session = Depends(session_opener)):
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for n in news:
        upvotes, upvoted = get_article_upvote_details(n.id, None, db)
        result.append(
            {**n.__dict__, "upvotes": upvotes, "is_upvoted": upvoted}
        )
    return result


@router.get(
    "/user_news",
    response_model=list[NewsArticleSchema],
    description="獲取包含user upvote資訊的新聞列表",
)
def read_user_news(
    db: Session = Depends(session_opener), u: User = Depends(authenticate_user_token)
):
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in news:
        upvotes, upvoted = get_article_upvote_details(article.id, u.id, db)
        result.append(
            {
                **article.__dict__,
                "upvotes": upvotes,
                "is_upvoted": upvoted,
            }
        )
    return result


@router.post("/search_news", response_model=list[SearchNewsArticleSchema])
async def search_news(request: PromptRequest):
    prompt = request.prompt
    newss = []
    keywords = openai_client.extract_search_keywords(prompt)
    if not keywords:
        return []
    # should change into simple factory pattern
    news = udn_crawler.get_headline(keywords, page=1)
    for n in news:
        try:
            detailed_n = udn_crawler.parse(n.url)
            if detailed_n:
                detailed_news_dict = detailed_n.model_dump()
                detailed_news_dict["id"] = next(_id_counter)
                newss.append(detailed_news_dict)
        except Exception as e:
            print(f"Error processing news {n.url}: {e}")
    return sorted(newss, key=lambda x: x["time"], reverse=True)




@router.post("/news_summary", response_model=NewsSummarySchema)
async def news_summary(
    payload: NewsSumaryRequestSchema, user=Depends(authenticate_user_token)
):
    content = payload.content
    response = {}
    result = openai_client.generate_summary(content)
    if result:
        result = json.loads(result)
        response["summary"] = result["影響"]
        response["reason"] = result["原因"]
    return response

@router.post("/{id}/upvote")
def upvote_article(
    id: int,
    db: Session = Depends(session_opener),
    u: User = Depends(authenticate_user_token),
):
    if not u:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not exists(id, db):
        raise HTTPException(status_code=404, detail="News not found")

    message = toggle_upvote(id, u.id, db)
    return {"message": message}


def toggle_upvote(n_id: int, u_id: int, db: Session):
    existing_upvote = db.execute(
        select(user_news_association_table).where(
            user_news_association_table.c.news_articles_id == n_id,
            user_news_association_table.c.user_id == u_id,
        )
    ).scalar()

    if existing_upvote:
        delete_stmt = delete(user_news_association_table).where(
            user_news_association_table.c.news_articles_id == n_id,
            user_news_association_table.c.user_id == u_id,
        )
        db.execute(delete_stmt)
        db.commit()
        return "Upvote removed"
    else:
        insert_stmt = insert(user_news_association_table).values(
            news_articles_id=n_id, user_id=u_id
        )
        db.execute(insert_stmt)
        db.commit()
        return "Article upvoted"


def exists(news_id: int, db: Session):
    return db.query(NewsArticle).filter_by(id=news_id).first() is not None
