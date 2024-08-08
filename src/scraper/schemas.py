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
