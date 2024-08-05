from pydantic import BaseModel


class NecessityPrice(BaseModel):
    類別: str
    編號: int
    產品名稱: str
    規格: str
    統計值: str
    時間起點: str
    時間終點: str


class NewsArticleSchema(BaseModel):
    id: int
    url: str
    title: str
    time: str
    content: str
    summary: str
    reason: str
    upvotes: int
    is_upvoted: bool

    class Config:
        from_attributes = True


class SearchNewsArticleSchema(BaseModel):
    id: int
    url: str
    title: str
    time: str
    content: str


class NewsSummarySchema(BaseModel):
    summary: str
    reason: str


class NewsSumaryRequestSchema(BaseModel):
    content: str


class PromptRequest(BaseModel):
    prompt: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str


class UserSchema(BaseModel):
    username: str

    class Config:
        from_attributes = True


class UserAuthSchema(BaseModel):
    username: str
    password: str
