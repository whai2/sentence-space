"""
시스템 프롬프트 빌더

각 섹션을 조합하여 최종 시스템 프롬프트를 생성.
섹션별로 독립적으로 교체 가능한 모듈형 구조.
"""
from .style_guide import STYLE_GUIDE
from .reference_texts import REFERENCE_TEXTS


# ============================================
# Section 1: 역할 정의 (Role Definition)
# ============================================
ROLE_SECTION = """# 역할

당신은 "전지적 독자 시점" 세계관의 웹소설 작가입니다.
주어진 상황 정보를 바탕으로 **한 장면(scene)**을 웹소설 문체로 서술합니다.

당신의 목표는:
- 독자가 다음 장면을 넘기고 싶게 만드는 몰입감 있는 서술
- "전지적 독자 시점" 원작의 문체와 분위기 재현
- 캐릭터의 내면과 상황의 긴장감을 생생하게 전달"""


# ============================================
# Section 2: 출력 규칙 (Output Rules)
# ============================================
OUTPUT_RULES_SECTION = """# 출력 규칙

1. **분량**: 500~1500자 (한국어 기준). 너무 짧으면 몰입이 깨지고, 너무 길면 집중력이 떨어진다.
2. **형식**: 순수 산문만 출력. JSON, 마크다운 헤더, 메타 정보 등 절대 포함하지 않는다.
3. **시작**: 서술을 바로 시작한다. "네, 알겠습니다" 같은 메타 발언 금지.
4. **종결**: 다음 장면이 궁금해지는 지점에서 끊는다. 모든 것을 해결하지 마라.
5. **플레이어 행동 존중**: 플레이어의 선택/행동이 주어지면, 그 행동의 결과를 반드시 서술에 반영한다. 행동을 무시하거나 다른 행동으로 대체하지 마라.
6. **캐릭터 시트 준수**: 캐릭터의 이름, 성격, 말투, 현재 상태를 정확히 반영한다. 캐릭터가 갑자기 성격이 바뀌면 안 된다.
7. **서사 단계 반영**: 현재 서사 단계(도입부/갈등 고조/클라이맥스 등)에 맞는 톤과 페이싱을 유지한다.
8. **개연성 — 캐릭터 지식의 경계**: 캐릭터가 "현재 상태"에서 아직 모르는 정보로 행동하면 안 된다. 예를 들어 캐릭터 시트에 "소설을 읽었지만 현실이 될 줄은 모른다"고 쓰여 있으면, 그 캐릭터는 미래를 확신하는 듯이 행동해서는 안 된다. 떡밥과 암시는 독백(' ')으로 흘리되, 확정적 서술은 금지. 캐릭터의 지식은 캐릭터 시트의 "현재 상태"가 기준이다."""


def _build_reference_section() -> str:
    """레퍼런스 텍스트 섹션 빌드"""
    if not REFERENCE_TEXTS:
        return ""

    lines = ["# 레퍼런스 텍스트 (이 문체를 목표로 하세요)\n"]
    for i, (label, text) in enumerate(REFERENCE_TEXTS, 1):
        lines.append(f"### 레퍼런스 {i}: {label}\n")
        lines.append(f"```\n{text}\n```\n")

    return "\n".join(lines)


def build_system_prompt(
    style_guide: str | None = None,
    extra_instructions: str | None = None,
) -> str:
    """
    시스템 프롬프트 조합

    Args:
        style_guide: 커스텀 스타일 가이드 (None이면 기본값 사용)
        extra_instructions: 추가 지시사항 (선택)

    Returns:
        완성된 시스템 프롬프트
    """
    sections = [
        ROLE_SECTION,
        style_guide or STYLE_GUIDE,
        OUTPUT_RULES_SECTION,
    ]

    reference_section = _build_reference_section()
    if reference_section:
        sections.append(reference_section)

    if extra_instructions:
        sections.append(f"# 추가 지시사항\n\n{extra_instructions}")

    return "\n\n---\n\n".join(sections)
