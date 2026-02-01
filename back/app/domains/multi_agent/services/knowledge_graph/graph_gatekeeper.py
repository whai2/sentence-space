"""Graph Gatekeeper - LLM 기반 쿼리 분류"""

import logging
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.domains.multi_agent.services.knowledge_graph.prompts import (
    GATEKEEPER_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class GatekeeperVerdict(str, Enum):
    STORE = "STORE"
    STORE_MINIMAL = "STORE_MINIMAL"
    SKIP = "SKIP"


class GraphGatekeeper:
    """LLM 기반 게이트키퍼: 쿼리의 지식 그래프 저장 가치 판단

    가벼운/저렴한 LLM 모델을 사용하여 분류합니다.
    실패 시 STORE로 기본값 (fail-open).
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def classify(self, message: str) -> GatekeeperVerdict:
        """메시지를 분류하여 저장 수준 결정"""
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=GATEKEEPER_SYSTEM_PROMPT),
                HumanMessage(content=message),
            ])

            verdict_text = response.content.strip().upper()

            if "STORE_MINIMAL" in verdict_text:
                return GatekeeperVerdict.STORE_MINIMAL
            elif "STORE" in verdict_text:
                return GatekeeperVerdict.STORE
            elif "SKIP" in verdict_text:
                return GatekeeperVerdict.SKIP
            else:
                return GatekeeperVerdict.STORE

        except Exception as e:
            logger.warning(f"Gatekeeper classification failed: {e}")
            return GatekeeperVerdict.STORE
