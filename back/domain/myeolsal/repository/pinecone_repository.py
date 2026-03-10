"""
Pinecone 괴수 저장소

멸살법 항목의 벡터 검색 및 저장
OpenAI text-embedding-3-small (1536d) 임베딩 사용
"""
import json
from typing import Any
from urllib.parse import quote, unquote

from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings

from domain.myeolsal.models import BeastEntry


class PineconeBeastRepository:
    """
    Pinecone 괴수 저장소

    벡터 임베딩을 통한 시맨틱 검색 지원
    Pinecone Serverless + OpenAI text-embedding-3-small 사용
    """

    def __init__(
        self,
        api_key: str,
        index_name: str,
        openai_api_key: str,
    ):
        """
        Args:
            api_key: Pinecone API 키
            index_name: Pinecone 인덱스 이름
            openai_api_key: OpenAI API 키 (임베딩용)
        """
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.index = self.pc.Index(index_name)
        self._embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_api_key,
        )

    def _embed(self, text: str) -> list[float]:
        """텍스트를 벡터로 변환"""
        return self._embeddings.embed_query(text)

    @staticmethod
    def _to_pinecone_id(beast_id: str) -> str:
        """Pinecone은 ASCII ID만 허용하므로 한글 등 non-ASCII를 URL-encode"""
        if beast_id.isascii():
            return beast_id
        return quote(beast_id, safe="")

    @staticmethod
    def _from_pinecone_id(pinecone_id: str) -> str:
        """Pinecone ID → 원본 ID 복원"""
        return unquote(pinecone_id)

    @staticmethod
    def _beast_to_metadata(beast: BeastEntry, document: str) -> dict:
        """BeastEntry → Pinecone 메타데이터 변환"""
        return {
            "document": document,
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

    @staticmethod
    def _parse_json_fields(metadata: dict) -> dict:
        """메타데이터의 JSON 문자열 필드를 파싱"""
        for field in ["tags", "weaknesses", "resistances", "appearance_scenarios"]:
            if field in metadata:
                try:
                    metadata[field] = json.loads(metadata[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return metadata

    def add_beast(self, beast: BeastEntry) -> str:
        """
        괴수 항목 추가

        Args:
            beast: 괴수 데이터

        Returns:
            추가된 괴수 ID
        """
        document = beast.get_searchable_text()
        vector = self._embed(document)
        metadata = self._beast_to_metadata(beast, document)
        metadata["original_id"] = beast.id

        pinecone_id = self._to_pinecone_id(beast.id)
        self.index.upsert(vectors=[(pinecone_id, vector, metadata)])
        return beast.id

    def add_beast_chunks(self, beast: BeastEntry) -> list[str]:
        """
        괴수 항목을 청크별로 추가 (더 정밀한 검색용)

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

        vectors = []
        chunk_ids = []

        # 설명 청크
        chunk_id = f"{beast.id}_desc"
        doc = f"{beast.title} {beast.grade} {beast.species}: {beast.description} {beast.lore_notes}"
        vectors.append((self._to_pinecone_id(chunk_id), self._embed(doc), {**base_metadata, "chunk_type": "description", "document": doc}))
        chunk_ids.append(chunk_id)

        # 전투 패턴 청크
        if beast.combat_patterns:
            chunk_id = f"{beast.id}_combat"
            doc = beast.get_combat_text()
            vectors.append((self._to_pinecone_id(chunk_id), self._embed(doc), {**base_metadata, "chunk_type": "combat", "document": doc}))
            chunk_ids.append(chunk_id)

        # 생존 가이드 청크
        if beast.survival_guide:
            chunk_id = f"{beast.id}_survival"
            doc = beast.get_survival_text()
            vectors.append((self._to_pinecone_id(chunk_id), self._embed(doc), {**base_metadata, "chunk_type": "survival", "document": doc}))
            chunk_ids.append(chunk_id)

        if vectors:
            self.index.upsert(vectors=vectors)

        return chunk_ids

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        """
        시맨틱 검색

        Args:
            query: 검색 쿼리 텍스트
            n_results: 반환할 결과 수
            filters: 메타데이터 필터 (예: {"grade": "7급"})

        Returns:
            검색 결과 리스트
        """
        vector = self._embed(query)

        # Pinecone 필터 변환
        pinecone_filter = None
        if filters:
            if len(filters) == 1:
                key, value = list(filters.items())[0]
                pinecone_filter = {key: {"$eq": value}}
            else:
                pinecone_filter = {
                    "$and": [{k: {"$eq": v}} for k, v in filters.items()]
                }

        results = self.index.query(
            vector=vector,
            top_k=n_results,
            filter=pinecone_filter,
            include_metadata=True,
        )

        formatted_results = []
        for match in results.matches:
            metadata = dict(match.metadata) if match.metadata else {}
            document = metadata.pop("document", None)
            metadata = self._parse_json_fields(metadata)

            original_id = metadata.pop("original_id", None) or self._from_pinecone_id(match.id)
            formatted_results.append({
                "id": original_id,
                "document": document,
                "metadata": metadata,
                "distance": 1.0 - (match.score or 0),
            })

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
            pinecone_id = self._to_pinecone_id(beast_id)
            result = self.index.fetch(ids=[pinecone_id])

            if pinecone_id not in result.vectors:
                return None

            vector_data = result.vectors[pinecone_id]
            metadata = dict(vector_data.metadata) if vector_data.metadata else {}
            document = metadata.pop("document", None)
            metadata.pop("original_id", None)
            metadata = self._parse_json_fields(metadata)

            return {
                "id": beast_id,
                "document": document,
                "metadata": metadata,
            }
        except Exception:
            return None

    def _get_raw_pinecone_ids(self) -> list[str]:
        """Pinecone에 저장된 원본(인코딩된) ID 목록"""
        raw_ids = []
        for page in self.index.list():
            raw_ids.extend(page)
        return raw_ids

    def get_all_ids(self) -> list[str]:
        """모든 괴수 ID 조회 (원본 ID로 반환)"""
        return [self._from_pinecone_id(pid) for pid in self._get_raw_pinecone_ids()]

    # === 전체 목록 조회 (캐시 기반) ===

    _all_beasts_cache: list[dict] | None = None

    def _fetch_all_beasts(self) -> list[dict]:
        """모든 괴수 메타데이터를 가져와 캐시"""
        raw_ids = self._get_raw_pinecone_ids()
        all_beasts = []

        for i in range(0, len(raw_ids), 100):
            batch = raw_ids[i : i + 100]
            result = self.index.fetch(ids=batch)
            for pid in batch:
                if pid not in result.vectors:
                    continue
                vec_data = result.vectors[pid]
                metadata = dict(vec_data.metadata) if vec_data.metadata else {}
                document = metadata.pop("document", None)
                original_id = metadata.pop("original_id", None) or self._from_pinecone_id(pid)
                metadata = self._parse_json_fields(metadata)
                all_beasts.append({
                    "id": original_id,
                    "document": document,
                    "metadata": metadata,
                })

        return all_beasts

    def invalidate_cache(self) -> None:
        """캐시 무효화 (괴수 추가/삭제 시 호출)"""
        self._all_beasts_cache = None

    def warm_cache(self) -> None:
        """캐시 워밍 (서버 시작 시 호출)"""
        if self._all_beasts_cache is None:
            self._all_beasts_cache = self._fetch_all_beasts()

    def list_beasts(
        self,
        offset: int = 0,
        limit: int = 50,
        grade: str | None = None,
        species: str | None = None,
    ) -> tuple[list[dict], int]:
        """
        전체 괴수 목록 조회 (페이지네이션 + 필터)

        Returns:
            (결과 리스트, 필터 적용 후 총 개수)
        """
        if self._all_beasts_cache is None:
            self._all_beasts_cache = self._fetch_all_beasts()

        filtered = self._all_beasts_cache
        if grade:
            filtered = [b for b in filtered if b["metadata"].get("grade") == grade]
        if species:
            filtered = [b for b in filtered if b["metadata"].get("species") == species]

        total = len(filtered)
        page = filtered[offset : offset + limit]
        return page, total

    def delete(self, beast_id: str) -> bool:
        """
        괴수 삭제

        Args:
            beast_id: 삭제할 괴수 ID

        Returns:
            삭제 성공 여부
        """
        try:
            self.index.delete(ids=[self._to_pinecone_id(beast_id)])
            return True
        except Exception:
            return False

    def count(self) -> int:
        """저장된 괴수 수 조회"""
        stats = self.index.describe_index_stats()
        return stats.total_vector_count

    def clear(self) -> None:
        """모든 데이터 삭제 (주의: 개발용)"""
        self.index.delete(delete_all=True)

    def get_stats(self) -> dict:
        """저장소 통계 조회 (캐시 활용)"""
        if self._all_beasts_cache is None:
            self._all_beasts_cache = self._fetch_all_beasts()

        beasts = self._all_beasts_cache
        grade_dist: dict[str, int] = {}
        species_dist: dict[str, int] = {}
        scenario_dist: dict[str, int] = {}

        for b in beasts:
            meta = b.get("metadata", {})
            grade = meta.get("grade", "unknown")
            species = meta.get("species", "unknown")
            grade_dist[grade] = grade_dist.get(grade, 0) + 1
            species_dist[species] = species_dist.get(species, 0) + 1

            scenarios = meta.get("appearance_scenarios", [])
            if isinstance(scenarios, list):
                for scenario in scenarios:
                    scenario_dist[scenario] = scenario_dist.get(scenario, 0) + 1

        return {
            "total_count": len(beasts),
            "grade_distribution": grade_dist,
            "species_distribution": species_dist,
            "scenario_distribution": scenario_dist,
        }

    @classmethod
    def create_index_if_not_exists(
        cls,
        api_key: str,
        index_name: str,
        dimension: int = 1536,
    ) -> None:
        """Pinecone 인덱스가 없으면 생성 (Serverless)"""
        pc = Pinecone(api_key=api_key)
        existing = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing:
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
