# models.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class NewsArticle(Base):
    __tablename__ = 'news_articles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    time = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)

engine = create_engine('sqlite:///news_database.db', echo=True)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
