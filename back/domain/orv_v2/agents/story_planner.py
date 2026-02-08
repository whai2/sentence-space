"""
Story Planner Agent

시나리오 시작 시 Neo4j 지식 그래프를 기반으로 전체 스토리 플랜 생성
"""
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from domain.orv_v2.models.story_plan import (
    StoryPlan,
    StoryPhase,
    StoryEvent,
    PlannerOutput
)
from domain.orv_v2.models import GameState

logger = logging.getLogger(__name__)


# ============================================
# Planner Prompts
# ============================================

PLANNER_SYSTEM_PROMPT = """당신은 "전지적 독자 시점" 웹소설의 **스토리 플래너**입니다.

## 핵심 역할
Neo4j 지식 그래프에서 제공된 시나리오 정보를 바탕으로, **간결한 스토리 진행 계획**을 수립합니다.

## 계획 수립 원칙

### 1. 원작 충실성
- 나무위키/원작 정보를 기반으로 핵심 스토리 구조 수립
- 주요 이벤트들이 적절한 순서로 발생하도록 배치
- 김독자의 원작 지식 활용을 자연스럽게 반영

### 2. 간결성과 효율성 (중요!)
- **3-4단계의 간결한 Phase 구조** (7단계 불필요)
- 각 Phase당 **핵심 이벤트 2-3개**만 포함
- 플레이어의 선택에 따라 유연하게 변형 가능

### 3. 긴장감 곡선
- 도입 (Phase 1): 상황 파악, 규칙 이해
- 전개 (Phase 2-3): 갈등 고조, 핵심 이벤트
- 결말 (Phase 3-4): 클라이막스와 종료

### 4. 서술 가이드
- 각 이벤트마다 간단한 narrative_hints 제공 (1-2문장)
- Auto-Narrator가 참고할 핵심 포인트만

## 출력 형식
반드시 구조화된 JSON 형식으로 출력하세요.
- story_plan: **3-4단계** 스토리 플랜 (간결하게!)
- opening_narrative: 시작 서술 (1-2 문단)
- initial_choices: 초기 선택지 3개
"""


def create_planner_prompt(
    scenario_id: str,
    scenario_data: dict,
    game_state: GameState
) -> str:
    """
    Planner 프롬프트 생성

    Args:
        scenario_id: 시나리오 ID
        scenario_data: Neo4j에서 조회한 시나리오 데이터
        game_state: 현재 게임 상태
    """

    # 시나리오 기본 정보 (나무위키에서 파싱된 데이터)
    scenario_info = scenario_data.get("s", {})

    # 나무위키 원본 정보 추출
    difficulty = scenario_info.get('difficulty', 'N/A')
    clear_condition = scenario_info.get('clear_condition', scenario_info.get('objective', 'N/A'))
    time_limit = scenario_info.get('time_limit', 'N/A')
    reward = scenario_info.get('reward', 'N/A')
    failure_penalty = scenario_info.get('failure_penalty', 'N/A')
    description = scenario_info.get('description', '')

    # 페이즈 정보
    phases_info = "\n\n".join([
        f"### Phase {phase.get('order')}: {phase.get('phase_name')}\n"
        f"- 설명: {phase.get('description')}\n"
        f"- 목표 턴: {phase.get('target_turn_start')} ~ {phase.get('target_turn_end')}\n"
        f"- 완료 조건: {phase.get('completion_condition')}\n"
        f"- 서술 톤: {phase.get('narrative_tone')}"
        for phase in scenario_data.get("phases", [])
    ])

    # 캐릭터 정보
    characters_info = "\n".join([
        f"- **{char.get('name')}**: {char.get('description')}"
        for char in scenario_data.get("characters", [])[:5]
    ])

    # 이벤트 정보
    events_info = "\n".join([
        f"- {event.get('description')}"
        for event in scenario_data.get("events", [])[:10]
    ])

    # 트릭 정보
    tricks_info = "\n".join([
        f"- **{trick.get('name')}**: {trick.get('description')}"
        for trick in scenario_data.get("protagonist_tricks", [])
    ])

    prompt = f"""
## 시나리오 기본 정보 (나무위키 원작 데이터)
- ID: {scenario_id}
- 제목: **{scenario_info.get('title', '알 수 없음')}**
- 난이도: **{difficulty}**
- 클리어 조건: {clear_condition}
- 제한 시간: {time_limit}
- 보상: {reward}
- 실패 시: {failure_penalty}

### 📖 나무위키 설명
{description if description else '(설명 없음)'}
"""

    # Phase, Character, Event, Trick 정보가 있는 경우에만 추가
    if phases_info:
        prompt += f"""
## 🎭 스토리 페이즈 구조 (수동 설정)

{phases_info}
"""

    if characters_info:
        prompt += f"""
## 👥 주요 등장인물

{characters_info}
"""

    if events_info:
        prompt += f"""
## 🎬 핵심 이벤트들

{events_info}
"""

    if tricks_info:
        prompt += f"""
## 💡 김독자 전용 트릭 (원작 지식)

{tricks_info}
"""

    prompt += f"""
## 🎮 현재 게임 상태
- 플레이어: {game_state.player.name}
- 위치: {game_state.player.position}
- 턴: {game_state.turn_count}

## 스토리 페이즈 구조

{phases_info}

## 주요 등장인물

{characters_info}

## 핵심 이벤트들

{events_info}

## 김독자 전용 트릭 (원작 지식)

{tricks_info}

## 현재 게임 상태
- 플레이어: {game_state.player.name}
- 위치: {game_state.player.position}
- 턴: {game_state.turn_count}

---

위 정보를 바탕으로 **간결한 스토리 플랜**을 작성하세요.

**중요**:
1. **3-4단계 페이즈 구조**로 작성하세요 (7단계 불필요)
2. 각 Phase당 **핵심 이벤트 2-3개**만 포함하세요
3. 각 이벤트에 간단한 narrative_hints를 추가하세요 (1-2문장)
4. opening_narrative는 "전지적 독자 시점" 스타일로 작성하세요 (1-2 문단으로 간결하게)
5. initial_choices는 3개만 제공하세요
"""

    return prompt


# ============================================
# Story Planner Agent
# ============================================

class StoryPlannerAgent:
    """
    스토리 플래너 에이전트

    시나리오 시작 시 전체 스토리 플랜 생성
    """

    def __init__(self, llm: ChatOpenAI):
        """
        Args:
            llm: LLM for story planning (Haiku 4.5 권장 - 빠르고 저렴함)
        """
        self.llm = llm
        # Structured Output 강제
        self.structured_llm = llm.with_structured_output(
            PlannerOutput,
            method="function_calling"
        )

    async def create_story_plan(
        self,
        scenario_id: str,
        scenario_data: dict,
        game_state: GameState
    ) -> PlannerOutput:
        """
        스토리 플랜 생성

        Args:
            scenario_id: 시나리오 ID
            scenario_data: Neo4j에서 조회한 시나리오 상세 데이터
            game_state: 현재 게임 상태

        Returns:
            PlannerOutput: 스토리 플랜 + 시작 서술
        """
        logger.info(f"📋 [StoryPlanner] 스토리 플랜 생성 시작: scenario_id={scenario_id}")

        # Neo4j 데이터 통계
        scenario_info = scenario_data.get("s", {})
        phases_count = len(scenario_data.get("phases", []))
        characters_count = len(scenario_data.get("characters", []))
        events_count = len(scenario_data.get("events", []))
        tricks_count = len(scenario_data.get("protagonist_tricks", []))

        logger.info(f"   - 시나리오: {scenario_info.get('title', 'Unknown')}")
        logger.info(f"   - Neo4j 데이터: Phase={phases_count}, Character={characters_count}, Event={events_count}, Trick={tricks_count}")

        if phases_count == 0:
            logger.warning(f"⚠️  [StoryPlanner] Phase 데이터가 없습니다. 나무위키 데이터만 사용합니다.")

        prompt = create_planner_prompt(
            scenario_id=scenario_id,
            scenario_data=scenario_data,
            game_state=game_state
        )

        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info(f"🤖 [StoryPlanner] LLM 호출 중... (model={self.llm.model_name})")
        output: PlannerOutput = await self.structured_llm.ainvoke(messages)

        logger.info(f"✅ [StoryPlanner] 스토리 플랜 생성 완료")
        logger.info(f"   - Phases: {len(output.story_plan.phases)}개")
        logger.info(f"   - Initial Choices: {len(output.initial_choices)}개")

        return output
