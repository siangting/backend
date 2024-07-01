import requests
from .base_scraper import BaseScraper
from bs4 import BeautifulSoup

class UDNNewsScraper(BaseScraper):
    def __init__(self):
        self.base_url = "https://udn.com/api/more"

    def fetch_news_data(self):
        all_news_data = []
        #iterate 3 pages to get more news data
        for page in range(3):
            news_data = self.custom_fetch_news_data(page, '價格')
            all_news_data.extend(news_data)
        return all_news_data

    def custom_fetch_news_data(self, page, search_term):
        try:
            params = {
                'page': page,
                'id': f'search:{search_term}',
                'channelId': 2,
                'type': 'searchword'
            }
            response = requests.get(self.base_url, params=params)
            return response.json()['lists'] if response.status_code == 200 else []
        except Exception as e:
            return []

    def news_parser(self, news_url):
        response = requests.get(news_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 標題
            title = soup.find('h1', class_='article-content__title').text
            time = soup.find('time', class_='article-content__time').text
            # 定位到包含文章内容的 <section>
            content_section = soup.find('section', class_='article-content__editor')
            if not content_section:
                return None
            # 過濾掉不需要的內容
            paragraphs = [p.text for p in content_section.find_all('p') if p.text.strip() != '' and '▪' not in p.text]
            return {
                'url': news_url,
                'title': title,
                'time': time,
                'content': paragraphs
            }
        else:
            return None


