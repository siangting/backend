"""
News Scraper Package

This package provides classes and methods for scraping news articles from various news websites.
The core functionality is encapsulated in the `NewsScraperBase` abstract class, which defines the
interface for news scrapers. Implementations of this interface, such as the `UDNScraper`, provide
concrete methods for fetching, parsing, and saving news articles.

"""

__author__ = "Intro to Software Eng. and Design Pat. with application to Project Develop Team"
__copyright__ = "Copyright (c) 2024 Intro to Software Eng. and Design Pat. with application to Project Develop Team"
__license__ = "MIT"
__version__ = "1.0.0"
__email__ = "hank93513@gmail.com"

from .base import NewsScraperBase, Headline, News
from .udn_scraper import UDNScraper
from .exceptions import DomainMismatchException

