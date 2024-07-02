from fastapi import FastAPI
from .api.v1.router import api_router
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from .services import UDNNewsScraper as UDNScraper
from .services.openai_client import openai_client
import json
from .models import engine, NewsArticle
from sqlalchemy.orm import sessionmaker


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fetch_news_task(is_initial=False):
    #should change into simple factory pattern
    scraper = UDNScraper.UDNNewsScraper()
    news_data = scraper.fetch_news_data('價格', is_initial=is_initial)
    for news in news_data:
        try:
            relevance = openai_client.evaluate_relevance(news['title'])
            if relevance == 'high':
                detailed_news = scraper.news_parser(news['titleLink'])
                if detailed_news:
                    result = openai_client.generate_summary(' '.join(detailed_news['content']))
                    if result:
                        result = json.loads(result)
                        detailed_news['summary'] = result['影響']
                        detailed_news['reason'] = result['原因']
                        scraper.save_news_content(detailed_news)
        except Exception as e:
            print(f"Error processing news {news['titleLink']}: {e}")

scheduler = BackgroundScheduler()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.on_event("startup")
def start_scheduler():
    db = SessionLocal()
    if db.query(NewsArticle).count() == 0:
        #should change into simple factory pattern
        fetch_news_task(is_initial=True)
    db.close()
    scheduler.add_job(fetch_news_task, 'interval', minutes=10)
    scheduler.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()

app.include_router(api_router, prefix="/api/v1")
