"""LangFuse Integration for Agent Tracing and Observability"""

import os
from typing import Optional
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler


class LangFuseHandler:
    """LangFuse 핸들러 - Agent 실행 추적 및 관찰성 제공

    환경변수에서 자동으로 LangFuse 설정을 로드합니다:
    - LANGFUSE_SECRET_KEY
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_HOST (또는 LANGFUSE_BASE_URL)
    """

    def __init__(self):
        """LangFuse 핸들러 초기화 (환경변수에서 자동 설정)"""
        self.langfuse = Langfuse()

    def get_callback_handler(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        trace_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> CallbackHandler:
        """
        LangChain 콜백 핸들러 생성

        Args:
            session_id: 세션 ID (대화 ID)
            user_id: 사용자 ID
            trace_name: 트레이스 이름
            metadata: 추가 메타데이터

        Returns:
            CallbackHandler: LangChain과 통합되는 LangFuse 콜백 핸들러
        """
        handler = CallbackHandler(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        )

        if session_id:
            handler.session_id = session_id
        if user_id:
            handler.user_id = user_id
        if trace_name:
            handler.trace_name = trace_name
        if metadata:
            handler.metadata = metadata

        return handler

    def flush(self):
        """남아있는 이벤트를 LangFuse 서버로 전송"""
        self.langfuse.flush()
