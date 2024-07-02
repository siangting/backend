from fastapi import APIRouter
from ....schemas import NewsArticleSchema, PromptRequest
from sqlalchemy.orm import Session
from ....models import NewsArticle, engine
from ....services.openai_client import openai_client
from ....services import UDNNewsScraper
import json
import itertools

router = APIRouter()
udn_scraper = UDNNewsScraper.UDNNewsScraper()
_id_counter = itertools.count(start=1000000)  # 從1000000開始以避免與現有的DB ID衝突

@router.get("/news", response_model=list[NewsArticleSchema])  # 使用 Pydantic 模型
def read_news():
    session = Session(bind=engine)
    try:
        news_list = session.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
        return news_list
    finally:
        session.close()

@router.post("/search_news", response_model=list[NewsArticleSchema])
async def search_news(request: PromptRequest):
    prompt = request.prompt
    news_list = []
    try:
        keywords = openai_client.extract_search_keywords(prompt)
        print(keywords)
        if not keywords:
            return []
        #should change into simple factory pattern
        news_items = udn_scraper.fetch_news_data(keywords, is_initial=False)
        for news in news_items:
            try:
                detailed_news = udn_scraper.news_parser(news['titleLink'])
                if detailed_news:
                    result = openai_client.generate_summary(' '.join(detailed_news['content']))
                    print(result)
                    if result:
                        result = json.loads(result)
                        detailed_news['summary'] = result['影響']
                        detailed_news['reason'] = result['原因']
                        detailed_news['content'] = ' '.join(detailed_news['content'])
                        detailed_news['id'] = next(_id_counter)
                        news_list.append(detailed_news)
            except Exception as e:
                print(f"Error processing news {news['titleLink']}: {e}")
        return sorted(news_list, key=lambda x: x['time'], reverse=True)
    
    except Exception as e:
        print('Error during process news: ', e)
        return []
