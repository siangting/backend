import json
import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.middleware.cors import CORSMiddleware
from .crawler.base import NewsWithSummary
import itertools
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker
from src.models import NewsArticle, User, engine, user_news_association_table
from src.schemas import (NewsArticleSchema, NewsSumaryRequestSchema,
                 NewsSummarySchema, PromptRequest,
                 SearchNewsArticleSchema, NecessityPrice, TokenSchema, UserAuthSchema, UserSchema)
from src.crawler import UDNCrawler
from src.services.openai_client import openai_client
from typing import List, Optional
import requests
from fastapi import APIRouter, HTTPException, Query, Depends, status, FastAPI
import os
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext


sentry_sdk.init(
    dsn="https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

app = FastAPI()
scheduler = BackgroundScheduler()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app.add_middleware(
    CORSMiddleware, # noqa
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fetch_news_task(is_init: bool = False):
    db = SessionLocal()
    # should change into simple factory pattern
    udn_crawler = UDNCrawler()
    if is_init:
        news_data = udn_crawler.startup("價格")
    else:
        news_data = udn_crawler.get_headline("價格", 1)
    for news in news_data:
        try:
            relevance = openai_client.evaluate_relevance(news.title)
            if relevance == "high":
                detailed_news = udn_crawler.parse(news.url)
                if detailed_news:
                    result = openai_client.generate_summary(detailed_news.content)
                    if result:
                        result = json.loads(result)
                        news_with_summary = NewsWithSummary(
                            title=detailed_news.title,
                            url=detailed_news.url,
                            time=detailed_news.time,
                            content=detailed_news.content,
                            summary=result.get("影響", ""),
                            reason=result.get("原因", "")
                        )
                        print(news_with_summary)
                        udn_crawler.save(news_with_summary, db)
                        print(f"Saved news {detailed_news.url}")
        except Exception as e:
            print(f"Error processing news {news.url}: {e}")


@app.on_event("startup")
def start_scheduler():
    db = SessionLocal()
    if db.query(NewsArticle).count() == 0:
        # should change into simple factory pattern
        fetch_news_task(is_init=True)
    db.close()
    scheduler.add_job(fetch_news_task, "interval", minutes=100)
    scheduler.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()


@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0 # noqa




# users api
users_router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

def session_opener():
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()

def get_user(db: Session, name: str):
    return db.query(User).filter(User.username == name).first()


def verify(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, username: str, pwd: str):
    user = get_user(db, username)
    if not user or not verify(pwd, user.hashed_password):
        return False
    return user


def authenticate_user_token(
    token: str = Depends(oauth2_scheme), db: Session = Depends(session_opener)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    print(to_encode)
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@users_router.post("/login", response_model=TokenSchema)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(session_opener)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.username)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@users_router.post("/register", response_model=UserSchema)
def create_user(user: UserAuthSchema, db: Session = Depends(session_opener)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@users_router.get("/me", response_model=UserSchema)
def read_users_me(user: str = Depends(authenticate_user_token)):
    return {"username": user.username}


#news api
news_router = APIRouter()

udn_crawler = UDNCrawler()

_id_counter = itertools.count(start=1000000)

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


@news_router.get("/news", response_model=list[NewsArticleSchema])
def read_news(db: Session = Depends(session_opener)):
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for n in news:
        upvotes, upvoted = get_article_upvote_details(n.id, None, db)
        result.append(
            {**n.__dict__, "upvotes": upvotes, "is_upvoted": upvoted}
        )
    return result


@news_router.get(
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


@news_router.post("/search_news", response_model=list[SearchNewsArticleSchema])
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


@news_router.post("/news_summary", response_model=NewsSummarySchema)
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

@news_router.post("/{id}/upvote")
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


prices_router = APIRouter()

@prices_router.get("/necessities-price", response_model=List[NecessityPrice])
def get_necessities_prices(
    category: Optional[str] = Query(None), commodity: Optional[str] = Query(None)
):
    response = requests.get(
        "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
        params={"CategoryName": category, "Name": commodity},
    )
    response.raise_for_status()


    return response.json()

api_router = APIRouter()
api_router.include_router(prices_router, prefix="/prices", tags=["prices"])
api_router.include_router(news_router, prefix="/news", tags=["news"])
api_router.include_router(users_router, prefix="/users", tags=["users"])

app.include_router(api_router, prefix="/api/v1")