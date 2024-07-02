import requests
from .base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import quote


class UDNNewsScraper(BaseScraper):
    def __init__(self):
        super().__init__('https://udn.com/api/more')

    def fetch_news_data(self, search_term, is_initial=False):
        all_news_data = []
        #iterate pages to get more news data, not actually get all news data
        if is_initial:
            for page in range(1,10):
                news_data = self.update_recent_news(page, search_term)
                all_news_data.extend(news_data)
        else:
            all_news_data = self.update_recent_news(1, search_term)
        return all_news_data

    def update_recent_news(self, page, search_term):
        try:
            params = {
                'page': page,
                'id': f'search:{quote(search_term)}',
                'channelId': 2,
                'type': 'searchword'
            }
            print(params)
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


