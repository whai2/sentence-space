"""ClickUp MCP Client Wrapper

클릭업 MCP 서버와의 연결을 관리하는 클라이언트
기존 clickup_demo의 mcp_client를 재사용
"""

# 기존 ClickUp MCP 클라이언트 재사용
from app.domains.clickup_demo.services.agent.mcp_client import ClickUpMCPClient

__all__ = ["ClickUpMCPClient"]
