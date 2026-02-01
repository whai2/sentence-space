"""Notion MCP Client Wrapper

노션 MCP 서버와의 연결을 관리하는 클라이언트
"""

import os
import logging
from typing import List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

# MCP 클라이언트의 JSONRPC 파싱 에러 로깅 억제
for logger_name in ["mcp", "mcp.client", "mcp.client.stdio"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)
    if not logger.handlers:
        handler = logging.NullHandler()
        logger.addHandler(handler)
    logger.propagate = False


class NotionMCPClient:
    """Notion MCP 서버 클라이언트

    공식 @notionhq/notion-mcp-server를 사용하여 MCP 도구를 로드
    세션을 지속적으로 유지하여 ClosedResourceError 방지
    """

    def __init__(self, notion_token: Optional[str] = None):
        """
        Args:
            notion_token: Notion Integration Token (없으면 환경변수 사용)
        """
        self.notion_token = notion_token
        self.session: Optional[ClientSession] = None
        self.tools: List[Any] = []
        self._initialized = False
        self._stdio_context = None
        self._read = None
        self._write = None

    async def initialize(self) -> List[Any]:
        """MCP 서버 연결 및 도구 로드

        Returns:
            로드된 LangChain 도구 목록

        Raises:
            ValueError: NOTION_TOKEN이 설정되지 않은 경우
        """
        if self._initialized and self.session:
            try:
                return self.tools
            except Exception:
                await self.close()
                self._initialized = False

        # 토큰 확인
        token = self.notion_token or os.environ.get("NOTION_TOKEN")
        if not token:
            raise ValueError(
                "NOTION_TOKEN이 필요합니다. "
                "환경변수로 설정하거나 생성자에 전달해주세요."
            )

        # MCP 서버 파라미터 설정
        # @notionhq/notion-mcp-server: 공식 Notion MCP 서버
        server_params = StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "--quiet",
                "@notionhq/notion-mcp-server",
            ],
            env={
                "NOTION_TOKEN": token,
                "LOG_LEVEL": "error",
                "NPX_QUIET": "true",
                "NPM_CONFIG_LOGLEVEL": "error",
                "NODE_ENV": "production",
            },
        )

        # Stdio 클라이언트로 서버 연결
        self._stdio_context = stdio_client(server_params)
        self._read, self._write = await self._stdio_context.__aenter__()

        # 세션 생성
        self.session = ClientSession(self._read, self._write)
        await self.session.__aenter__()

        # 세션 초기화
        await self.session.initialize()

        # MCP 도구를 LangChain 도구로 변환
        self.tools = await load_mcp_tools(self.session)

        self._initialized = True
        return self.tools

    async def get_tools(self) -> List[Any]:
        """로드된 도구 목록 반환

        Returns:
            LangChain 도구 목록
        """
        if not self.tools or not self._initialized:
            await self.initialize()
        return self.tools

    async def ensure_session(self):
        """세션이 활성화되어 있는지 확인하고, 필요하면 재초기화

        실제로 MCP 서버와 통신을 시도하여 세션 상태를 확인합니다.
        """
        if not self._initialized or not self.session or not self.tools:
            await self.initialize()
            return

        # 실제로 MCP 서버와 통신을 시도하여 세션이 살아있는지 확인
        try:
            # list_tools()를 호출하여 실제 통신 테스트
            # 이 호출이 성공하면 세션이 살아있는 것
            await self.session.list_tools()
        except Exception:
            # 통신 실패 시 세션 재초기화
            await self.close()
            await self.initialize()

    async def close(self):
        """MCP 서버 연결 종료"""
        if not self._initialized:
            return

        if self.session:
            try:
                if hasattr(self.session, "_closed") and not self.session._closed:
                    await self.session.__aexit__(None, None, None)
            except (GeneratorExit, RuntimeError, Exception):
                pass
            finally:
                self.session = None

        if self._stdio_context:
            try:
                if self._read or self._write:
                    await self._stdio_context.__aexit__(None, None, None)
            except (GeneratorExit, RuntimeError, Exception):
                pass
            finally:
                self._stdio_context = None
                self._read = None
                self._write = None

        self.tools = []
        self._initialized = False
