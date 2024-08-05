import json

import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from .api.v1.router import api_router
from .models import NewsArticle, engine
from .services import UDNNewsScraper as UDNScraper
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

app.add_middleware(
    CORSMiddleware, # noqa
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_news_task(is_initial=False):
    # should change into simple factory pattern
    scraper = UDNScraper.UDNNewsScraper()
    news_data = scraper.fetch_news_data("價格", is_initial=is_initial)
    for news in news_data:
        try:
            relevance = openai_client.evaluate_relevance(news["title"])
            if relevance == "high":
                detailed_news = scraper.news_parser(news["titleLink"])
                if detailed_news:
                    result = openai_client.generate_summary(
                        " ".join(detailed_news["content"])
                    )
                    if result:
                        result = json.loads(result)
                        detailed_news["summary"] = result["影響"]
                        detailed_news["reason"] = result["原因"]
                        scraper.save_news_content(detailed_news)
        except Exception as e:
            print(f"Error processing news {news['titleLink']}: {e}")


scheduler = BackgroundScheduler()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@app.on_event("startup")
def start_scheduler():
    db = SessionLocal()
    if db.query(NewsArticle).count() == 0:
        # should change into simple factory pattern
        fetch_news_task(is_initial=True)
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
