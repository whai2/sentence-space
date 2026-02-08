"""
NPC Agent

Claude Haiku 4.5 기반 개별 NPC 의사결정 에이전트
- 각 NPC가 독립적으로 판단
- 성격/기억 기반 행동 결정
- 비용 절감 (Haiku)
"""
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from domain.orv_v2.models import NPCState, GameState


# ============================================
# NPC 의사결정 Output
# ============================================

class NPCDecision(BaseModel):
    """
    NPC의 의사결정 결과

    Structured Output으로 강제
    """
    npc_id: str = Field(description="NPC ID")
    npc_name: str = Field(description="NPC 이름")

    # 행동 결정
    action_type: str = Field(
        description="행동 유형 (observe, speak, flee, attack, help, hide)"
    )
    action_description: str = Field(
        description="행동 설명 (구체적으로)"
    )

    # 대사 (있으면)
    dialogue: str | None = Field(
        default=None,
        description="NPC 대사 (말하는 경우)"
    )
    dialogue_tone: str = Field(
        default="neutral",
        description="대사 톤 (scared, angry, calm, hopeful, desperate)"
    )

    # 내면 심리
    internal_thought: str = Field(
        description="NPC 내면 생각 (1-2 문장)"
    )

    # 감정 변화
    new_emotional_state: str | None = Field(
        default=None,
        description="새로운 감정 상태 (변화 있으면)"
    )


# ============================================
# NPC 프롬프트
# ============================================

NPC_SYSTEM_PROMPT = """당신은 NPC입니다. 주어진 성격과 상황에 따라 **현실적으로** 반응하세요.

## 행동 유형
- **observe**: 상황 관찰, 아무것도 하지 않음
- **speak**: 플레이어나 다른 NPC에게 말함
- **flee**: 도망침
- **attack**: 공격
- **help**: 도움
- **hide**: 숨음

## 중요 원칙
1. **성격 반영**: 용기, 공격성, 공감 수치에 따라 행동
2. **공포 우선**: 공포도가 높으면 도망가거나 얼어붙음
3. **자기 보존**: 대부분의 민간인은 자신의 생존을 우선함
4. **일관성**: 이전 행동과 일관되게
"""


def create_npc_prompt(
    npc: NPCState,
    player_action: str,
    game_state: GameState,
) -> str:
    """NPC 의사결정용 프롬프트"""

    prompt = f"""
## 당신은 누구인가
- 이름: {npc.name}
- 유형: {npc.npc_type}
- 설명: {npc.description}
- 현재 감정: {npc.emotional_state}

## 성격
- 용기: {npc.personality.bravery}/100 (높을수록 겁 없음)
- 공격성: {npc.personality.aggression}/100 (높을수록 공격적)
- 공감: {npc.personality.empathy}/100 (높을수록 타인 배려)

## 플레이어와의 관계
- 호감도: {npc.relationship.affinity}/100
- 신뢰도: {npc.relationship.trust}/100
- 공포도: {npc.relationship.fear}/100

## 현재 상황
- 위치: {npc.position}
- 체력: {npc.health}/{npc.max_health}
- 태도: {npc.disposition}
- 무기 보유: {npc.has_weapon}

## 플레이어 행동
플레이어 "{game_state.player.name}"의 행동: {player_action}

---

당신은 이 상황에서 어떻게 반응하겠습니까?

**중요**: 성격과 공포도에 맞게 현실적으로 반응하세요.
"""

    return prompt


# ============================================
# NPC Agent
# ============================================

class NPCAgent:
    """
    개별 NPC 의사결정 에이전트

    Claude Haiku 4.5 기반 (비용 절감)
    """

    def __init__(self, llm: ChatOpenAI):
        """
        Args:
            llm: Claude Haiku 4.5 LLM (LLMFactory에서 생성)
        """
        self.llm = llm
        # Structured Output 강제 (function_calling 방식)
        self.structured_llm = llm.with_structured_output(
            NPCDecision,
            method="function_calling"
        )

    async def decide(
        self,
        npc: NPCState,
        player_action: str,
        game_state: GameState,
    ) -> NPCDecision:
        """
        NPC 의사결정

        Args:
            npc: NPC 상태
            player_action: 플레이어 행동
            game_state: 게임 상태

        Returns:
            NPCDecision: NPC 결정
        """
        # 프롬프트 생성
        prompt = create_npc_prompt(
            npc=npc,
            player_action=player_action,
            game_state=game_state,
        )

        # LLM 호출
        messages = [
            SystemMessage(content=NPC_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        decision: NPCDecision = await self.structured_llm.ainvoke(messages)

        # NPC ID/이름 설정 (안전장치)
        decision.npc_id = npc.npc_id
        decision.npc_name = npc.name

        return decision
