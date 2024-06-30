from fastapi import FastAPI
from .api.v1.router import api_router
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from .services import UDNNewsScraper as UDNScraper


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fetch_news_task():
    scraper = UDNScraper.UDNNewsScraper("https://udn.com/api/more")
    news_data = scraper.fetch_news_data('價格')
    for news in news_data:
        relevance = scraper.evaluate_relevance(news['title'])
        if relevance in ['high', 'medium']:
            detailed_news = scraper.news_parser(news['titleLink'])
            if detailed_news:
                scraper.save_news_content(detailed_news)

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(fetch_news_task, 'interval', minutes=10)
    scheduler.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()

app.include_router(api_router, prefix="/api/v1")
