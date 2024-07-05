from fastapi import APIRouter
from .endpoints import prices, news, users

api_router = APIRouter()
api_router.include_router(prices.router, prefix="/prices", tags=["prices"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

