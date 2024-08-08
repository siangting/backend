import json

import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from .api.v1.router import api_router
from .models import NewsArticle, engine
from .crawler import UDNCrawler
from .crawler.base import NewsWithSummary
from .services.openai_client import openai_client

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


app.include_router(api_router, prefix="/api/v1")
