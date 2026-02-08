"""
ChromaDB 괴수 저장소

멸살법 항목의 벡터 검색 및 저장
"""
import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from domain.myeolsal.models import BeastEntry


class ChromaBeastRepository:
    """
    ChromaDB 괴수 저장소

    벡터 임베딩을 통한 시맨틱 검색 지원
    ChromaDB 기본 임베딩 함수 사용 (sentence-transformers, 로컬 실행)
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma_myeolsal",
        collection_name: str = "myeolsal_beasts"
    ):
        """
        Args:
            persist_directory: ChromaDB 데이터 저장 경로
            collection_name: 컬렉션 이름
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 기본 임베딩 함수 (sentence-transformers, API 키 불필요)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # 컬렉션 생성 또는 가져오기
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embedding_function
        )

    def add_beast(self, beast: BeastEntry) -> str:
        """
        괴수 항목 추가 (자동 임베딩)

        Args:
            beast: 괴수 데이터

        Returns:
            추가된 괴수 ID
        """
        # 메타데이터 준비 (ChromaDB는 기본 타입만 지원)
        metadata = {
            "layer": beast.layer.value,
            "confidence": beast.confidence,
            "source": beast.source,
            "volume": beast.volume,
            "grade": beast.grade,
            "species": beast.species,
            "danger_class": beast.danger_class,
            "title": beast.title,
            "tags": json.dumps(beast.tags, ensure_ascii=False),
            "weaknesses": json.dumps(beast.weaknesses, ensure_ascii=False),
            "resistances": json.dumps(beast.resistances, ensure_ascii=False),
            "appearance_scenarios": json.dumps(beast.appearance_scenarios, ensure_ascii=False),
        }

        # 검색용 텍스트
        document = beast.get_searchable_text()

        # ChromaDB가 자동으로 임베딩 생성
        self.collection.add(
            ids=[beast.id],
            documents=[document],
            metadatas=[metadata]
        )

        return beast.id

    def add_beast_chunks(self, beast: BeastEntry) -> list[str]:
        """
        괴수 항목을 청크별로 추가 (더 정밀한 검색용, 자동 임베딩)

        Args:
            beast: 괴수 데이터

        Returns:
            추가된 청크 ID 리스트
        """
        base_metadata = {
            "beast_id": beast.id,
            "layer": beast.layer.value,
            "confidence": beast.confidence,
            "grade": beast.grade,
            "species": beast.species,
            "danger_class": beast.danger_class,
            "title": beast.title,
            "tags": json.dumps(beast.tags, ensure_ascii=False),
        }

        chunk_ids = []
        ids = []
        docs = []
        metas = []

        # 설명 청크
        chunk_id = f"{beast.id}_desc"
        ids.append(chunk_id)
        docs.append(f"{beast.title} {beast.grade} {beast.species}: {beast.description} {beast.lore_notes}")
        metas.append({**base_metadata, "chunk_type": "description"})
        chunk_ids.append(chunk_id)

        # 전투 패턴 청크
        if beast.combat_patterns:
            chunk_id = f"{beast.id}_combat"
            ids.append(chunk_id)
            docs.append(beast.get_combat_text())
            metas.append({**base_metadata, "chunk_type": "combat"})
            chunk_ids.append(chunk_id)

        # 생존 가이드 청크
        if beast.survival_guide:
            chunk_id = f"{beast.id}_survival"
            ids.append(chunk_id)
            docs.append(beast.get_survival_text())
            metas.append({**base_metadata, "chunk_type": "survival"})
            chunk_ids.append(chunk_id)

        if ids:
            # ChromaDB가 자동으로 임베딩 생성
            self.collection.add(
                ids=ids,
                documents=docs,
                metadatas=metas
            )

        return chunk_ids

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[dict]:
        """
        시맨틱 검색 (자동 임베딩)

        Args:
            query: 검색 쿼리 텍스트
            n_results: 반환할 결과 수
            filters: 메타데이터 필터 (예: {"grade": "7급"})

        Returns:
            검색 결과 리스트
        """
        where_filter = None
        if filters:
            # ChromaDB where 절 형식으로 변환
            if len(filters) == 1:
                key, value = list(filters.items())[0]
                where_filter = {key: value}
            else:
                where_filter = {"$and": [{k: v} for k, v in filters.items()]}

        # ChromaDB가 자동으로 쿼리 임베딩 생성
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # 결과 정리
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i, id_ in enumerate(results["ids"][0]):
                result = {
                    "id": id_,
                    "document": results["documents"][0][i] if results["documents"] else None,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else None,
                    "distance": results["distances"][0][i] if results["distances"] else None,
                }
                # JSON 필드 파싱
                if result["metadata"]:
                    for field in ["tags", "weaknesses", "resistances", "appearance_scenarios"]:
                        if field in result["metadata"]:
                            try:
                                result["metadata"][field] = json.loads(result["metadata"][field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                formatted_results.append(result)

        return formatted_results

    def get_by_id(self, beast_id: str) -> dict | None:
        """
        ID로 괴수 조회

        Args:
            beast_id: 괴수 ID

        Returns:
            괴수 데이터 또는 None
        """
        try:
            results = self.collection.get(
                ids=[beast_id],
                include=["documents", "metadatas"]
            )

            if not results["ids"]:
                return None

            result = {
                "id": results["ids"][0],
                "document": results["documents"][0] if results["documents"] else None,
                "metadata": results["metadatas"][0] if results["metadatas"] else None,
            }

            # JSON 필드 파싱
            if result["metadata"]:
                for field in ["tags", "weaknesses", "resistances", "appearance_scenarios"]:
                    if field in result["metadata"]:
                        try:
                            result["metadata"][field] = json.loads(result["metadata"][field])
                        except (json.JSONDecodeError, TypeError):
                            pass

            return result
        except Exception:
            return None

    def get_all_ids(self) -> list[str]:
        """모든 괴수 ID 조회"""
        results = self.collection.get()
        return results["ids"] if results["ids"] else []

    def delete(self, beast_id: str) -> bool:
        """
        괴수 삭제

        Args:
            beast_id: 삭제할 괴수 ID

        Returns:
            삭제 성공 여부
        """
        try:
            self.collection.delete(ids=[beast_id])
            return True
        except Exception:
            return False

    def count(self) -> int:
        """저장된 괴수 수 조회"""
        return self.collection.count()

    def clear(self) -> None:
        """모든 데이터 삭제 (주의: 개발용)"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def get_stats(self) -> dict:
        """저장소 통계 조회"""
        count = self.collection.count()

        # 등급별, 종별, 시나리오별 분포
        grade_dist = {}
        species_dist = {}
        scenario_dist = {}

        if count > 0:
            all_data = self.collection.get(include=["metadatas"])
            for meta in all_data["metadatas"]:
                grade = meta.get("grade", "unknown")
                species = meta.get("species", "unknown")
                grade_dist[grade] = grade_dist.get(grade, 0) + 1
                species_dist[species] = species_dist.get(species, 0) + 1

                # 시나리오 분포
                scenarios_raw = meta.get("appearance_scenarios", "[]")
                try:
                    scenarios = json.loads(scenarios_raw) if isinstance(scenarios_raw, str) else scenarios_raw
                    for scenario in scenarios:
                        scenario_dist[scenario] = scenario_dist.get(scenario, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    pass

        return {
            "total_count": count,
            "grade_distribution": grade_dist,
            "species_distribution": species_dist,
            "scenario_distribution": scenario_dist,
        }
