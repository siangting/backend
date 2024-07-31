import itertools
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from ....models import NewsArticle, User, engine, user_news_association_table
from ....schemas import (NewsArticleSchema, NewsSumaryRequestSchema,
                         NewsSummarySchema, PromptRequest,
                         SearchNewsArticleSchema)
from ....services import UDNNewsScraper
from ....services.openai_client import openai_client
from .users import authenticate_user_token

router = APIRouter()
udn_scraper = UDNNewsScraper.UDNNewsScraper()
_id_counter = itertools.count(start=1000000)  # 從1000000開始以避免與現有的DB ID衝突


def get_db():
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


def get_article_upvote_details(article_id, user_id, db):
    upvote_count = (
        db.query(user_news_association_table)
        .filter_by(news_articles_id=article_id)
        .count()
    )
    is_upvoted = False
    if user_id:
        is_upvoted = (
            db.query(user_news_association_table)
            .filter_by(news_articles_id=article_id, user_id=user_id)
            .first()
            is not None
        )
    return upvote_count, is_upvoted


@router.get("/news", response_model=list[NewsArticleSchema])
def read_news(db: Session = Depends(get_db)):
    try:
        news_list = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
        result = []
        for news in news_list:
            upvotes, is_upvoted = get_article_upvote_details(news.id, None, db)
            result.append(
                {**news.__dict__, "upvotes": upvotes, "is_upvoted": is_upvoted}
            )
        return result
    finally:
        db.close()


@router.get(
    "/user_news",
    response_model=list[NewsArticleSchema],
    description="獲取包含user upvote資訊的新聞列表",
)
def read_user_news(
    db: Session = Depends(get_db), user: User = Depends(authenticate_user_token)
):
    news_items = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in news_items:
        upvote_count, is_upvoted = get_article_upvote_details(article.id, user.id, db)
        result.append(
            {
                **article.__dict__,
                "upvotes": upvote_count,
                "is_upvoted": is_upvoted,
            }
        )
    return result


@router.post("/search_news", response_model=list[SearchNewsArticleSchema])
async def search_news(request: PromptRequest):
    prompt = request.prompt
    news_list = []
    try:
        keywords = openai_client.extract_search_keywords(prompt)
        if not keywords:
            return []
        # should change into simple factory pattern
        news_items = udn_scraper.fetch_news_data(keywords, is_initial=False)
        for news in news_items:
            try:
                detailed_news = udn_scraper.news_parser(news["titleLink"])
                if detailed_news:
                    detailed_news["content"] = " ".join(detailed_news["content"])
                    detailed_news["id"] = next(_id_counter)
                    news_list.append(detailed_news)
            except Exception as e:
                print(f"Error processing news {news['titleLink']}: {e}")
        return sorted(news_list, key=lambda x: x["time"], reverse=True)

    except Exception as e:
        print("Error during process news: ", e)
        return []


@router.post("/news_summary", response_model=NewsSummarySchema)
def news_summary(
    payload: NewsSumaryRequestSchema, user=Depends(authenticate_user_token)
):
    content = payload.content
    response = {}
    try:
        result = openai_client.generate_summary(content)
        if result:
            result = json.loads(result)
            response["summary"] = result["影響"]
            response["reason"] = result["原因"]
        return response
    except Exception as e:
        print("Error during process news summary: ", e)
        return {}


@router.post("/{news_id}/upvote")
def upvote_article(
    news_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(authenticate_user_token),
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not check_article_exists(news_id, db):
        raise HTTPException(status_code=404, detail="News not found")

    message = toggle_upvote(news_id, user.id, db)
    return {"message": message}


def toggle_upvote(news_id: int, user_id: int, db: Session):
    existing_upvote = db.execute(
        select(user_news_association_table).where(
            user_news_association_table.c.news_articles_id == news_id,
            user_news_association_table.c.user_id == user_id,
        )
    ).scalar()

    if existing_upvote:
        delete_stmt = delete(user_news_association_table).where(
            user_news_association_table.c.news_articles_id == news_id,
            user_news_association_table.c.user_id == user_id,
        )
        db.execute(delete_stmt)
        db.commit()
        return "Upvote removed"
    else:
        insert_stmt = insert(user_news_association_table).values(
            news_articles_id=news_id, user_id=user_id
        )
        db.execute(insert_stmt)
        db.commit()
        return "Article upvoted"


def check_article_exists(news_id: int, db: Session):
    return db.query(NewsArticle).filter_by(id=news_id).first() is not None
