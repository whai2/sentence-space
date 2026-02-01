from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

from app.domains.clickup_demo.routers import clickup_demo_router
from app.domains.clickup_demo.container.container import ClickUpDemoContainer
from app.domains.notion_demo.routers import notion_demo_router
from app.domains.notion_demo.container.container import NotionDemoContainer
from app.domains.multi_agent.apis import router as multi_agent_router
from app.domains.multi_agent.container import MultiAgentContainer
from app.common.database.mongodb import connect_to_mongo, close_mongo_connection
from app.common.database.neo4j_db import connect_to_neo4j, close_neo4j_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # MongoDB 연결
    await connect_to_mongo()

    # Neo4j 연결
    await connect_to_neo4j()

    # ClickUp Demo Container 초기화
    clickup_container = ClickUpDemoContainer()
    app.clickup_container = clickup_container
    clickup_container.wire(modules=["app.domains.clickup_demo.apis.clickup_apis"])

    # ClickUp Agent 초기화
    clickup_agent = clickup_container.clickup_agent()
    await clickup_agent.initialize()

    # Notion Demo Container 초기화
    notion_container = NotionDemoContainer()
    app.notion_container = notion_container
    notion_container.wire(modules=["app.domains.notion_demo.apis.notion_apis"])

    # Notion Agent 초기화
    notion_agent = notion_container.notion_agent()
    await notion_agent.initialize()

    yield

    # Shutdown
    # ClickUp MCP 클라이언트 종료
    try:
        clickup_mcp_client = clickup_container.mcp_client()
        if clickup_mcp_client:
            await clickup_mcp_client.close()
    except Exception as e:
        print(f"Warning: Error closing ClickUp MCP client: {e}")

    # Notion MCP 클라이언트 종료
    try:
        notion_mcp_client = notion_container.mcp_client()
        if notion_mcp_client:
            await notion_mcp_client.close()
    except Exception as e:
        print(f"Warning: Error closing Notion MCP client: {e}")

    # Neo4j 연결 종료
    await close_neo4j_connection()

    # MongoDB 연결 종료
    await close_mongo_connection()


app = FastAPI(
    title="In-House System Backend",
    description="FastAPI backend with ClickUp integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ClickUp Demo Router 추가
app.include_router(clickup_demo_router, prefix="/api/v1")

# Notion Demo Router 추가
app.include_router(notion_demo_router, prefix="/api/v1")

# Multi-Agent Router 추가
app.include_router(multi_agent_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "In-House System Backend API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
    )
