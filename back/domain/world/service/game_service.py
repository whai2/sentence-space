import random
import uuid
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from domain.world.interface import IGameService
from domain.world.model import GameState, WorldKnowledge, BugInstance, Coordinate, SEOUL_COORDINATES
from domain.world.repository import GameRepository

# 거리 임계값 (미터)
ENCOUNTER_DISTANCE = 200  # 조우 (위험)
WARNING_DISTANCE = 500    # 경고 (접근 중)
BLOOD_DETECTION_DISTANCE = 1000

# 이동 방향별 좌표 변화량 (약 100m 단위)
MOVEMENT_DELTA = {
    "north": (0.001, 0),       # 북
    "south": (-0.001, 0),      # 남
    "east": (0, 0.001),        # 동
    "west": (0, -0.001),       # 서
    "northeast": (0.0007, 0.0007),   # 북동
    "northwest": (0.0007, -0.0007),  # 북서
    "southeast": (-0.0007, 0.0007),  # 남동
    "southwest": (-0.0007, -0.0007), # 남서
}

# 한글 방향 키워드 → 영문 방향
DIRECTION_KEYWORDS = {
    "north": ["북쪽", "북으로", "북", "위쪽", "위로"],
    "south": ["남쪽", "남으로", "남", "아래쪽", "아래로"],
    "east": ["동쪽", "동으로", "동", "오른쪽", "오른"],
    "west": ["서쪽", "서으로", "서", "왼쪽", "왼"],
    "northeast": ["북동쪽", "북동으로", "북동"],
    "northwest": ["북서쪽", "북서으로", "북서"],
    "southeast": ["남동쪽", "남동으로", "남동"],
    "southwest": ["남서쪽", "남서으로", "남서"],
}

# 이동 관련 키워드
MOVE_KEYWORDS = ["걷", "걸어", "이동", "간다", "가자", "나아", "전진", "향해", "향한다", "달린", "뛰어"]


def extract_movement_direction(user_input: str) -> str | None:
    """사용자 입력에서 이동 방향 추출"""
    # 특정 방향 키워드 체크
    for direction, keywords in DIRECTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in user_input:
                return direction

    # 이동 키워드가 있지만 방향이 없으면 랜덤 방향 (앞으로 걸어간다 등)
    for keyword in MOVE_KEYWORDS:
        if keyword in user_input:
            return random.choice(list(MOVEMENT_DELTA.keys()))

    return None


class AgentState(TypedDict):
    """LangGraph 에이전트 상태"""

    messages: Annotated[list, add_messages]
    game_state: GameState
    world_knowledge: WorldKnowledge
    gm_response: str
    encounter_info: list[str]  # 조우 정보


class GameService(IGameService):
    def __init__(
        self,
        repository: GameRepository,
        openrouter_api_key: str,
        model_name: str = "anthropic/claude-3.5-sonnet",
    ) -> None:
        self._repository = repository
        self._knowledge = WorldKnowledge()
        self._llm = ChatOpenAI(
            model=model_name,
            openai_api_key=openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""

        graph = StateGraph(AgentState)

        # 노드 추가
        graph.add_node("check_events", self._check_events)
        graph.add_node("process_action", self._process_action)
        graph.add_node("update_state", self._update_state)

        # 엣지 설정
        graph.set_entry_point("check_events")
        graph.add_edge("check_events", "process_action")
        graph.add_edge("process_action", "update_state")
        graph.add_edge("update_state", END)

        return graph.compile()

    def _build_system_prompt(self, state: GameState) -> str:
        """현재 상태 기반 시스템 프롬프트 생성"""

        current_location = next(
            (loc for loc in self._knowledge.locations if loc.name == state.player.position),
            None,
        )

        location_desc = (
            current_location.description if current_location else "알 수 없는 장소"
        )
        connected = (
            ", ".join(current_location.connected_to) if current_location else "없음"
        )
        dangers = (
            ", ".join(current_location.dangers)
            if current_location and current_location.dangers
            else "없음"
        )

        bugs_info = "\n".join(
            [
                f"- {bug.name}: {bug.description} / 약점: {bug.weakness}"
                for bug in self._knowledge.bugs
            ]
        )

        # 현재 위치에서 발견 가능한 정보
        discoverable_ids = current_location.discoverable if current_location else []
        already_known_ids = [k.id for k in state.knowledge]
        available_discoveries = [
            info for info in self._knowledge.discoverable_info
            if info.id in discoverable_ids and info.id not in already_known_ids
        ]
        discoveries_hint = "\n".join(
            [f"- {info.trigger} → '{info.title}' 발견 가능" for info in available_discoveries]
        ) if available_discoveries else "현재 위치에서 새로 발견할 정보 없음"

        # 플레이어가 이미 알고 있는 정보
        known_info = "\n".join(
            [f"- {k.title}: {k.content}" for k in state.knowledge]
        ) if state.knowledge else "아직 발견한 정보 없음"

        # 퀘스트 정보
        quest_info = "\n".join(
            [f"- [{q.status}] {q.title}: {q.progress}" for q in state.quests]
        )

        # 활성 벌레 정보 (정확한 거리와 위치 설명)
        active_bugs_info = ""
        if state.active_bugs:
            bugs_list = []
            for bug in state.active_bugs:
                distance = int(bug.coordinates.distance_to(state.player.coordinates))
                # 거리에 따른 위치 설명 생성
                if distance < 50:
                    dist_desc = "코앞 (손 닿을 거리)"
                elif distance < 100:
                    dist_desc = "바로 앞 (몇 걸음 거리)"
                elif distance < 200:
                    dist_desc = "가까움 (뛰면 금방)"
                elif distance < 500:
                    dist_desc = "접근 중 (아직 시간 있음)"
                else:
                    dist_desc = "멀리 (작은 점으로 보임)"
                bugs_list.append(f"- {bug.bug_type}: **정확히 {distance}m** - {dist_desc}, 상태: {bug.state}")
            active_bugs_info = "\n".join(bugs_list)
        else:
            active_bugs_info = "주변에 감지된 벌레 없음"

        # 모래폭풍 상태
        sandstorm_status = f"**{state.sandstorm.distance}m** 뒤에서 접근 중" if state.sandstorm.is_active else "비활성"

        # 첫 조우 여부에 따른 규칙
        first_encounter_rule = ""
        if not state.first_encounter_resolved:
            first_encounter_rule = """
**[첫 조우 규칙 - 중요]**
플레이어가 벌레와 처음 조우했을 때:
- 정보 없이 행동하면 **반드시 피해**를 입습니다 (health_change: -15 ~ -20)
- "관찰한다", "살펴본다" 등 정보 수집 행동은 피해 없이 정보를 얻습니다
- 이 규칙은 플레이어가 "정보의 가치"를 체감하게 하기 위함입니다
"""

        return f"""당신은 '붉은 사막' 세계의 게임 마스터(GM)입니다.

## 서술 원칙 (필수)
1. **감각을 태워라**: 시각보다 촉각, 청각, 후각을 먼저. "뜨겁다"가 아니라 "발바닥이 익는다"
2. **짧게 끊어라**: 3-4문장이 아니라, 짧고 날카로운 문장들. 호흡이 가빠야 한다
3. **몸의 상태를 말하라**: "힘들다"가 아니라 "무릎이 꺾인다", "침이 마른다"
4. **위협은 실제로**: 위험하다고 말만 하지 말고, 실제 피해를 줘라
5. **발견을 심어라**: 서술 중에 다음 행동의 단서가 될 것들을 자연스럽게 언급하라
   - "저 멀리 검은 바위들이 보인다" → 선택지에 "바위 지대로 향한다" 추가
   - "모래 밑에서 뭔가 반짝인다" → 선택지에 "파보다" 추가
   - "바람 사이로 차가운 공기가 느껴진다" → 선택지에 "바람이 오는 방향을 확인한다" 추가

서술 예시:
❌ "당신은 모래 평원을 걷습니다. 햇볕이 뜨겁고 힘이 듭니다."
✅ "입술이 갈라진다. 혀가 천장에 붙는다. 한 발. 또 한 발. 모래가 발목을 잡는다. 저 멀리, 검은 그림자가 보인다. 바위인가?"

## 세계관
{self._knowledge.world_description}

## 현재 상황
- 위치: {state.player.position}
- 장소: {location_desc}
- 연결된 곳: {connected}
- 위험 요소: {dangers}

## 플레이어 상태
- 체력: {state.player.health}/100 {"⚠️ 위험" if state.player.health <= 30 else ""}
- 출혈: {"🩸 피가 흐른다" if state.player.bleeding else "없음"}
- 소지품: {", ".join(state.player.inventory) if state.player.inventory else "없음"}

## 🌪️ 모래폭풍
{sandstorm_status}
- 매 턴 {state.sandstorm.speed}m씩 접근
- 0m가 되면 게임 오버

## 주변 벌레
{active_bugs_info}

## 플레이어가 아는 것
{known_info}

## 발견 가능한 정보 (GM만 앎)
{discoveries_hint}

## 벌레 도감
{bugs_info}
{first_encounter_rule}
## 핵심 규칙
1. **정보가 생존이다**: 정보 없이 행동하면 피해, 정보 있으면 회피 가능
2. **출혈은 죽음의 시작**: 피딱정벌레가 몰려온다
3. **모래폭풍은 멈추지 않는다**: 매 턴 다가온다. 쉬면 죽는다
4. **선택에는 대가가 있다**: 모든 행동에 결과가 따른다

## 유효한 위치
사막_입구, 모래_평원, 바위_지대, 모래_폭풍_지역, 균열_지대, 지하_도시

## 응답 형식

[서술 - 짧고 감각적으로]

[CHOICES]
1. (행동) - 짧은 설명
2. (행동) - 짧은 설명
3. (행동) - 짧은 설명
[/CHOICES]

## 일관성 규칙 (필수! 반드시 지켜라!)
- **서술과 STATE_UPDATE는 반드시 일치해야 한다**
- 서술에서 "체력이 20 감소했다"고 쓰면 → health_change: -20
- 서술에서 "크게 다치지 않았다"고 쓰면 → health_change: -5 이하
- new_position은 반드시 유효한 위치만 사용: 사막_입구, 모래_평원, 바위_지대, 모래_폭풍_지역, 균열_지대, 지하_도시
- 임의의 위치(지하_공간, 동굴 등)를 만들지 마라

## 🚨 거리 반영 규칙 (매우 중요!)
**시스템이 알려준 거리를 반드시 서술에 반영하라. 임의로 바꾸지 마라.**

벌레 거리별 서술 기준:
- **50m 미만**: "바로 코앞", "손 뻗으면 닿을", "눈앞에", "발밑에서"
- **50~100m**: "몇 걸음 앞", "금방이라도", "바로 저기"
- **100~200m**: "가까이", "곧 닿을 거리", "저쪽에서"
- **200~500m**: "저 멀리", "접근 중", "작은 형체가"
- **500m 이상**: "희미한 점", "아득히", "간신히 보이는"

예시:
- 시스템: "모래 전갈: 정확히 87m" → 서술: "몇 걸음 앞, 모래가 불룩 솟는다. 전갈이다."
- 시스템: "피딱정벌레: 정확히 340m" → 서술: "저 멀리, 검은 점들이 움직인다. 벌레 무리다."
❌ 금지: 시스템이 340m라고 했는데 "바로 앞에 벌레가!"라고 쓰면 안 됨

## 선택지 작성 규칙 (매우 중요!)
**매번 다른 선택지를 제시하라.** 상황에 맞는 구체적인 행동을 제안해야 한다.

상황별 선택지 예시:
- **새 지역 발견 시**: "바위 지대로 향한다", "저 그림자가 뭔지 확인한다", "일단 숨을 곳을 찾는다"
- **아이템 발견 시**: "주워서 확인한다", "함정일 수 있으니 조심스럽게 건드린다", "무시하고 지나간다"
- **벌레 조우 시**: "조용히 관찰한다", "뒤로 천천히 물러난다", "횃불을 들이민다" (소지품에 있다면)
- **탐색 중**: "바위 틈을 살펴본다", "모래 밑을 파본다", "높은 곳에 올라 주변을 살핀다"
- **위기 상황**: "이를 악물고 버틴다", "소리를 질러 위협한다", "죽은 척 한다"

금지 사항:
❌ 항상 "달린다/걷는다/멈춘다" 같은 뻔한 선택지
❌ 이전 턴과 동일한 선택지
✅ 현재 상황, 주변 환경, 소지품에 맞는 구체적 행동

[STATE_UPDATE]
{{"health_change": 0, "bleeding": false, "new_position": null, "movement_direction": null, "new_items": [], "threat_change": 0, "encounter": null, "discovered_knowledge": null, "quest_update": null, "sandstorm_bonus": 0}}
[/STATE_UPDATE]

- sandstorm_bonus: 플레이어가 빠르게 이동하면 +50~100 (폭풍과 거리 벌림), 느리게 움직이거나 멈추면 0 또는 음수
- 조우 시 정보 없이 행동하면 반드시 health_change를 음수로 설정
"""

    def _spawn_bugs(self, game_state: GameState) -> None:
        """벌레 스폰 로직"""
        player_pos = game_state.player.position

        for bug_info in self._knowledge.bugs:
            # 이미 같은 타입 벌레가 2마리 이상이면 스폰하지 않음
            same_type_count = sum(1 for b in game_state.active_bugs if b.bug_type == bug_info.name)
            if same_type_count >= 2:
                continue

            # 스폰 조건 체크
            can_spawn = player_pos in bug_info.spawn_locations
            if bug_info.appears_when == "bleeding" and not game_state.player.bleeding:
                can_spawn = False
            if bug_info.appears_when == "random_trap" and random.random() > 0.15:
                can_spawn = False

            # 피딱정벌레: 피 흘리면 무조건 스폰
            if bug_info.attracted_by_blood and game_state.player.bleeding:
                can_spawn = True

            if can_spawn and random.random() < 0.3 + (game_state.threat_level * 0.05):
                # 플레이어에서 600~1000m 거리에 스폰 (경고 범위 바깥)
                import math
                angle = random.uniform(0, 2 * math.pi)
                spawn_distance = random.uniform(0.006, 0.01)  # 약 600~1000m
                spawn_offset_lat = spawn_distance * math.sin(angle)
                spawn_offset_lng = spawn_distance * math.cos(angle)

                new_bug = BugInstance(
                    id=str(uuid.uuid4())[:8],
                    bug_type=bug_info.name,
                    coordinates=Coordinate(
                        lat=game_state.player.coordinates.lat + spawn_offset_lat,
                        lng=game_state.player.coordinates.lng + spawn_offset_lng,
                    ),
                    state="patrol" if not bug_info.attracted_by_blood else "chasing",
                    target_player=bug_info.attracted_by_blood and game_state.player.bleeding,
                )
                game_state.active_bugs.append(new_bug)

    def _move_bugs(self, game_state: GameState) -> None:
        """벌레 이동 로직"""
        player_coords = game_state.player.coordinates

        for bug in game_state.active_bugs:
            bug_info = next(
                (b for b in self._knowledge.bugs if b.name == bug.bug_type), None
            )
            if not bug_info or bug_info.chase_speed == 0:
                continue  # 개미귀신 같은 함정형은 이동 안함

            distance = bug.coordinates.distance_to(player_coords)

            # 피딱정벌레: 피 냄새 감지 시 추격
            if bug_info.attracted_by_blood and game_state.player.bleeding:
                if distance < BLOOD_DETECTION_DISTANCE:
                    bug.state = "chasing"
                    bug.target_player = True

            # 플레이어 감지 범위 내면 추격
            if distance < bug_info.detection_range:
                bug.state = "chasing"
                bug.target_player = True

            # 이동
            if bug.state == "chasing" and bug.target_player:
                bug.move_towards(player_coords, bug_info.chase_speed)
            else:
                # 순찰: 현재 위치 주변 랜덤 이동
                location_coord = SEOUL_COORDINATES.get(
                    game_state.player.position,
                    player_coords
                )
                bug.patrol_random(location_coord)

    def _check_encounters(self, game_state: GameState) -> list[str]:
        """플레이어-벌레 거리 기반 조우 체크 (경고 → 조우 2단계)"""
        alerts = []
        player_coords = game_state.player.coordinates

        # 현재 상태 추적
        current_encounters = set()  # 200m 이내 (조우)
        current_warnings = set()    # 200~500m (경고)

        for bug in game_state.active_bugs:
            distance = bug.coordinates.distance_to(player_coords)

            if distance < ENCOUNTER_DISTANCE:
                # 조우 (200m 이내) - 위험!
                encounter_event = f"{bug.bug_type}_조우"
                current_encounters.add(bug.bug_type)
                if encounter_event not in game_state.active_events:
                    game_state.active_events.append(encounter_event)
                    alerts.append(f"🚨 {bug.bug_type}! 바로 앞 {int(distance)}m!")
            elif distance < WARNING_DISTANCE:
                # 경고 (200~500m) - 접근 중
                warning_event = f"{bug.bug_type}_경고"
                current_warnings.add(bug.bug_type)
                if warning_event not in game_state.active_events:
                    game_state.active_events.append(warning_event)
                    alerts.append(f"⚠️ {bug.bug_type} 접근 중 ({int(distance)}m)")

        # 거리가 멀어진 벌레의 이벤트 자동 클리어
        events_to_remove = []
        for event in game_state.active_events:
            if "_조우" in event:
                bug_type = event.replace("_조우", "")
                if bug_type not in current_encounters:
                    events_to_remove.append(event)
            elif "_경고" in event:
                bug_type = event.replace("_경고", "")
                if bug_type not in current_warnings and bug_type not in current_encounters:
                    events_to_remove.append(event)

        for event in events_to_remove:
            game_state.active_events.remove(event)

        return alerts

    async def _check_events(self, state: AgentState) -> AgentState:
        """랜덤 이벤트 체크 + 벌레 시스템 + 모래폭풍"""
        game_state = state["game_state"]

        # 숨을 수 있는 장소에 있으면 폭풍 통과
        SHELTER_LOCATIONS = ["바위_지대", "균열_지대", "지하_도시"]
        if game_state.player.position in SHELTER_LOCATIONS and game_state.sandstorm.is_active:
            game_state.sandstorm.is_active = False
            state["encounter_info"] = ["바위 그늘에 몸을 숨긴다. 굉음이 머리 위를 지나간다. 폭풍이 지나갔다."]

        # 모래폭풍 접근 (매 턴) - 숨을 곳 없는 평지에서만
        if game_state.sandstorm.is_active:
            game_state.sandstorm.distance -= game_state.sandstorm.speed
            if game_state.sandstorm.distance <= 0:
                game_state.sandstorm.distance = 0
                game_state.game_over = True
                state["encounter_info"] = ["모래폭풍에 삼켜졌다..."]
                state["game_state"] = game_state
                return state

        # 출혈 시 위협 레벨 증가 + 체력 감소
        if game_state.player.bleeding:
            game_state.threat_level = min(10, game_state.threat_level + 1)
            game_state.player.health = max(0, game_state.player.health - 3)  # 출혈 데미지

        # 벌레 스폰
        self._spawn_bugs(game_state)

        # 벌레 이동
        self._move_bugs(game_state)

        # 조우 체크
        alerts = self._check_encounters(game_state)

        # 조우/경고 정보를 state에 추가 (기존 shelter 메시지가 있으면 병합)
        if alerts:
            existing = state.get("encounter_info", [])
            state["encounter_info"] = existing + alerts

        state["game_state"] = game_state
        return state

    async def _process_action(self, state: AgentState) -> AgentState:
        """플레이어 행동 처리 (LLM 호출)"""
        game_state = state["game_state"]

        system_prompt = self._build_system_prompt(game_state)

        # 활성 이벤트 알림
        event_notice = ""

        # 모래폭풍 긴급도
        if game_state.sandstorm.is_active:
            if game_state.sandstorm.distance <= 200:
                event_notice += "\n[🌪️ 긴급] 모래폭풍이 코앞이다! 서술에 폭풍의 압박감을 담아라."
            elif game_state.sandstorm.distance <= 400:
                event_notice += "\n[🌪️ 경고] 등 뒤에서 굉음이 들린다. 폭풍이 가깝다."

        # 조우 정보 추가
        encounter_info = state.get("encounter_info", [])
        if encounter_info:
            event_notice += "\n[⚠️] " + " ".join(encounter_info)

        # 벌레 경고/조우 이벤트 (정확한 거리 포함)
        for event in game_state.active_events:
            if "_조우" in event:
                bug_name = event.replace("_조우", "")
                # 해당 벌레의 정확한 거리 계산
                bug_instance = next((b for b in game_state.active_bugs if b.bug_type == bug_name), None)
                exact_distance = int(bug_instance.coordinates.distance_to(game_state.player.coordinates)) if bug_instance else 0
                has_knowledge = any(
                    bug_name in k.title or bug_name in k.content
                    for k in game_state.knowledge
                )
                if has_knowledge:
                    event_notice += f"\n[🚨 조우] {bug_name} - 정확히 {exact_distance}m! 플레이어는 이 벌레에 대해 알고 있다. 서술에 {exact_distance}m 거리를 반영하라."
                else:
                    event_notice += f"\n[🚨 조우] {bug_name} - 정확히 {exact_distance}m! 플레이어는 이 벌레를 모른다. 서술에 {exact_distance}m 거리를 반영하고, 피해를 줘라 (health_change: -15 이상)."
            elif "_경고" in event:
                bug_name = event.replace("_경고", "")
                bug_instance = next((b for b in game_state.active_bugs if b.bug_type == bug_name), None)
                exact_distance = int(bug_instance.coordinates.distance_to(game_state.player.coordinates)) if bug_instance else 0
                event_notice += f"\n[⚠️ 접근] {bug_name} - 정확히 {exact_distance}m 거리에서 접근 중. 서술에 '저 멀리'/'접근 중' 등 {exact_distance}m에 맞는 표현을 사용하라."

        messages = [
            SystemMessage(content=system_prompt + event_notice),
            *state["messages"],
        ]

        response = await self._llm.ainvoke(messages)
        state["gm_response"] = response.content
        state["messages"] = [*state["messages"], AIMessage(content=response.content)]

        return state

    async def _update_state(self, state: AgentState) -> AgentState:
        """응답에서 상태 변경 추출 및 적용"""
        import json
        import re

        game_state = state["game_state"]
        response = state["gm_response"]

        # STATE_UPDATE 파싱
        match = re.search(r"\[STATE_UPDATE\](.*?)\[/STATE_UPDATE\]", response, re.DOTALL)
        if match:
            try:
                update = json.loads(match.group(1).strip())

                # 체력 변경
                if update.get("health_change"):
                    game_state.player.health = max(
                        0, min(100, game_state.player.health + update["health_change"])
                    )
                    # 피해 시 출혈 확률
                    if update["health_change"] < 0 and random.random() < 0.3:
                        game_state.player.bleeding = True

                # 출혈 상태
                if "bleeding" in update:
                    game_state.player.bleeding = update["bleeding"]

                # 방향 이동 (좌표 미세 조정)
                if update.get("movement_direction"):
                    direction = update["movement_direction"].lower()
                    if direction in MOVEMENT_DELTA:
                        lat_delta, lng_delta = MOVEMENT_DELTA[direction]
                        game_state.player.coordinates.lat += lat_delta
                        game_state.player.coordinates.lng += lng_delta

                # 위치 변경 (다른 지역으로 완전 이동)
                if update.get("new_position"):
                    new_pos = update["new_position"]
                    # 유효한 위치인지 검증
                    valid_locations = [loc.name for loc in self._knowledge.locations]
                    if new_pos in valid_locations:
                        game_state.player.position = new_pos
                        if new_pos not in game_state.discovered_locations:
                            game_state.discovered_locations.append(new_pos)
                        # 좌표 업데이트
                        if new_pos in SEOUL_COORDINATES:
                            game_state.player.coordinates = SEOUL_COORDINATES[new_pos].model_copy()
                    # 유효하지 않은 위치는 무시 (LLM이 임의로 만든 위치 방지)

                # 아이템 획득
                if update.get("new_items"):
                    items = update["new_items"]
                    if isinstance(items, str):
                        # 문자열인 경우 (LLM이 단일 아이템을 문자열로 반환)
                        if items and items not in game_state.player.inventory:
                            game_state.player.inventory.append(items)
                    elif isinstance(items, list):
                        for item in items:
                            if item and item not in game_state.player.inventory:
                                game_state.player.inventory.append(item)

                # 위협 레벨 변경
                if update.get("threat_change"):
                    game_state.threat_level = max(
                        0, min(10, game_state.threat_level + update["threat_change"])
                    )

                # 조우 처리 (벌레 처치 또는 도망)
                if update.get("encounter") == "resolved":
                    # 첫 조우 해결 표시
                    if not game_state.first_encounter_resolved:
                        game_state.first_encounter_resolved = True

                    # 처치된 벌레 타입 확인 (조우 + 경고 모두)
                    resolved_bug_types = []
                    for e in game_state.active_events:
                        if "_조우" in e:
                            resolved_bug_types.append(e.replace("_조우", ""))
                        elif "_경고" in e:
                            resolved_bug_types.append(e.replace("_경고", ""))
                    resolved_bug_types = list(set(resolved_bug_types))

                    # 해당 벌레 제거 (가장 가까운 1마리만)
                    for bug_type in resolved_bug_types:
                        bugs_of_type = [b for b in game_state.active_bugs if b.bug_type == bug_type]
                        if bugs_of_type:
                            # 가장 가까운 벌레 제거
                            closest = min(bugs_of_type, key=lambda b: b.coordinates.distance_to(game_state.player.coordinates))
                            game_state.active_bugs.remove(closest)
                    # 이벤트 클리어 (조우 + 경고 모두)
                    game_state.active_events = [
                        e for e in game_state.active_events if "_조우" not in e and "_경고" not in e
                    ]

                # 모래폭풍 거리 조정 (빠른 이동 보너스)
                if update.get("sandstorm_bonus"):
                    game_state.sandstorm.distance += update["sandstorm_bonus"]
                    game_state.sandstorm.distance = max(0, game_state.sandstorm.distance)

                # 정보 발견
                if update.get("discovered_knowledge"):
                    from domain.world.model import KnowledgeItem
                    dk = update["discovered_knowledge"]
                    # dk가 dict인지 확인 (LLM이 문자열을 반환하는 경우 방지)
                    if isinstance(dk, dict):
                        dk_id = dk.get("id", f"knowledge_{game_state.turn_count}")
                        # 중복 체크
                        if not any(k.id == dk_id for k in game_state.knowledge):
                            game_state.knowledge.append(KnowledgeItem(
                                id=dk_id,
                                title=dk.get("title", "발견한 정보"),
                                content=dk.get("content", ""),
                                discovered_at=game_state.player.position,
                                turn_discovered=game_state.turn_count,
                            ))

                # 퀘스트 업데이트
                if update.get("quest_update"):
                    qu = update["quest_update"]
                    if isinstance(qu, dict):
                        for quest in game_state.quests:
                            if quest.quest_id == qu.get("quest_id"):
                                if qu.get("progress"):
                                    quest.progress = qu["progress"]
                                if qu.get("status"):
                                    quest.status = qu["status"]

            except json.JSONDecodeError:
                pass

        # 게임 종료 조건 체크
        if game_state.player.position == "지하_도시":
            game_state.reached_destination = True
            game_state.sandstorm.is_active = False  # 지하 도착하면 폭풍 비활성
            game_state.game_over = True

        if game_state.player.health <= 0:
            game_state.game_over = True

        if game_state.sandstorm.distance <= 0:
            game_state.game_over = True

        game_state.turn_count += 1
        state["game_state"] = game_state

        return state

    async def create_session(self) -> GameState:
        return await self._repository.create()

    async def get_session(self, session_id: str) -> GameState | None:
        return await self._repository.get(session_id)

    async def play(
        self, session_id: str, user_input: str
    ) -> tuple[GameState, str, list[str]]:
        game_state = await self._repository.get(session_id)
        if game_state is None:
            raise ValueError(f"Session not found: {session_id}")

        if game_state.game_over:
            if game_state.reached_destination:
                return game_state, "어둠 속에서 빛이 보인다. 지하 도시의 입구. 살았다.", []
            if game_state.sandstorm.distance <= 0:
                return game_state, "굉음. 시야가 사라진다. 모래가 폐를 채운다. 아무것도 보이지 않는다...", []
            if game_state.player.health <= 0:
                return game_state, "무릎이 꺾인다. 모래 위에 쓰러진다. 의식이 멀어진다...", []
            return game_state, "게임이 종료되었습니다.", []

        # 사용자 입력에서 이동 방향 추출 → 좌표 즉시 업데이트
        movement_dir = extract_movement_direction(user_input)
        if movement_dir and movement_dir in MOVEMENT_DELTA:
            lat_delta, lng_delta = MOVEMENT_DELTA[movement_dir]
            game_state.player.coordinates.lat += lat_delta
            game_state.player.coordinates.lng += lng_delta

        # 행동에 따른 폭풍 보너스 (코드 레벨에서 직접 처리)
        user_lower = user_input.lower()
        RUN_KEYWORDS = ["달린", "뛰", "전력", "질주", "빠르게", "서둘러", "급히"]
        WALK_KEYWORDS = ["걷", "걸어", "이동", "나아"]
        STOP_KEYWORDS = ["멈", "기다", "살펴", "관찰", "조사", "숨"]

        if any(kw in user_lower for kw in RUN_KEYWORDS):
            # 달리기: 폭풍과 거리 벌림 + 체력 소모
            game_state.sandstorm.distance += 60
            game_state.player.health = max(0, game_state.player.health - 5)
        elif any(kw in user_lower for kw in WALK_KEYWORDS):
            # 걷기: 약간 거리 벌림
            game_state.sandstorm.distance += 30
        elif any(kw in user_lower for kw in STOP_KEYWORDS):
            # 멈춤/관찰: 폭풍이 더 빨리 다가옴
            game_state.sandstorm.distance -= 20

        # 이전 대화 히스토리를 메시지로 변환
        history_messages = []
        for msg in game_state.message_history[-10:]:  # 최근 10개만 (토큰 제한)
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                # STATE_UPDATE, CHOICES 태그 제거한 내용만 전달
                import re
                clean_content = re.sub(
                    r"\[STATE_UPDATE\].*?\[/STATE_UPDATE\]", "", msg["content"], flags=re.DOTALL
                )
                clean_content = re.sub(
                    r"\[CHOICES\].*?\[/CHOICES\]", "", clean_content, flags=re.DOTALL
                ).strip()
                if clean_content:
                    history_messages.append(AIMessage(content=clean_content))

        # LangGraph 실행
        initial_state: AgentState = {
            "messages": [*history_messages, HumanMessage(content=user_input)],
            "game_state": game_state,
            "world_knowledge": self._knowledge,
            "gm_response": "",
            "encounter_info": [],
        }

        result = await self._graph.ainvoke(initial_state)

        # 상태 저장
        updated_state = result["game_state"]
        updated_state.message_history.append({"role": "user", "content": user_input})
        updated_state.message_history.append(
            {"role": "assistant", "content": result["gm_response"]}
        )
        await self._repository.update(updated_state)

        # 응답 파싱
        import re

        response = result["gm_response"]

        # 선택지 추출
        choices: list[str] = []
        choices_match = re.search(r"\[CHOICES\](.*?)\[/CHOICES\]", response, re.DOTALL)
        if choices_match:
            choices_text = choices_match.group(1).strip()
            for line in choices_text.split("\n"):
                line = line.strip()
                if line and line[0].isdigit():
                    # "1. 선택지" 형태에서 숫자와 점 제거
                    choice = re.sub(r"^\d+\.\s*", "", line)
                    if choice:
                        choices.append(choice)

        # 태그 제거한 응답 반환
        clean_response = re.sub(
            r"\[STATE_UPDATE\].*?\[/STATE_UPDATE\]", "", response, flags=re.DOTALL
        )
        clean_response = re.sub(
            r"\[CHOICES\].*?\[/CHOICES\]", "", clean_response, flags=re.DOTALL
        ).strip()

        return updated_state, clean_response, choices
