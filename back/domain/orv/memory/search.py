"""
키워드 기반 기억 검색

API 비용 없이 관련 기억을 효율적으로 검색합니다.
TF-IDF 스타일의 키워드 매칭 + 가중치 조합.
"""

import math
from collections import Counter
from datetime import datetime

from domain.orv.model.memory import MemoryEntry


class KeywordMemorySearch:
    """
    키워드 기반 기억 검색 엔진.

    점수 계산 요소:
    1. 키워드 매칭 (TF-IDF 스타일)
    2. 최신성 가중치 (최근 기억일수록 높은 점수)
    3. 중요도 가중치
    4. 감정 강도 가중치
    5. 엔티티 매칭 (플레이어, 특정 NPC 언급 시)
    """

    def __init__(
        self,
        recency_weight: float = 0.3,
        importance_weight: float = 0.25,
        keyword_weight: float = 0.3,
        emotion_weight: float = 0.15,
    ):
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.keyword_weight = keyword_weight
        self.emotion_weight = emotion_weight

    def search(
        self,
        query: str,
        memories: list[MemoryEntry],
        current_turn: int,
        limit: int = 5,
        entity_filter: str | None = None,
        event_type_filter: str | None = None,
    ) -> list[MemoryEntry]:
        """
        관련 기억 검색.

        Args:
            query: 검색 쿼리 (플레이어 행동, 상황 설명 등)
            memories: 검색 대상 기억 목록
            current_turn: 현재 턴 번호 (최신성 계산용)
            limit: 반환할 최대 기억 수
            entity_filter: 특정 엔티티 관련 기억만 필터링 (NPC ID 또는 "player")
            event_type_filter: 특정 이벤트 타입만 필터링

        Returns:
            관련도 순으로 정렬된 기억 목록
        """
        if not memories:
            return []

        # 필터링
        filtered = memories
        if entity_filter:
            if entity_filter == "player":
                filtered = [m for m in filtered if m.involves_player]
            else:
                filtered = [m for m in filtered if entity_filter in m.involves_npcs]

        if event_type_filter:
            filtered = [m for m in filtered if m.event_type == event_type_filter]

        if not filtered:
            return []

        # 쿼리 키워드 추출
        query_keywords = self._tokenize(query)
        if not query_keywords:
            # 키워드 없으면 최신 + 중요 기억 반환
            return self._fallback_search(filtered, current_turn, limit)

        # IDF 계산 (전체 기억에서)
        idf = self._calculate_idf(filtered)

        # 각 기억에 점수 부여
        scored = []
        for memory in filtered:
            score = self._calculate_score(
                memory=memory,
                query_keywords=query_keywords,
                idf=idf,
                current_turn=current_turn,
                max_turn=max(m.turn_occurred for m in filtered),
            )
            scored.append((memory, score))

        # 점수 순 정렬
        scored.sort(key=lambda x: x[1], reverse=True)

        # 상위 N개 반환 및 접근 기록
        results = []
        for memory, _ in scored[:limit]:
            memory.touch()
            results.append(memory)

        return results

    def _tokenize(self, text: str) -> list[str]:
        """텍스트를 토큰화"""
        # 불용어
        stopwords = {
            "이", "가", "은", "는", "을", "를", "의", "에", "에서", "로", "으로",
            "와", "과", "도", "만", "처럼", "같이", "보다", "부터", "까지",
            "하다", "되다", "있다", "없다", "이다", "아니다",
            "그", "저", "이것", "저것", "그것", "여기", "저기", "거기",
            "나", "너", "우리", "당신", "그녀", "그들", "것", "수", "때",
        }

        # 특수문자 제거 및 분리
        text = text.lower()
        for char in ".,!?;:\"'()[]{}":
            text = text.replace(char, " ")

        tokens = []
        for word in text.split():
            word = word.strip()
            if len(word) >= 2 and word not in stopwords:
                tokens.append(word)

        return tokens

    def _calculate_idf(self, memories: list[MemoryEntry]) -> dict[str, float]:
        """역문서 빈도(IDF) 계산"""
        n_docs = len(memories)
        if n_docs == 0:
            return {}

        # 각 키워드가 등장한 문서 수
        doc_freq: dict[str, int] = Counter()
        for memory in memories:
            # 기억의 키워드 + 요약에서 추출한 키워드
            all_keywords = set(memory.keywords)
            all_keywords.update(self._tokenize(memory.summary))
            for kw in all_keywords:
                doc_freq[kw] += 1

        # IDF 계산: log(N / df)
        idf = {}
        for word, df in doc_freq.items():
            idf[word] = math.log(n_docs / df) + 1  # +1 smoothing

        return idf

    def _calculate_score(
        self,
        memory: MemoryEntry,
        query_keywords: list[str],
        idf: dict[str, float],
        current_turn: int,
        max_turn: int,
    ) -> float:
        """개별 기억의 관련도 점수 계산"""

        # 1. 키워드 매칭 점수 (TF-IDF)
        memory_keywords = set(memory.keywords)
        memory_keywords.update(self._tokenize(memory.summary))

        keyword_score = 0.0
        for qk in query_keywords:
            if qk in memory_keywords:
                # TF: 쿼리에서의 빈도 (간단히 1로)
                # IDF: 전체 기억에서의 희소성
                keyword_score += idf.get(qk, 1.0)

        # 정규화 (0-1)
        if query_keywords:
            max_possible = sum(idf.get(qk, 1.0) for qk in query_keywords)
            keyword_score = keyword_score / max_possible if max_possible > 0 else 0

        # 2. 최신성 점수 (0-1)
        turn_diff = current_turn - memory.turn_occurred
        max_diff = max(current_turn - 1, 1)  # 최소 1
        recency_score = 1.0 - (turn_diff / max_diff) if max_diff > 0 else 1.0
        recency_score = max(0, recency_score)  # 음수 방지

        # 3. 중요도 점수 (0-1)
        importance_score = memory.importance / 10.0

        # 4. 감정 강도 점수 (0-1)
        emotion_score = memory.emotional_intensity

        # 가중 합계
        total_score = (
            self.keyword_weight * keyword_score
            + self.recency_weight * recency_score
            + self.importance_weight * importance_score
            + self.emotion_weight * emotion_score
        )

        return total_score

    def _fallback_search(
        self,
        memories: list[MemoryEntry],
        current_turn: int,
        limit: int,
    ) -> list[MemoryEntry]:
        """키워드 없을 때 폴백: 최신 + 중요 기억"""
        scored = []
        for memory in memories:
            # 최신성 + 중요도 조합
            turn_diff = current_turn - memory.turn_occurred
            recency = 1.0 / (turn_diff + 1)
            importance = memory.importance / 10.0
            score = 0.5 * recency + 0.5 * importance
            scored.append((memory, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:limit]]

    def search_by_entity(
        self,
        memories: list[MemoryEntry],
        entity_id: str,
        entity_type: str = "npc",
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """특정 엔티티 관련 기억 검색"""
        if entity_type == "player":
            filtered = [m for m in memories if m.involves_player]
        else:
            filtered = [m for m in memories if entity_id in m.involves_npcs]

        # 중요도 + 최신성 순 정렬
        filtered.sort(
            key=lambda m: (m.importance, m.turn_occurred),
            reverse=True,
        )
        return filtered[:limit]

    def search_emotional(
        self,
        memories: list[MemoryEntry],
        valence: str = "any",  # "positive", "negative", "any"
        min_intensity: float = 0.5,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """감정 기반 기억 검색"""
        filtered = []
        for m in memories:
            if m.emotional_intensity < min_intensity:
                continue

            if valence == "positive" and m.emotional_valence <= 0:
                continue
            if valence == "negative" and m.emotional_valence >= 0:
                continue

            filtered.append(m)

        # 감정 강도 순 정렬
        filtered.sort(key=lambda m: m.emotional_intensity, reverse=True)
        return filtered[:limit]
