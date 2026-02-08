"""
GraphRAG Retriever

Neo4j 지식 그래프에서 시나리오 정보를 검색하여
EnrichedScenarioContext를 생성합니다.
"""
import logging
from domain.orv_v2.repository.neo4j_repository import Neo4jGraphRepository
from domain.orv_v2.models.scenario import (
    EnrichedScenarioContext,
    CharacterInfo,
    RuleInfo,
    TrickInfo,
    AlternativeSolution,
    LocationInfo,
)

logger = logging.getLogger(__name__)


class GraphRAGRetriever:
    """
    GraphRAG 검색기

    Neo4j 지식 그래프에서 시나리오 관련 정보를 검색하여
    AutoNarrator가 사용할 수 있는 풍부한 컨텍스트를 생성합니다.
    """

    def __init__(self, neo4j_repo: Neo4jGraphRepository):
        """
        Args:
            neo4j_repo: Neo4j 저장소
        """
        self.repo = neo4j_repo

    async def retrieve_scenario_knowledge(
        self,
        scenario_id: str,
        remaining_time: int | None = None,
        current_phase: str | None = None,
    ) -> EnrichedScenarioContext:
        """
        시나리오 지식 검색 (전체 컨텍스트)

        Args:
            scenario_id: 시나리오 ID
            remaining_time: 남은 턴 수
            current_phase: 현재 단계

        Returns:
            강화된 시나리오 컨텍스트
        """
        import asyncio
        logger.info(f"🔍 [GraphRAG] 시나리오 지식 검색 시작: scenario_id={scenario_id}, phase={current_phase}, remaining_time={remaining_time}")

        # 1. 모든 Neo4j 쿼리를 병렬 실행 (성능 최적화)
        full_context, protagonist_tricks_data, alternatives_data = await asyncio.gather(
            self.repo.get_scenario_full_context(scenario_id),
            self.repo.get_protagonist_tricks(scenario_id),
            self.repo.get_alternative_solutions(scenario_id),
        )

        if not full_context:
            # Neo4j에 데이터가 없으면 기본 컨텍스트 반환
            logger.warning(f"⚠️  [GraphRAG] Neo4j에 데이터가 없습니다: scenario_id={scenario_id}")
            return self._create_empty_context(scenario_id)

        scenario = full_context.get("s", {})
        logger.info(f"✅ [GraphRAG] Neo4j 데이터 조회 완료 (병렬): scenario_title={scenario.get('title', 'Unknown')}")

        # 2. 캐릭터 정보 파싱
        characters_data = full_context.get("characters", [])
        logger.debug(f"   - 캐릭터 데이터: {len(characters_data)}개")
        key_characters = []
        for char_data in characters_data:
            char = char_data.get("character")
            if char:
                key_characters.append(
                    CharacterInfo(
                        character_id=char.get("character_id", ""),
                        name=char.get("name", ""),
                        character_type=char.get("character_type", ""),
                        description=char.get("description", ""),
                        role=char_data.get("role", ""),
                        personality_traits=char.get("personality_traits", []),
                        appearance=char.get("appearance"),
                    )
                )

        # 3. 위치 정보 파싱
        locations_data = full_context.get("locations", [])
        locations = []
        for loc in locations_data:
            if loc:
                locations.append(
                    LocationInfo(
                        location_id=loc.get("location_id", ""),
                        name=loc.get("name", ""),
                        description=loc.get("description", ""),
                        atmosphere=loc.get("atmosphere", ""),
                        danger_level=loc.get("danger_level", 0),
                    )
                )

        # 4. 규칙 정보 파싱
        rules_data = full_context.get("rules", [])
        win_conditions = []
        fail_conditions = []

        for rule in rules_data:
            if rule:
                rule_info = RuleInfo(
                    rule_id=rule.get("rule_id", ""),
                    rule_type=rule.get("rule_type", ""),
                    description=rule.get("description", ""),
                    is_hidden=rule.get("is_hidden", False),
                    importance=rule.get("importance", 0),
                )

                if rule.get("rule_type") == "win_condition":
                    win_conditions.append(rule_info)
                elif rule.get("rule_type") == "fail_condition":
                    fail_conditions.append(rule_info)

        # 5. 주인공 전용 트릭 (병렬 조회 결과 사용)
        logger.debug(f"   - 주인공 트릭: {len(protagonist_tricks_data)}개")
        protagonist_tricks = []
        for trick_data in protagonist_tricks_data:
            protagonist_tricks.append(
                TrickInfo(
                    trick_id=trick_data.get("trick_id", ""),
                    name=trick_data.get("name", ""),
                    description=trick_data.get("description", ""),
                    difficulty_to_discover=trick_data.get("difficulty", 0),
                    is_protagonist_knowledge=True,
                    narrative_hint=trick_data.get("narrative_hint", ""),
                )
            )

        # 6. 대안 솔루션 (병렬 조회 결과 사용)
        logger.debug(f"   - 대안 솔루션: {len(alternatives_data)}개")
        alternative_solutions = []
        for alt_data in alternatives_data:
            trick_info = TrickInfo(
                trick_id="",  # ID는 대안 솔루션 쿼리에서 반환되지 않음
                name=alt_data.get("name", ""),
                description=alt_data.get("description", ""),
                difficulty_to_discover=alt_data.get("difficulty", 0),
                is_protagonist_knowledge=False,  # 대안 솔루션은 일반 정보
                narrative_hint="",
            )
            alternative_solutions.append(
                AlternativeSolution(
                    trick=trick_info,
                    difficulty=alt_data.get("difficulty", 0),
                    morality_score=alt_data.get("morality_score", 0),
                )
            )

        # 7. 서술 힌트 추출 (주인공 트릭에서)
        narrative_hints = [
            trick.narrative_hint
            for trick in protagonist_tricks
            if trick.narrative_hint
        ]

        # 8. EnrichedScenarioContext 생성
        enriched_context = EnrichedScenarioContext(
            scenario_id=scenario.get("scenario_id", scenario_id),
            title=scenario.get("title", "Unknown Scenario"),
            objective=scenario.get("objective", ""),
            difficulty=scenario.get("difficulty", ""),
            remaining_time=remaining_time,
            current_phase=current_phase,
            detailed_description=scenario.get("description", ""),
            key_characters=key_characters,
            locations=locations,
            win_conditions=win_conditions,
            fail_conditions=fail_conditions,
            protagonist_tricks=protagonist_tricks,
            alternative_solutions=alternative_solutions,
            narrative_hints=narrative_hints,
        )

        logger.info(f"🎯 [GraphRAG] 시나리오 컨텍스트 생성 완료:")
        logger.info(f"   - 캐릭터: {len(key_characters)}개, 위치: {len(locations)}개")
        logger.info(f"   - 승리조건: {len(win_conditions)}개, 실패조건: {len(fail_conditions)}개")
        logger.info(f"   - 주인공 트릭: {len(protagonist_tricks)}개, 대안 솔루션: {len(alternative_solutions)}개")
        logger.info(f"   - 서술 힌트: {len(narrative_hints)}개")

        return enriched_context

    def _create_empty_context(self, scenario_id: str) -> EnrichedScenarioContext:
        """
        빈 컨텍스트 생성 (Neo4j에 데이터가 없을 때)

        Args:
            scenario_id: 시나리오 ID

        Returns:
            기본 EnrichedScenarioContext
        """
        return EnrichedScenarioContext(
            scenario_id=scenario_id,
            title="Unknown Scenario",
            objective="No objective defined",
            difficulty="Unknown",
            remaining_time=None,
            detailed_description="No description available",
        )

    async def get_character_details(self, character_id: str) -> CharacterInfo | None:
        """
        특정 캐릭터의 상세 정보 조회

        Args:
            character_id: 캐릭터 ID

        Returns:
            캐릭터 정보 또는 None
        """
        logger.info(f"🔍 [GraphRAG] 캐릭터 상세 조회: character_id={character_id}")
        query = """
        MATCH (c:Character {character_id: $character_id})
        RETURN c
        """
        records = await self.repo.execute_query(query, {"character_id": character_id})

        if not records:
            logger.warning(f"⚠️  [GraphRAG] 캐릭터를 찾을 수 없습니다: character_id={character_id}")
            return None

        char = records[0]["c"]
        logger.info(f"✅ [GraphRAG] 캐릭터 조회 완료: {char.get('name', 'Unknown')}")
        return CharacterInfo(
            character_id=char.get("character_id", ""),
            name=char.get("name", ""),
            character_type=char.get("character_type", ""),
            description=char.get("description", ""),
            role=char.get("role", ""),
            personality_traits=char.get("personality_traits", []),
            appearance=char.get("appearance"),
        )

    async def get_location_details(self, location_id: str) -> LocationInfo | None:
        """
        특정 위치의 상세 정보 조회

        Args:
            location_id: 위치 ID

        Returns:
            위치 정보 또는 None
        """
        logger.info(f"🔍 [GraphRAG] 위치 상세 조회: location_id={location_id}")
        query = """
        MATCH (l:Location {location_id: $location_id})
        RETURN l
        """
        records = await self.repo.execute_query(query, {"location_id": location_id})

        if not records:
            logger.warning(f"⚠️  [GraphRAG] 위치를 찾을 수 없습니다: location_id={location_id}")
            return None

        loc = records[0]["l"]
        logger.info(f"✅ [GraphRAG] 위치 조회 완료: {loc.get('name', 'Unknown')}")
        return LocationInfo(
            location_id=loc.get("location_id", ""),
            name=loc.get("name", ""),
            description=loc.get("description", ""),
            atmosphere=loc.get("atmosphere", ""),
            danger_level=loc.get("danger_level", 0),
        )
