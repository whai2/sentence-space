"""Query Pre-Filter - Regex 기반 사전 필터링"""

import re
from enum import Enum


class PreFilterResult(str, Enum):
    PASS = "PASS"
    SKIP = "SKIP"


class QueryPreFilter:
    """사전 필터링: 명백한 노이즈를 빠르게 제거

    동기 함수, 정규식 기반.
    인사말, 단순 반응, 너무 짧은 메시지 등을 필터링.
    """

    MIN_MEANINGFUL_LENGTH = 5

    SKIP_PATTERNS = [
        r"^(안녕|하이|헬로|hello|hi|hey|yo)[\s!?.]*$",
        r"^(감사합니다|고마워|ㄱㅅ|ㅇㅋ|ok|okay|네|예|응|ㅇ)[\s!?.]*$",
        r"^(ㅎㅎ+|ㅋㅋ+|ㄷㄷ+|ㅠㅠ+|ㅜㅜ+|lol|lmao)[\s!?.]*$",
        r"^(아니|취소|됐어|잠깐|잠만)[\s!?.]*$",
        r"^test.*$",
        r"^(\.+|;+)$",
    ]

    def __init__(self):
        self._compiled = [
            re.compile(p, re.IGNORECASE) for p in self.SKIP_PATTERNS
        ]

    def should_store(self, message: str) -> PreFilterResult:
        """메시지를 저장할 가치가 있는지 사전 판단"""
        stripped = message.strip()

        if len(stripped) < self.MIN_MEANINGFUL_LENGTH:
            return PreFilterResult.SKIP

        for pattern in self._compiled:
            if pattern.match(stripped):
                return PreFilterResult.SKIP

        return PreFilterResult.PASS
