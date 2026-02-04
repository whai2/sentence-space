"""
도깨비 에이전트

전지적 독자 시점 세계관의 시나리오 관리자.
시나리오 안내, 클리어 판정, 보상 지급을 담당합니다.
"""

import json
import re
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from domain.orv.model.state import GameState, ScenarioState
from domain.orv.model.knowledge import ScenarioInfo


class ScenarioClearRecord(BaseModel):
    """시나리오 클리어 기록"""

    scenario_id: str
    scenario_title: str
    difficulty: str
    cleared_at_turn: int
    clear_time: datetime = Field(default_factory=datetime.now)

    # 클리어 방식
    clear_method: str = ""  # "kill_animal", "kill_human", "alternative" 등
    target_killed: Optional[str] = None  # 죽인 대상 (있다면)

    # 보상
    coins_earned: int = 0
    exp_earned: int = 0
    bonus_rewards: list[str] = Field(default_factory=list)

    # 성과
    achievements: list[str] = Field(default_factory=list)  # "첫 시나리오 클리어", "무자비한 선택" 등

    # 평가
    dokkaebi_comment: str = ""  # 도깨비의 평가


class DokkaebiState(BaseModel):
    """도깨비 상태"""

    current_scenario: Optional[ScenarioInfo] = None
    clear_records: list[ScenarioClearRecord] = Field(default_factory=list)
    total_scenarios_cleared: int = 0
    watching_since_turn: int = 0


class DokkaebiAgent:
    """
    도깨비 에이전트.

    역할:
    - 시나리오 시작 안내 메시지 생성
    - 시나리오 클리어 조건 판정
    - 클리어 시 결과 발표 및 보상 처리
    - 클리어 기록 관리
    """

    # 도깨비 성격 설정
    PERSONALITY = """당신은 '전지적 독자 시점' 세계관의 도깨비입니다.

## 성격
- 장난스럽고 비꼬는 말투
- 인간의 고통과 갈등을 즐기지만, 규칙은 철저히 지킴
- 시나리오 진행에 대해 냉정하고 객관적
- 가끔 의미심장한 힌트를 주기도 함
- 대사 앞에 "[도깨비]" 태그를 붙여서 도깨비의 말임을 명확히 표시

## 말투 예시
- "[도깨비] 크크, 드디어 시작이군."
- "[도깨비] 뭐야, 벌써 끝이야? 좀 더 발버둥 치는 모습을 보고 싶었는데."
- "[도깨비] 선택은 네 몫이야. 난 그저 지켜볼 뿐이지."
- "[도깨비] 흥미롭군. 그런 방법이 있었어?"
"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self._states: dict[str, DokkaebiState] = {}  # session_id -> DokkaebiState

    def get_or_create_state(self, session_id: str) -> DokkaebiState:
        """세션별 도깨비 상태 조회/생성"""
        if session_id not in self._states:
            self._states[session_id] = DokkaebiState()
        return self._states[session_id]

    async def generate_scenario_opening(
        self,
        scenario: ScenarioInfo,
        game_state: GameState,
    ) -> str:
        """
        시나리오 시작 메시지 생성.

        도깨비가 시나리오를 안내하는 연출.
        """
        prompt = f"""## 상황
새로운 시나리오가 시작됩니다. 도깨비로서 이 시나리오를 안내하세요.

## 시나리오 정보
- 제목: {scenario.title}
- 난이도: {scenario.difficulty}급
- 목표: {scenario.objective}
- 제한 시간: {scenario.time_limit if scenario.time_limit else '없음'}턴
- 보상: {scenario.reward_coins} 코인, {scenario.reward_exp} 경험치
- 실패 패널티: 사망

## 현재 상황
- 위치: {game_state.player.position}
- 턴: {game_state.turn_count}

## 지시사항
1. 지하철이 갑자기 멈추고 시나리오가 시작되는 상황을 연출하세요
2. 시스템 창 형태로 시나리오 정보를 알려주세요 (목표, 제한 시간, 실패 패널티: 사망 반드시 포함)
3. 주변 상황 묘사 (패닉에 빠진 승객들)
4. 도깨비로서 짧은 코멘트 (2문장 이내)
5. 분위기 있게 웹소설처럼 서술

## 형식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[별빛 스트림이 연결되었습니다]
...시스템 메시지...
목표: ...
제한 시간: ...
실패 패널티: 사망
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(상황 묘사)

(도깨비 코멘트 - 따옴표로 감싸기)
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.PERSONALITY),
                HumanMessage(content=prompt),
            ])
            return response.content
        except Exception:
            # 실패 시 기본 메시지
            return self._default_opening(scenario)

    def _default_opening(self, scenario: ScenarioInfo) -> str:
        """기본 시나리오 시작 메시지"""
        return f"""지하철이 멈췄다.

갑자기. 아무 예고 없이.

형광등이 깜빡인다. 한 번. 두 번.
그리고 눈앞에, 푸른 빛의 창이 떠올랐다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[별빛 스트림이 연결되었습니다]
[<멸망한 세계에서 살아남는 세 가지 방법>의
 시나리오가 현실화됩니다]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[메인 시나리오 - {scenario.title}]
난이도: {scenario.difficulty}

목표: {scenario.objective}

보상: {scenario.reward_coins} 코인
제한시간: {scenario.time_limit if scenario.time_limit else '없음'}
실패 패널티: 사망
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

비명이 퍼진다. 누군가 문을 두드린다. 열리지 않는다.

"크크, 시작이군. 제한 시간 안에 못하면... 뭐, 알아서 알겠지?"

어디선가 들려오는 목소리. 보이지 않는 존재의 웃음소리."""

    def check_scenario_clear(
        self,
        game_state: GameState,
        player_action: str,
        killed_target: Optional[str] = None,
        narrative: str = "",
    ) -> tuple[bool, Optional[str]]:
        """
        시나리오 클리어 조건 체크.

        Args:
            game_state: 현재 게임 상태
            player_action: 플레이어 행동
            killed_target: 죽인 NPC 이름 (있다면)
            narrative: Director가 생성한 서술 (환경 생명체 검증용)

        Returns:
            (is_cleared, clear_method)
        """
        scenario = game_state.current_scenario
        if not scenario or scenario.status == "completed":
            return False, None

        # 첫 번째 시나리오: 생명체 하나를 죽여라
        if scenario.scenario_id in ("scenario_1", "main_scenario_1"):
            # NPC 살해인 경우
            if game_state.first_kill_completed:
                if killed_target:
                    if "강아지" in killed_target or "개" in killed_target or "동물" in killed_target:
                        return True, "kill_animal"
                    else:
                        return True, "kill_human"
                return True, "kill_unknown"

            # 강아지/반려동물 살해 감지 (NPC가 아닌 경우)
            # 플레이어 행동 + Director 서술 모두에서 확인되어야 함
            dog_kill = self._detect_dog_kill(player_action, narrative)
            if dog_kill:
                return True, "kill_animal"

            # 환경 생명체(곤충 등) 살해 감지
            # 플레이어 행동 + Director 서술 모두에서 확인되어야 함
            insect_kill = self._detect_insect_kill(player_action, narrative)
            if insect_kill:
                return True, "kill_insect"

        return False, None

    def _detect_insect_kill(self, player_action: str, narrative: str = "") -> bool:
        """
        플레이어 행동에서 곤충/환경 생명체 살해 감지.

        플레이어가 거짓말로 없는 생명체를 죽였다고 주장하는 것을 방지하기 위해,
        Director의 서술에서도 해당 생명체가 확인되어야 합니다.

        Args:
            player_action: 플레이어 행동
            narrative: Director가 생성한 서술

        Returns:
            True if insect/creature kill detected AND confirmed in narrative
        """
        action_lower = player_action.lower()
        narrative_lower = narrative.lower()

        # 곤충/소형 생명체 키워드
        insect_keywords = [
            "바퀴벌레", "바퀴 벌레", "벌레", "개미", "파리", "모기", "거미",
            "지네", "곤충", "벌", "나방", "나비", "딱정벌레",
            "쥐", "생쥐", "애벌레", "구더기"
        ]

        # 살해 행위 키워드
        kill_keywords = [
            "죽", "밟", "짓밟", "짓이기", "으깨", "때려",
            "잡아", "처치", "없애", "제거"
        ]

        # 살해 확인 키워드 (서술에서 실제로 죽었음을 확인)
        kill_confirm_keywords = [
            "죽", "밟", "짓이겨", "으깨", "터", "납작",
            "시체", "사체", "끈적", "잔해"
        ]

        # 플레이어 행동에서 곤충 + 살해 행위 확인
        has_insect_in_action = any(insect in action_lower for insect in insect_keywords)
        has_kill_in_action = any(kill in action_lower for kill in kill_keywords)

        if not (has_insect_in_action and has_kill_in_action):
            return False

        # 서술이 없으면 거부 (Director가 무시했다는 의미)
        if not narrative:
            return False

        # 서술에서 곤충이 언급되고, 살해가 확인되어야 함
        has_insect_in_narrative = any(insect in narrative_lower for insect in insect_keywords)
        has_kill_in_narrative = any(kw in narrative_lower for kw in kill_confirm_keywords)

        # 또는 서술에서 "없다", "보이지 않는다" 등이 있으면 거부
        denial_keywords = ["없다", "없어", "보이지 않", "찾을 수 없", "어디에도"]
        has_denial = any(denial in narrative_lower for denial in denial_keywords)

        if has_denial and not has_kill_in_narrative:
            return False

        return has_insect_in_narrative and has_kill_in_narrative

    def _detect_dog_kill(self, player_action: str, narrative: str = "") -> bool:
        """
        플레이어 행동에서 강아지/반려동물 살해 감지.

        강아지는 별도의 NPC가 아니라 '반려견_주인' NPC의 속성이므로,
        플레이어 행동과 서술에서 직접 감지해야 합니다.

        Args:
            player_action: 플레이어 행동
            narrative: Director가 생성한 서술

        Returns:
            True if dog/pet kill detected AND confirmed in narrative
        """
        action_lower = player_action.lower()
        narrative_lower = narrative.lower()

        # 강아지/반려동물 키워드
        dog_keywords = [
            "강아지", "개", "몽이", "포메라니안", "반려견", "애완견",
            "퍼피", "멍멍이", "댕댕이", "포메", "작은 동물"
        ]

        # 살해 행위 키워드
        kill_keywords = [
            "죽", "밟", "짓밟", "으깨", "때려", "찍", "비틀",
            "목", "졸", "던져", "내던져", "패", "치", "꺾",
            "부러", "살해", "처치", "없애", "제거", "처리"
        ]

        # 살해 확인 키워드 (서술에서 실제로 죽었음을 확인)
        kill_confirm_keywords = [
            "죽", "사망", "숨", "멈춰", "멈추", "축 늘어", "축늘어",
            "늘어졌", "늘어지", "쓰러졌", "쓰러지", "꺼졌", "꺼지",
            "움직이지 않", "시체", "사체", "피", "생명",
            "끝", "더 이상", "차갑", "식어", "비명", "절규"
        ]

        # 플레이어 행동에서 강아지 + 살해 행위 확인
        has_dog_in_action = any(dog in action_lower for dog in dog_keywords)
        has_kill_in_action = any(kill in action_lower for kill in kill_keywords)

        if not (has_dog_in_action and has_kill_in_action):
            return False

        # 서술이 없으면 거부 (Director가 무시했다는 의미)
        if not narrative:
            return False

        # 서술에서 강아지가 언급되고, 살해가 확인되어야 함
        has_dog_in_narrative = any(dog in narrative_lower for dog in dog_keywords)
        has_kill_in_narrative = any(kw in narrative_lower for kw in kill_confirm_keywords)

        # "없다", "보이지 않는다" 등이 있으면 거부
        denial_keywords = ["없다", "없어", "보이지 않", "찾을 수 없", "어디에도", "실패"]
        has_denial = any(denial in narrative_lower for denial in denial_keywords)

        if has_denial and not has_kill_in_narrative:
            return False

        return has_dog_in_narrative and has_kill_in_narrative

    async def generate_clear_announcement(
        self,
        game_state: GameState,
        clear_method: str,
        killed_target: Optional[str] = None,
    ) -> tuple[str, ScenarioClearRecord]:
        """
        시나리오 클리어 발표 및 기록 생성.

        Returns:
            (announcement_message, clear_record)
        """
        scenario = game_state.current_scenario
        if not scenario:
            return "", ScenarioClearRecord(
                scenario_id="unknown",
                scenario_title="Unknown",
                difficulty="?",
                cleared_at_turn=game_state.turn_count,
            )

        # 클리어 방식에 따른 성과 결정
        achievements = ["첫 시나리오 클리어"]
        bonus_rewards = []

        if clear_method == "kill_insect":
            achievements.append("현실적인 선택")
            bonus_rewards.append("곤충 살해 - 가장 합리적인 해석")
        elif clear_method == "kill_animal":
            achievements.append("자비로운 선택")
            bonus_rewards.append("동물 희생 - 도덕적 딜레마 회피")
        elif clear_method == "kill_human":
            achievements.append("무자비한 선택")
            bonus_rewards.append("인간 살해 - 성좌들의 관심 상승")

        # 살아남은 NPC와 죽은 NPC 파악
        alive_npcs = [npc.name for npc in game_state.npcs if npc.is_alive]
        dead_npcs = [npc.name for npc in game_state.npcs if not npc.is_alive]
        total_npcs = len(game_state.npcs)
        dead_count = len(dead_npcs)

        # 시나리오 1인지 확인 (상황 요약 포함)
        is_scenario_1 = scenario.scenario_id in ("scenario_1", "main_scenario_1")

        # 도깨비 코멘트 생성
        prompt = f"""시나리오가 클리어되었습니다. 도깨비로서 결과를 발표하세요.

## 클리어 정보
- 시나리오: {scenario.title}
- 클리어 방식: {clear_method}
- 죽인 대상: {killed_target or '알 수 없음'}
- 클리어 턴: {game_state.turn_count}
- 획득 보상: {scenario.reward_coins} 코인, {scenario.reward_exp} 경험치

## 객차 상황
- 전체 승객: {total_npcs}명
- 사망자: {dead_count}명
- 살아남은 사람: {', '.join(alive_npcs[:5]) if alive_npcs else '없음'}
- 사망한 사람: {', '.join(dead_npcs[:5]) if dead_npcs else '없음'}

## 지시사항
1. 시스템 창으로 클리어 알림
2. **상황 요약**: 객차 안의 상황을 빠르게 요약 (누가 살아남았고, 시간 내에 클리어하지 못한 사람들은 어떻게 되었는지)
3. **비극적 현실**: 시나리오를 클리어하지 못한 승객들은 "사망"했음을 암시 (비명, 쓰러지는 소리, 갑자기 조용해진 객차)
4. 도깨비의 짧은 평가
5. **다음 시나리오 예고**: "한강 대교" - 지하철을 탈출해 한강을 건너야 한다는 것을 암시

형식:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[시나리오 클리어!]
'{scenario.title}' 완료
보상: {scenario.reward_coins} 코인, {scenario.reward_exp} 경험치
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(상황 요약 - 객차의 비극적 상황)

(도깨비 코멘트)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[다음 시나리오 예고]
E급: 한강 대교
목표: 한강 대교를 건너 생존 구역에 도달하시오.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.PERSONALITY),
                HumanMessage(content=prompt),
            ])
            dokkaebi_comment = response.content
        except Exception:
            dokkaebi_comment = self._default_clear_announcement(scenario, clear_method)

        # 클리어 기록 생성
        record = ScenarioClearRecord(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            difficulty=scenario.difficulty,
            cleared_at_turn=game_state.turn_count,
            clear_method=clear_method,
            target_killed=killed_target,
            coins_earned=scenario.reward_coins,
            exp_earned=scenario.reward_exp,
            bonus_rewards=bonus_rewards,
            achievements=achievements,
            dokkaebi_comment=dokkaebi_comment[:200] if dokkaebi_comment else "",
        )

        # 상태 업데이트
        state = self.get_or_create_state(game_state.session_id)
        state.clear_records.append(record)
        state.total_scenarios_cleared += 1

        return dokkaebi_comment, record

    def _default_clear_announcement(self, scenario: ScenarioState, clear_method: str) -> str:
        """기본 클리어 발표 메시지"""
        method_comment = {
            "kill_insect": "크크, 벌레? 규칙의 허점을 찾았군. 머리 쓸 줄 아는 녀석이야.",
            "kill_animal": "동물을 선택했군. 인간보다 쉬운 선택이지.",
            "kill_human": "크크, 인간을 죽였어? 흥미로운 선택이야.",
            "kill_unknown": "어쨌든 죽였으니 됐어.",
        }

        comment = method_comment.get(clear_method, "클리어는 클리어지.")

        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[시나리오 클리어!]

'{scenario.title}' 완료

보상 지급:
- {scenario.reward_coins} 코인
- {scenario.reward_exp} 경험치
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

갑자기, 객차 곳곳에서 비명이 터져 나왔다.

쿵. 쿵. 쿵.

무언가 쓰러지는 소리. 한 명, 두 명... 시간 안에 시나리오를 클리어하지 못한 사람들이다.
몇 초 전까지 살아있던 사람들이 바닥에 쓰러져 있다. 숨을 쉬지 않는다.

그리고, 객차가 조용해졌다.

"{comment}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[다음 시나리오 예고]
E급: 한강 대교
목표: 한강 대교를 건너 생존 구역에 도달하시오.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"크크, 이제부터가 진짜 시작이야. 지하철 밖은... 훨씬 위험하거든."
"""

    async def generate_progress_comment(
        self,
        game_state: GameState,
        player_action: str,
        significant_event: Optional[str] = None,
    ) -> Optional[str]:
        """
        중요한 순간에 도깨비 코멘트 생성.

        모든 턴에 나오지 않고, 의미 있는 순간에만.
        """
        # 코멘트가 필요한 상황인지 판단
        should_comment = False

        # 중요 이벤트가 있을 때
        if significant_event:
            should_comment = True

        # 시나리오 진행률이 특정 지점에 도달했을 때
        scenario = game_state.current_scenario
        if scenario and scenario.remaining_time:
            if scenario.remaining_time <= 3:  # 시간이 얼마 안 남았을 때
                should_comment = True

        if not should_comment:
            return None

        prompt = f"""상황에 대해 도깨비로서 짧은 코멘트를 하세요.

## 상황
- 플레이어 행동: {player_action}
- 특별 이벤트: {significant_event or '없음'}
- 시나리오 남은 시간: {scenario.remaining_time if scenario and scenario.remaining_time else '제한 없음'}턴

## 지시사항
- 1-2문장으로 짧게
- 비꼬거나 의미심장하게
- 직접적인 힌트는 주지 않음
- 따옴표로 감싸서 대사 형식으로
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.PERSONALITY),
                HumanMessage(content=prompt),
            ])
            return response.content
        except Exception:
            return None

    def get_clear_records(self, session_id: str) -> list[ScenarioClearRecord]:
        """세션의 클리어 기록 조회"""
        state = self._states.get(session_id)
        if state:
            return state.clear_records
        return []

    def get_statistics(self, session_id: str) -> dict:
        """세션 통계 조회"""
        state = self._states.get(session_id)
        if not state:
            return {"total_cleared": 0, "achievements": []}

        all_achievements = []
        for record in state.clear_records:
            all_achievements.extend(record.achievements)

        return {
            "total_cleared": state.total_scenarios_cleared,
            "achievements": list(set(all_achievements)),
            "clear_records": [r.model_dump() for r in state.clear_records],
        }

    # ================================================================
    # 룰 브리핑 기능
    # ================================================================

    def detect_rule_event(
        self,
        player_action: str,
        game_state: GameState,
        new_position: Optional[str] = None,
    ) -> Optional[str]:
        """
        플레이어 행동에서 도깨비 개입이 필요한 룰 이벤트 감지.

        Returns:
            이벤트 타입 또는 None
            - "area_transition": 새 구역 이동
            - "suicide_attempt": 자살 시도
            - "death": 사망
            - "rule_violation": 규칙 위반
            - "time_warning": 시간 경고
        """
        action_lower = player_action.lower()

        # 자살/자해 시도 감지
        suicide_keywords = ["자살", "자해", "목숨", "죽겠", "죽을", "스스로 죽"]
        if any(kw in action_lower for kw in suicide_keywords):
            return "suicide_attempt"

        # 새 구역 이동
        if new_position and new_position != game_state.player.position:
            # 처음 방문하는 구역인지 확인
            if new_position not in game_state.discovered_locations:
                return "area_transition"

        # 사망 체크
        if game_state.player.health <= 0:
            return "death"

        # 시간 경고
        scenario = game_state.current_scenario
        if scenario and scenario.remaining_time is not None:
            if scenario.remaining_time == 3:
                return "time_warning"

        return None

    async def generate_area_transition_briefing(
        self,
        game_state: GameState,
        new_position: str,
        area_description: str,
    ) -> str:
        """새 구역 진입 시 도깨비 브리핑"""
        prompt = f"""플레이어가 새로운 구역으로 이동했습니다. 도깨비로서 구역을 안내하세요.

## 이동 정보
- 이전 위치: {game_state.player.position}
- 새 위치: {new_position}
- 구역 설명: {area_description}

## 현재 상태
- 턴: {game_state.turn_count}
- 시나리오: {game_state.current_scenario.title if game_state.current_scenario else '없음'}
- 시나리오 상태: {game_state.current_scenario.status if game_state.current_scenario else 'N/A'}

## 지시사항
1. 구역 전환을 알리는 시스템 메시지
2. 도깨비의 짧은 코멘트 (1-2문장)
3. 새 구역의 위험도나 특징에 대한 힌트 (간접적으로)

형식:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[구역 이동]
{new_position}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(도깨비 코멘트)
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.PERSONALITY),
                HumanMessage(content=prompt),
            ])
            return response.content
        except Exception:
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[구역 이동]
{new_position}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"새 구역이군. 조심해, 뭐가 있을지 모르니까."
"""

    async def generate_death_briefing(
        self,
        game_state: GameState,
        cause_of_death: str,
    ) -> str:
        """플레이어 사망 시 도깨비 브리핑"""
        prompt = f"""플레이어가 사망했습니다. 도깨비로서 사망을 선언하세요.

## 사망 정보
- 사망 원인: {cause_of_death}
- 턴: {game_state.turn_count}
- 위치: {game_state.player.position}
- 시나리오: {game_state.current_scenario.title if game_state.current_scenario else '없음'}

## 지시사항
1. 사망 선언 시스템 메시지
2. 도깨비의 냉정한 평가 (1-2문장)
3. 약간의 비꼬는 어조

형식:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[사망]
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(도깨비 코멘트)
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.PERSONALITY),
                HumanMessage(content=prompt),
            ])
            return response.content
        except Exception:
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[사망]

참가자가 사망하였습니다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"끝이야. 이렇게 허무하게? 좀 더 재미있을 줄 알았는데."
"""

    async def generate_suicide_warning(
        self,
        game_state: GameState,
        player_action: str,
    ) -> str:
        """자살 시도 시 도깨비 경고"""
        prompt = f"""플레이어가 자살/자해를 시도했습니다. 도깨비로서 이를 막고 규칙을 설명하세요.

## 상황
- 플레이어 행동: {player_action}
- 턴: {game_state.turn_count}
- 시나리오: {game_state.current_scenario.title if game_state.current_scenario else '없음'}

## 지시사항
1. 자살은 시나리오에서 허용되지 않는다고 설명
2. 규칙 위반 경고
3. 약간 재미있어하는 어조로, 하지만 단호하게
4. "그렇게 쉽게 끝날 거라고 생각했어?" 같은 뉘앙스

형식:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[규칙 위반 - 무효]
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(도깨비 코멘트)
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.PERSONALITY),
                HumanMessage(content=prompt),
            ])
            return response.content
        except Exception:
            return """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[규칙 위반 - 무효]

자해/자살은 시나리오 규칙에 의해
허용되지 않습니다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"크크, 그렇게 쉽게 도망칠 수 있을 거라고 생각했어? 규칙은 규칙이야. 네가 직접 끝내는 건 허용 안 돼."
"""

    async def generate_time_warning(
        self,
        game_state: GameState,
    ) -> str:
        """시간 제한 경고"""
        scenario = game_state.current_scenario
        remaining = scenario.remaining_time if scenario else 0

        prompt = f"""시나리오 제한 시간이 얼마 남지 않았습니다. 도깨비로서 경고하세요.

## 상황
- 시나리오: {scenario.title if scenario else '없음'}
- 남은 시간: {remaining}턴
- 목표: {scenario.objective if scenario else '없음'}

## 지시사항
1. 시간 경고 시스템 메시지
2. 도깨비의 재촉하는 코멘트 (1-2문장)
3. 긴박감을 주되 직접적인 힌트는 주지 않음

형식:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[경고]
제한 시간: {remaining}턴 남음
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(도깨비 코멘트)
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.PERSONALITY),
                HumanMessage(content=prompt),
            ])
            return response.content
        except Exception:
            return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[경고]
제한 시간: {remaining}턴 남음
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"시간이 없어. 뭘 망설이는 거야?"
"""

    async def generate_rule_briefing(
        self,
        event_type: str,
        game_state: GameState,
        player_action: str = "",
        new_position: Optional[str] = None,
        area_description: str = "",
        cause_of_death: str = "",
    ) -> Optional[str]:
        """
        이벤트 타입에 따른 적절한 브리핑 생성.

        Args:
            event_type: detect_rule_event()에서 반환된 이벤트 타입
            game_state: 현재 게임 상태
            player_action: 플레이어 행동
            new_position: 새 위치 (area_transition인 경우)
            area_description: 구역 설명 (area_transition인 경우)
            cause_of_death: 사망 원인 (death인 경우)

        Returns:
            도깨비 브리핑 메시지 또는 None
        """
        if event_type == "area_transition" and new_position:
            return await self.generate_area_transition_briefing(
                game_state, new_position, area_description
            )
        elif event_type == "death":
            return await self.generate_death_briefing(game_state, cause_of_death)
        elif event_type == "suicide_attempt":
            return await self.generate_suicide_warning(game_state, player_action)
        elif event_type == "time_warning":
            return await self.generate_time_warning(game_state)

        return None
