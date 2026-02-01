"""Topic Extractor - LLM 기반 토픽/의도/키워드 추출"""

import json
import logging
from typing import List
from dataclasses import dataclass, field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.domains.multi_agent.services.knowledge_graph.prompts import (
    TOPIC_EXTRACTOR_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    topics: List[str] = field(default_factory=list)
    intent: str = ""
    keywords: List[str] = field(default_factory=list)


class TopicExtractor:
    """LLM 기반 토픽 추출기

    사용자 메시지에서 토픽, 의도, 키워드를 구조화하여 추출합니다.
    실패 시 빈 ExtractionResult 반환.
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def extract(self, message: str) -> ExtractionResult:
        """메시지에서 토픽, 의도, 키워드 추출"""
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=TOPIC_EXTRACTOR_SYSTEM_PROMPT),
                HumanMessage(content=message),
            ])

            content = response.content.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)
            return ExtractionResult(
                topics=data.get("topics", []),
                intent=data.get("intent", ""),
                keywords=data.get("keywords", []),
            )

        except Exception as e:
            logger.warning(f"Topic extraction failed: {e}")
            return ExtractionResult()
