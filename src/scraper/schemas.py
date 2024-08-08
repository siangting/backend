from pydantic import BaseModel, Field, AnyHttpUrl
from datetime import datetime


class Headline(BaseModel):
    title: str = Field(
        default=...,
        example="Title of the article",
        description="The title of the article"
    )
    url: AnyHttpUrl | str = Field(
        default=...,
        example="https://www.example.com",
        description="The URL of the article"
    )


class News(Headline):
    time: datetime = Field(
        default=...,
        example="2021-10-01T00:00:00",
        description="The time the article was published"
    )
    content: str = Field(
        default=...,
        example="Content of the article",
        description="The content of the article"
    )


class NewsWithSummary(News):
    summary: str = Field(
        default=...,
        example="Summary of the article",
        description="The summary of the article"
    )
    reason: str = Field(
        default=...,
        example="Reason of the article",
        description="The reason of the article"
    )

# Example
# headline = Headline(title="Title of the article", url="https://www.example.com")
# headline.title
# headline.url
# news = News(title="Title of the article", url="https://www.example.com",
#             time="2021-10-01T00:00:00", content="Content of the article")
# news.time
# news.content
# news_with_summary = NewsWithSummary(title="Title of the article", url="https://www.example.com",
#                                     time="2021-10-01T00:00:00", content="Content of the article",
#                                     summary="Summary of the article", reason="Reason of the article")
# news_with_summary.summary
# news_with_summary.reason