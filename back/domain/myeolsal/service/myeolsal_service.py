"""
멸살법 서비스

비즈니스 로직 레이어
"""
import json
from pathlib import Path
from typing import Any

from domain.myeolsal.models import BeastEntry, BeastLayer, MyeolsalRules
from domain.myeolsal.repository import ChromaBeastRepository, Neo4jMyeolsalRepository
from domain.myeolsal.agents import (
    BeastGeneratorAgent,
    BeastRetrieverAgent,
    BeastValidatorAgent,
    GenerationRequest,
)
from domain.myeolsal.graph import MyeolsalWorkflow


class MyeolsalService:
    """
    멸살법 서비스

    괴수 검색, 생성, 관리를 위한 통합 서비스
    """

    def __init__(
        self,
        chroma_repo: ChromaBeastRepository,
        neo4j_repo: Neo4jMyeolsalRepository,
        retriever: BeastRetrieverAgent,
        generator: BeastGeneratorAgent,
        validator: BeastValidatorAgent,
        workflow: MyeolsalWorkflow,
        rules: MyeolsalRules,
    ):
        self.chroma_repo = chroma_repo
        self.neo4j_repo = neo4j_repo
        self.retriever = retriever
        self.generator = generator
        self.validator = validator
        self.workflow = workflow
        self.rules = rules

    # ============================================
    # RAG 질의
    # ============================================

    async def query(self, question: str) -> dict:
        """
        자연어 질문 처리

        Args:
            question: 사용자 질문

        Returns:
            응답 결과
        """
        return await self.workflow.run(question)

    # ============================================
    # 괴수 검색
    # ============================================

    async def search_beasts(
        self,
        query: str,
        grade: str | None = None,
        species: str | None = None,
        scenario: str | None = None,
        limit: int = 10
    ) -> list[dict]:
        """
        괴수 검색

        Args:
            query: 검색 쿼리
            grade: 등급 필터
            species: 종 필터
            scenario: 시나리오 필터
            limit: 결과 수

        Returns:
            검색 결과
        """
        filters = {}
        if grade:
            filters["grade"] = grade
        if species:
            filters["species"] = species

        results = await self.retriever.search(
            query=query,
            n_results=limit * 2 if scenario else limit,  # 시나리오 필터 시 더 많이 가져옴
            filters=filters if filters else None
        )

        # 시나리오 필터링 (appearance_scenarios는 JSON 배열이라 $contains 사용 불가)
        if scenario:
            filtered = []
            for r in results:
                scenarios = r.get("metadata", {}).get("appearance_scenarios", [])
                if scenario in scenarios:
                    filtered.append(r)
                    if len(filtered) >= limit:
                        break
            return filtered

        return results[:limit]

    async def get_beast(self, beast_id: str) -> dict | None:
        """괴수 상세 조회"""
        result = self.chroma_repo.get_by_id(beast_id)
        if result:
            # Neo4j 관계 정보 추가
            relations = await self.neo4j_repo.get_related_beasts(beast_id)
            evolution = await self.neo4j_repo.get_evolution_tree(beast_id)
            scenarios = await self.neo4j_repo.get_scenarios_for_beast(beast_id)

            result["relations"] = relations
            result["evolution_tree"] = evolution
            result["scenarios"] = scenarios

        return result

    async def get_beasts_by_grade(self, grade: str) -> list[dict]:
        """등급별 괴수 목록"""
        return await self.retriever.search_by_grade(grade)

    async def get_beasts_by_species(self, species: str) -> list[dict]:
        """종별 괴수 목록"""
        return await self.retriever.search_by_species(species)

    # ============================================
    # 괴수 생성
    # ============================================

    async def generate_beast(
        self,
        concept: str,
        grade: str | None = None,
        species: str | None = None,
        save: bool = True
    ) -> dict:
        """
        새로운 괴수 생성

        Args:
            concept: 괴수 컨셉
            grade: 등급 지정
            species: 종 지정
            save: 저장 여부

        Returns:
            생성 결과
        """
        # 유사 괴수 검색
        similar = await self.retriever.search(concept, n_results=3)

        # 생성 요청
        request = GenerationRequest(
            concept=concept,
            grade=grade,
            species=species
        )

        # 생성
        beast = await self.generator.generate(request)

        # 검증
        validation = self.validator.validate(beast)

        if not validation.is_valid:
            # 스탯 자동 수정 시도
            beast = self.validator.fix_stats(beast)
            validation = self.validator.validate(beast)

        result = {
            "beast": beast.model_dump(),
            "validation": validation.model_dump(),
            "saved": False,
        }

        # 저장 (검증 통과 시)
        if save and validation.is_valid:
            await self._save_beast(beast)
            result["saved"] = True

        return result

    # ============================================
    # 괴수 저장/관리
    # ============================================

    async def _save_beast(self, beast: BeastEntry) -> str:
        """괴수 저장 (내부용)"""
        # ChromaDB 저장 (자동 임베딩)
        self.chroma_repo.add_beast(beast)

        # Neo4j 저장
        await self.neo4j_repo.create_beast_node(beast)

        # 진화 관계 저장
        for evo in beast.evolution_line:
            parts = evo.split(" → ")
            for i in range(len(parts) - 1):
                # 간단한 ID 추출 (실제로는 더 정교하게)
                from_id = self._extract_beast_id(parts[i])
                to_id = self._extract_beast_id(parts[i + 1])
                if from_id and to_id:
                    await self.neo4j_repo.create_evolution_relation(from_id, to_id)

        # 시나리오 연결
        for scenario_id in beast.appearance_scenarios:
            await self.neo4j_repo.link_to_scenario(beast.id, scenario_id)

        return beast.id

    def _extract_beast_id(self, text: str) -> str | None:
        """텍스트에서 괴수 ID 추출 (간단한 구현)"""
        # "어룡(7급)" → 기존 데이터에서 매칭 필요
        # 실제 구현에서는 이름으로 검색하여 ID 찾기
        return None

    async def add_beast(self, beast: BeastEntry) -> str:
        """외부에서 괴수 추가"""
        # 검증
        validation = self.validator.validate(beast)
        if not validation.is_valid:
            raise ValueError(f"검증 실패: {validation.errors}")

        return await self._save_beast(beast)

    async def delete_beast(self, beast_id: str) -> bool:
        """괴수 삭제"""
        # ChromaDB 삭제
        self.chroma_repo.delete(beast_id)

        # Neo4j 삭제
        await self.neo4j_repo.delete_beast_node(beast_id)

        return True

    # ============================================
    # 통계/정보
    # ============================================

    def get_stats(self) -> dict:
        """저장소 통계"""
        chroma_stats = self.chroma_repo.get_stats()
        return {
            "chroma": chroma_stats,
            "rules": {
                "grades": len(self.rules.grade_stat_ranges),
                "species": len(self.rules.species_traits),
                "elements": len(self.rules.elemental_affinities),
            }
        }

    def get_rules(self) -> dict:
        """규칙 조회"""
        return self.rules.model_dump()

    async def get_graph(self, limit: int = 100) -> dict:
        """괴수 관계 그래프 조회"""
        return await self.neo4j_repo.get_full_graph(limit)

    # ============================================
    # 초기화
    # ============================================

    async def initialize(self, auto_seed: bool = True) -> dict:
        """
        서비스 초기화 (DB 연결 확인, 인덱스 생성, 시드 데이터 로드)

        Args:
            auto_seed: ChromaDB가 비어있을 때 자동으로 시드 데이터 로드
        """
        # Neo4j 연결 확인
        neo4j_ok = await self.neo4j_repo.verify_connectivity()

        if neo4j_ok:
            await self.neo4j_repo.create_constraints()
            await self.neo4j_repo.create_indexes()

        chroma_count = self.chroma_repo.count()
        seed_result = None

        # ChromaDB가 비어있으면 시드 데이터 자동 로드
        if auto_seed and chroma_count == 0:
            data_dir = Path(__file__).parent.parent / "data"
            seed_result = await self.load_seed_data(data_dir)
            chroma_count = self.chroma_repo.count()

        return {
            "neo4j": neo4j_ok,
            "chroma_count": chroma_count,
            "seed_loaded": seed_result,
        }

    async def load_seed_data(self, data_dir: str | Path, force: bool = False) -> dict:
        """
        시드 데이터 로드

        Args:
            data_dir: 데이터 디렉토리 경로
            force: True면 기존 데이터 삭제 후 재로드

        Returns:
            로드 결과
        """
        data_dir = Path(data_dir)
        results = {"loaded": 0, "skipped": 0, "errors": []}

        # 강제 재로드 시 기존 데이터 삭제
        if force:
            self.chroma_repo.clear()
            results["cleared"] = True

        # 기존 ID 목록 조회 (중복 방지)
        existing_ids = set(self.chroma_repo.get_all_ids())

        # canon_beasts.json 로드
        beasts_file = data_dir / "canon_beasts.json"
        if beasts_file.exists():
            with open(beasts_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for beast_data in data.get("beasts", []):
                try:
                    beast = BeastEntry(**beast_data)

                    # 이미 존재하면 스킵
                    if beast.id in existing_ids:
                        results["skipped"] += 1
                        continue

                    # ChromaDB 저장 (자동 임베딩)
                    self.chroma_repo.add_beast(beast)

                    # Neo4j 저장
                    await self.neo4j_repo.create_beast_node(beast)

                    results["loaded"] += 1

                except Exception as e:
                    results["errors"].append({
                        "id": beast_data.get("id", "unknown"),
                        "error": str(e)
                    })

        return results
