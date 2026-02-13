"""
ORV v3 Narrator API Routes

Stateless 나레이터 엔드포인트.
프론트엔드가 컨텍스트를 관리하고, 매 요청마다 전송.
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.config import get_settings
from domain.orv_v3.config import NarratorConfig, create_narrator_llm
from domain.orv_v3.narrator import NarratorAgent, SceneInput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orv/v3", tags=["ORV v3"])

# 싱글턴 에이전트 (서버 시작 시 한 번만 생성)
_agent: NarratorAgent | None = None


def _get_agent() -> NarratorAgent:
    global _agent
    if _agent is None:
        settings = get_settings()
        config = NarratorConfig(openrouter_api_key=settings.openrouter_api_key)
        llm = create_narrator_llm(config)
        _agent = NarratorAgent(llm=llm)
        logger.info(f"[ORV v3] NarratorAgent 초기화 완료 (model={config.model})")
    return _agent


# ============================================
# Request/Response Models
# ============================================


class NarrateRequest(BaseModel):
    """서술 요청"""

    world_setting: str = Field(description="세계관 설정")
    character_sheet: str = Field(description="캐릭터 시트")
    narrative_stage: str = Field(description="현재 서사 단계")
    previous_scene: str = Field(description="직전 장면")
    player_action: str = Field(description="플레이어 행동")
    extra_direction: str = Field(default="", description="추가 지시사항")


class NarrateResponse(BaseModel):
    """서술 응답"""

    success: bool
    narrative: str
    char_count: int
    error: str | None = None


# ============================================
# Routes
# ============================================


@router.post("/narrate", response_model=NarrateResponse)
async def narrate(request: NarrateRequest):
    """
    장면 서술 생성

    프론트엔드에서 모든 컨텍스트를 전송하면,
    나레이터가 웹소설 스타일의 장면 텍스트를 반환.
    """
    logger.info(f"[ORV v3] narrate 요청 - action: {request.player_action[:50]}...")

    try:
        agent = _get_agent()

        scene_input = SceneInput(
            world_setting=request.world_setting,
            character_sheet=request.character_sheet,
            narrative_stage=request.narrative_stage,
            previous_scene=request.previous_scene,
            player_action=request.player_action,
            extra_direction=request.extra_direction,
        )

        narrative = await agent.narrate(scene_input)

        logger.info(f"[ORV v3] 서술 생성 완료 ({len(narrative)}자)")

        return NarrateResponse(
            success=True,
            narrative=narrative,
            char_count=len(narrative),
        )

    except Exception as e:
        logger.error(f"[ORV v3] 서술 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
