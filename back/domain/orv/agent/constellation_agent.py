"""
성좌 에이전트

플레이어의 행동을 관전하고 흥미로운 순간에 반응하는 성좌들을 관리합니다.
"""

import json
import random
import re
from typing import Optional
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from domain.orv.model.state import GameState, ConstellationChannel
from domain.orv.model.knowledge import ConstellationInfo
from domain.orv.model.memory import NPCDecision


class ConstellationReaction(BaseModel):
    """성좌의 반응"""

    constellation_name: str
    should_react: bool = False
    message: Optional[str] = None
    coins_donated: int = 0
    reaction_type: str = "neutral"  # positive, negative, neutral, excited, disappointed


class ConstellationAgent:
    """
    성좌 에이전트.

    특징:
    - 흥미로운 이벤트를 감지하여 성좌 반응 결정
    - 각 성좌의 성격과 관심사에 맞는 반응 생성
    - 코인 후원 결정
    """

    # 흥미로운 이벤트 키워드
    INTERESTING_KEYWORDS = {
        "violence": ["죽", "공격", "때리", "싸우", "살", "피"],
        "help": ["돕", "구하", "지키", "보호", "치료"],
        "explore": ["살피", "관찰", "조사", "찾", "발견"],
        "creative": ["던지", "숨", "속이", "유인", "함정"],
        "moral": ["선택", "결정", "포기", "희생", "배신"],
        "discovery": ["강아지", "동물", "비밀", "단서", "열쇠"],
    }

    def __init__(
        self,
        constellations: list[ConstellationInfo],
        llm: ChatOpenAI,
    ):
        self.constellations = constellations
        self.llm = llm

    def _detect_interesting_event(
        self,
        player_action: str,
        npc_decisions: list[NPCDecision],
        game_state: GameState,
    ) -> dict[str, bool]:
        """흥미로운 이벤트 감지"""
        detected = {category: False for category in self.INTERESTING_KEYWORDS}

        # 플레이어 행동에서 키워드 검색
        action_lower = player_action.lower()
        for category, keywords in self.INTERESTING_KEYWORDS.items():
            if any(kw in action_lower for kw in keywords):
                detected[category] = True

        # NPC 반응에서 키워드 검색
        for decision in npc_decisions:
            desc = (decision.action_description or "").lower()
            dialogue = (decision.dialogue or "").lower()
            combined = desc + " " + dialogue

            for category, keywords in self.INTERESTING_KEYWORDS.items():
                if any(kw in combined for kw in keywords):
                    detected[category] = True

        # 특수 상태 체크
        if game_state.first_kill_completed:
            detected["violence"] = True

        return detected

    def _should_any_react(
        self,
        detected_events: dict[str, bool],
        game_state: GameState,
    ) -> bool:
        """성좌가 반응해야 하는지 판단"""
        # 흥미로운 이벤트가 있으면 반응
        if any(detected_events.values()):
            return True

        # 첫 턴에는 소개 차원에서 반응
        if game_state.turn_count == 0:
            return True

        # 3% 확률로 랜덤 반응 (너무 잦으면 안 됨)
        if random.random() < 0.03:
            return True

        return False

    def _match_constellation_interest(
        self,
        constellation: ConstellationInfo,
        detected_events: dict[str, bool],
        player_action: str,
    ) -> tuple[bool, int]:
        """성좌의 관심사와 이벤트 매칭, (반응여부, 흥미도) 반환"""
        interest_score = 0

        # 선호하는 행동 체크
        for preferred in constellation.preferred_actions:
            if any(kw in player_action for kw in preferred.split()):
                interest_score += 3

        # 싫어하는 행동 체크
        for disliked in constellation.disliked_actions:
            if any(kw in player_action for kw in disliked.split()):
                interest_score -= 2

        # 이벤트 타입에 따른 관심도
        if constellation.name == "지독한_살인귀":
            if detected_events.get("violence"):
                interest_score += 5
        elif constellation.name == "선악의_중재자":
            if detected_events.get("moral") or detected_events.get("help"):
                interest_score += 4
        elif constellation.name == "미친_광대":
            if detected_events.get("creative"):
                interest_score += 5
        elif constellation.name == "냉정한_관찰자":
            if detected_events.get("explore") or detected_events.get("discovery"):
                interest_score += 4
        elif constellation.name == "연민의_수호자":
            if detected_events.get("help"):
                interest_score += 5
            if detected_events.get("violence"):
                interest_score -= 3

        # 흥미도가 4 이상이면 반응 (더 엄격하게)
        should_react = interest_score >= 4

        # 확률 기반 반응 (흥미도가 낮아도 아주 가끔 반응, 10%)
        if not should_react and interest_score >= 2 and random.random() < 0.1:
            should_react = True

        return should_react, interest_score

    async def generate_reactions(
        self,
        game_state: GameState,
        player_action: str,
        npc_decisions: list[NPCDecision],
        narrative: str = "",
    ) -> list[ConstellationReaction]:
        """
        성좌 반응 생성.

        Args:
            game_state: 현재 게임 상태
            player_action: 플레이어 행동
            npc_decisions: NPC 의사결정 목록
            narrative: 생성된 서술 (추가 컨텍스트)

        Returns:
            반응할 성좌들의 목록
        """
        # 흥미로운 이벤트 감지
        detected_events = self._detect_interesting_event(
            player_action, npc_decisions, game_state
        )

        # 반응 필요 여부 확인
        if not self._should_any_react(detected_events, game_state):
            return []

        reactions = []

        # 각 성좌별로 반응 여부 결정
        for constellation in self.constellations:
            should_react, interest_score = self._match_constellation_interest(
                constellation, detected_events, player_action
            )

            if not should_react:
                continue

            # 최대 1개 성좌만 반응 (특별한 이벤트일 때만 2개)
            max_reactions = 2 if game_state.first_kill_completed and game_state.turn_count == 1 else 1
            if len(reactions) >= max_reactions:
                break

            # LLM으로 반응 메시지 생성
            reaction = await self._generate_single_reaction(
                constellation=constellation,
                player_action=player_action,
                game_state=game_state,
                interest_score=interest_score,
                detected_events=detected_events,
            )

            if reaction.should_react:
                reactions.append(reaction)

        return reactions

    async def _generate_single_reaction(
        self,
        constellation: ConstellationInfo,
        player_action: str,
        game_state: GameState,
        interest_score: int,
        detected_events: dict[str, bool],
    ) -> ConstellationReaction:
        """단일 성좌의 반응 생성"""

        # 이벤트 타입 요약
        active_events = [k for k, v in detected_events.items() if v]
        events_str = ", ".join(active_events) if active_events else "일반적인 상황"

        prompt = f"""당신은 '{constellation.title}' 성좌입니다.

## 성좌 정보
- 이름: {constellation.title}
- 설명: {constellation.description}
- 성격/말투: {constellation.personality}
- 선호하는 행동: {', '.join(constellation.preferred_actions)}
- 싫어하는 행동: {', '.join(constellation.disliked_actions)}
- 코인 관대함: {constellation.coin_generosity}/10

## 현재 상황
- 플레이어 행동: {player_action}
- 턴: {game_state.turn_count}
- 감지된 이벤트: {events_str}
- 시나리오: {game_state.current_scenario.title if game_state.current_scenario else '없음'}
- 첫 번째 살인: {'완료' if game_state.first_kill_completed else '미완료'}
- 현재 흥미도 점수: {interest_score}

## 지시사항
이 상황에서 {constellation.title}로서 짧은 반응 메시지를 생성하세요.
- 성격과 말투에 맞게 1-2문장으로 짧게
- 반응이 적절하지 않으면 should_react를 false로

## 코인 후원 규칙 (매우 중요!)
코인 후원은 **특별한 경우에만** 합니다:
1. 플레이어가 **당신의 선호 행동과 정확히 일치**하는 행동을 했을 때만 후원
2. 흥미도 점수가 5 이상일 때만 후원 고려
3. 대부분의 경우 coins는 0으로 설정
4. 후원할 때도 10-30 정도의 소액만 (50 이상은 정말 특별할 때만)
5. 단순히 "괜찮네" 정도로는 후원하지 않음

JSON 형식으로 응답:
{{
    "should_react": true/false,
    "message": "반응 메시지",
    "coins": 0-100,
    "reaction_type": "positive/negative/neutral/excited/disappointed"
}}"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="당신은 웹소설 '전지적 독자 시점'의 성좌입니다. 짧고 인상적인 반응을 생성하세요."),
                HumanMessage(content=prompt),
            ])

            # JSON 파싱
            json_match = re.search(r"\{[\s\S]*\}", response.content)
            if json_match:
                data = json.loads(json_match.group())

                # 코인 조정 (관대함에 따라)
                base_coins = data.get("coins", 0)

                # 흥미도가 5 미만이면 코인 후원 안 함 (강제)
                if interest_score < 5:
                    base_coins = 0

                adjusted_coins = int(base_coins * (constellation.coin_generosity / 5))

                return ConstellationReaction(
                    constellation_name=constellation.title,
                    should_react=data.get("should_react", False),
                    message=data.get("message"),
                    coins_donated=adjusted_coins,
                    reaction_type=data.get("reaction_type", "neutral"),
                )
        except Exception:
            pass

        # 파싱 실패 시 기본 반응
        return ConstellationReaction(
            constellation_name=constellation.title,
            should_react=False,
        )

    def apply_reactions(
        self,
        game_state: GameState,
        reactions: list[ConstellationReaction],
    ) -> list[str]:
        """
        성좌 반응을 게임 상태에 적용.

        Returns:
            시스템 메시지 목록 (서술에 포함될 내용)
        """
        messages = []

        for reaction in reactions:
            if not reaction.should_react or not reaction.message:
                continue

            # 채널에 메시지 추가
            game_state.constellation_channel.append(ConstellationChannel(
                constellation_name=reaction.constellation_name,
                message=reaction.message,
                coins_donated=reaction.coins_donated,
                turn=game_state.turn_count,
                reaction_type=reaction.reaction_type,
            ))

            # 코인 지급
            if reaction.coins_donated > 0:
                game_state.player.coins += reaction.coins_donated

            # 시스템 메시지 생성
            msg = f"성좌 '{reaction.constellation_name}'이(가) 말합니다: \"{reaction.message}\""
            if reaction.coins_donated > 0:
                msg += f" [{reaction.coins_donated} 코인 후원!]"
            messages.append(msg)

        return messages
