"""ClickUp MCP Client Wrapper

클릭업 MCP 서버와의 연결을 관리하는 클라이언트
"""

import os
import logging
from typing import List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

# MCP 클라이언트의 JSONRPC 파싱 에러 로깅 억제
# dotenvx가 stdout에 로그를 출력하여 발생하는 파싱 에러는 실제 동작에 지장이 없으므로
# 로깅 레벨을 조정하여 에러 메시지를 숨깁니다.
# 모든 관련 로거에 대해 조정
for logger_name in ["mcp", "mcp.client", "mcp.client.stdio"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)  # CRITICAL 레벨만 표시
    # 핸들러가 없으면 추가하여 로그를 억제
    if not logger.handlers:
        handler = logging.NullHandler()
        logger.addHandler(handler)
    logger.propagate = False  # 상위 로거로 전파하지 않음


class ClickUpMCPClient:
    """ClickUp MCP 서버 클라이언트

    Nazruden의 clickup-mcp-server를 사용하여 MCP 도구를 로드
    세션을 지속적으로 유지하여 ClosedResourceError 방지
    """

    def __init__(self, clickup_token: Optional[str] = None):
        """
        Args:
            clickup_token: ClickUp Personal API Token (없으면 환경변수 사용)
        """
        self.clickup_token = clickup_token
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
            ValueError: CLICKUP_PERSONAL_TOKEN이 설정되지 않은 경우
        """
        if self._initialized and self.session:
            # 세션이 살아있는지 확인
            try:
                # 간단한 핑으로 세션 상태 확인
                return self.tools
            except Exception:
                # 세션이 닫혔으면 기존 세션 정리 후 재초기화
                await self.close()
                self._initialized = False

        # 토큰 확인
        token = self.clickup_token or os.environ.get("CLICKUP_API_KEY")
        if not token:
            raise ValueError(
                "CLICKUP_API_KEY가 필요합니다. "
                "환경변수로 설정하거나 생성자에 전달해주세요."
            )

        # 팀 ID 확인
        team_id = os.environ.get("CLICKUP_TEAM_ID")
        if not team_id:
            raise ValueError(
                "CLICKUP_TEAM_ID가 필요합니다. " "환경변수로 설정해주세요."
            )

        # MCP 서버 파라미터 설정
        # @twofeetup/clickup-mcp: 성능 최적화 및 응답 최적화가 적용된 버전
        # - 통합된 도구로 도구 호출 횟수 감소
        # - 응답 크기 최적화로 토큰 사용량 절감
        # 참고: npx와 dotenv가 stdout에 로그를 출력하면 MCP 클라이언트가 이를 JSONRPC 메시지로
        # 파싱하려고 시도하여 에러가 발생할 수 있습니다. 하지만 MCP 클라이언트가 이를 처리하므로
        # 실제 동작에는 지장이 없습니다. 다만 로그를 깔끔하게 유지하기 위해 출력을 억제합니다.
        server_params = StdioServerParameters(
            command="npx",
            args=[
                "-y",  # 자동으로 패키지 설치
                "--quiet",  # npx 출력 억제 (dotenv 로그 등)
                "@twofeetup/clickup-mcp@latest",  # 성능 최적화된 버전
            ],
            env={
                # @twofeetup/clickup-mcp는 CLICKUP_API_KEY와 CLICKUP_TEAM_ID를 사용
                "CLICKUP_API_KEY": token,
                "CLICKUP_TEAM_ID": team_id,
                # 하위 호환성을 위한 기존 환경변수도 포함
                "CLICKUP_PERSONAL_TOKEN": token,
                "LOG_LEVEL": "error",  # info 레벨의 로그가 JSONRPC 파싱을 방해할 수 있음
                # dotenvx 관련 로그 억제 (모든 가능한 환경변수 설정)
                "DOTENVX_QUIET": "true",
                "DOTENVX_SILENT": "true",
                "NPX_QUIET": "true",
                "NPM_CONFIG_LOGLEVEL": "error",  # npm 로그 레벨
                "NODE_ENV": "production",  # production 모드로 실행
            },
        )

        # Stdio 클라이언트로 서버 연결 (컨텍스트 매니저 사용하지 않고 직접 관리)
        self._stdio_context = stdio_client(server_params)
        self._read, self._write = await self._stdio_context.__aenter__()

        # 세션 생성 (컨텍스트 매니저 사용하지 않고 직접 관리)
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
        # 세션이 초기화되지 않았거나 도구가 없으면 초기화
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

        # 세션 종료
        if self.session:
            try:
                # 세션이 이미 닫혔는지 확인
                if hasattr(self.session, "_closed") and not self.session._closed:
                    await self.session.__aexit__(None, None, None)
            except (GeneratorExit, RuntimeError, Exception) as e:
                # 종료 중 발생하는 예외는 무시 (정상적인 종료 프로세스의 일부)
                pass
            finally:
                self.session = None

        # Stdio 컨텍스트 종료
        if self._stdio_context:
            try:
                # 컨텍스트가 이미 닫혔는지 확인
                if self._read or self._write:
                    await self._stdio_context.__aexit__(None, None, None)
            except (GeneratorExit, RuntimeError, Exception) as e:
                # 종료 중 발생하는 예외는 무시 (정상적인 종료 프로세스의 일부)
                pass
            finally:
                self._stdio_context = None
                self._read = None
                self._write = None

        # 상태 초기화
        self.tools = []
        self._initialized = False
