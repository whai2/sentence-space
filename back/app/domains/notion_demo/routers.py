"""Notion Demo Domain Router"""

from fastapi import APIRouter

from app.domains.notion_demo.apis.notion_apis import notion_router

# Notion Router
notion_demo_router = APIRouter()
notion_demo_router.include_router(
    prefix="/notion", router=notion_router, tags=["Notion Demo"]
)
