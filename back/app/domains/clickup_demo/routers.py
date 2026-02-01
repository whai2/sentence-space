"""ClickUp Demo Domain Router"""

from fastapi import APIRouter

from app.domains.clickup_demo.apis.clickup_apis import clickup_router

# ClickUp Router
clickup_demo_router = APIRouter()
clickup_demo_router.include_router(
    prefix="/clickup", router=clickup_router, tags=["ClickUp Demo"]
)
