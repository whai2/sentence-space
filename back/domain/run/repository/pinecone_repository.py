"""
Pinecone 런 세계관 저장소

엔티티의 벡터 검색 및 저장
OpenAI text-embedding-3-small (1536d) 임베딩 사용
"""
import json
from typing import Any
from urllib.parse import quote, unquote

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

from domain.run.models.entities import EntityType, RunEntity


class PineconeRunRepository:
    """
    런 세계관 Pinecone 저장소

    Concept, Character, Event, WorldSetting 엔티티의
    벡터 임베딩 기반 시맨틱 검색 지원
    """

    def __init__(
        self,
        api_key: str,
        index_name: str,
        openai_api_key: str,
    ):
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name

        # 인덱스 없으면 생성
        self._ensure_index(api_key, index_name)
        self.index = self.pc.Index(index_name)

        self._embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_api_key,
        )

        # 캐시
        self._all_entities_cache: list[dict] | None = None

    def _ensure_index(self, api_key: str, index_name: str) -> None:
        """인덱스가 없으면 생성"""
        existing = [idx.name for idx in self.pc.list_indexes()]
        if index_name not in existing:
            self.pc.create_index(
                name=index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

    def _embed(self, text: str) -> list[float]:
        """텍스트를 벡터로 변환"""
        return self._embeddings.embed_query(text)

    @staticmethod
    def _to_pinecone_id(entity_id: str) -> str:
        if entity_id.isascii():
            return entity_id
        return quote(entity_id, safe="")

    @staticmethod
    def _from_pinecone_id(pinecone_id: str) -> str:
        return unquote(pinecone_id)

    @staticmethod
    def _entity_to_metadata(entity: RunEntity, document: str) -> dict:
        """RunEntity → Pinecone 메타데이터"""
        return {
            "document": document,
            "entity_type": entity.entity_type.value,
            "title": entity.title,
            "tags": json.dumps(entity.tags, ensure_ascii=False),
            "original_id": entity.id,
            "source_url": entity.source_url,
        }

    @staticmethod
    def _parse_json_fields(metadata: dict) -> dict:
        for field in ["tags"]:
            if field in metadata:
                try:
                    metadata[field] = json.loads(metadata[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return metadata

    def add_entity(self, entity: RunEntity, extra_metadata: dict | None = None) -> str:
        """
        엔티티 추가 (벡터 임베딩 자동 생성)

        Returns:
            추가된 엔티티 ID
        """
        document = entity.get_searchable_text()
        vector = self._embed(document)
        metadata = self._entity_to_metadata(entity, document)

        if extra_metadata:
            metadata.update(extra_metadata)

        pinecone_id = self._to_pinecone_id(entity.id)
        self.index.upsert(vectors=[(pinecone_id, vector, metadata)])
        self._invalidate_cache()
        return entity.id

    def add_entity_chunks(self, entity: RunEntity, chunks: list[tuple[str, str]]) -> list[str]:
        """
        엔티티를 여러 청크로 추가

        Args:
            entity: 엔티티
            chunks: [(chunk_suffix, chunk_text), ...] 예: [("bio", "..."), ("timeline", "...")]

        Returns:
            추가된 청크 ID 리스트
        """
        base_metadata = {
            "entity_id": entity.id,
            "entity_type": entity.entity_type.value,
            "title": entity.title,
            "tags": json.dumps(entity.tags, ensure_ascii=False),
        }

        vectors = []
        chunk_ids = []

        for suffix, text in chunks:
            chunk_id = f"{entity.id}_{suffix}"
            metadata = {**base_metadata, "chunk_type": suffix, "document": text, "original_id": chunk_id}
            vectors.append((self._to_pinecone_id(chunk_id), self._embed(text), metadata))
            chunk_ids.append(chunk_id)

        if vectors:
            self.index.upsert(vectors=vectors)
            self._invalidate_cache()

        return chunk_ids

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        """시맨틱 검색"""
        vector = self._embed(query)

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

        formatted = []
        for match in results.matches:
            metadata = dict(match.metadata) if match.metadata else {}
            document = metadata.pop("document", None)
            metadata = self._parse_json_fields(metadata)
            original_id = metadata.pop("original_id", None) or self._from_pinecone_id(match.id)

            formatted.append({
                "id": original_id,
                "document": document,
                "metadata": metadata,
                "score": match.score or 0,
            })

        return formatted

    def get_by_id(self, entity_id: str) -> dict | None:
        """ID로 엔티티 조회"""
        try:
            pinecone_id = self._to_pinecone_id(entity_id)
            result = self.index.fetch(ids=[pinecone_id])

            if pinecone_id not in result.vectors:
                return None

            vector_data = result.vectors[pinecone_id]
            metadata = dict(vector_data.metadata) if vector_data.metadata else {}
            document = metadata.pop("document", None)
            metadata.pop("original_id", None)
            metadata = self._parse_json_fields(metadata)

            return {
                "id": entity_id,
                "document": document,
                "metadata": metadata,
            }
        except Exception:
            return None

    def delete(self, entity_id: str) -> bool:
        """엔티티 삭제"""
        try:
            pinecone_id = self._to_pinecone_id(entity_id)
            self.index.delete(ids=[pinecone_id])
            self._invalidate_cache()
            return True
        except Exception:
            return False

    def count(self) -> int:
        """총 벡터 수"""
        try:
            stats = self.index.describe_index_stats()
            return stats.total_vector_count
        except Exception:
            return 0

    def get_stats(self) -> dict:
        """저장소 통계"""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_count": stats.total_vector_count,
                "index_name": self.index_name,
            }
        except Exception:
            return {"total_count": 0, "index_name": self.index_name}

    def clear(self) -> None:
        """전체 삭제 (개발용)"""
        self.index.delete(delete_all=True)
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        self._all_entities_cache = None
