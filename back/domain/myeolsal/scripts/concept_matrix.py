"""
컨셉 매트릭스 생성기

100개의 다양한 괴수 컨셉 시드를 결정론적으로 생성.
등급/종/테마/속성/환경 조합의 다양성을 보장.
"""
import random
from dataclasses import dataclass


@dataclass
class BeastConcept:
    """괴수 생성 컨셉"""
    grade: str
    species: str
    theme: str
    element: str
    environment: str

    @property
    def prompt(self) -> str:
        return (
            f"{self.grade} {self.species}, {self.theme} 테마, "
            f"{self.element} 속성, {self.environment} 환경의 괴수"
        )


# === 등급 목표 분포 (부족한 등급 우선) ===
GRADE_TARGETS = {
    "1급": 8,
    "특급": 4,
    "4급": 12,
    "3급": 12,
    "2급": 8,
    "5급": 12,
    "6급": 14,
    "7급": 12,
    "8급": 10,
    "9급": 8,
}

# === 종 (규칙 6종 + 기존 데이터 확장종) ===
SPECIES_POOL = [
    "괴수종", "악마종", "거신", "재앙", "해수종", "충왕종",
    "인외종", "유령종", "식물종", "지하종", "기계종", "용종",
]

# === 테마 (괴수 성격/역할) ===
THEMES = [
    "포식자", "기생체", "수호자", "군체", "잠행자",
    "변이체", "고대종", "돌연변이", "매복자", "방랑자",
    "광폭화", "지배자", "정찰병", "파괴자", "미믹",
    "흡혈종", "결계사", "환술사", "독살자", "부활자",
]

# === 속성 ===
ELEMENTS = [
    "화염", "수속성", "빙결", "전기", "지속성",
    "신성", "어둠", "물리", "독", "무속성",
]

# === 환경 ===
ENVIRONMENTS = [
    "지하철", "한강", "마계", "심해", "폐건물",
    "산악", "도심", "숲", "하수도", "차원균열",
    "화산", "빙하", "사막", "늪지", "공중",
]


def generate_concepts(count: int = 100, seed: int = 42) -> list[BeastConcept]:
    """
    다양한 괴수 컨셉 생성

    Args:
        count: 생성할 컨셉 수
        seed: 랜덤 시드 (재현 가능)

    Returns:
        컨셉 리스트
    """
    rng = random.Random(seed)
    concepts: list[BeastConcept] = []
    seen_combos: set[tuple[str, str, str]] = set()

    # 등급별 할당
    grade_queue: list[str] = []
    for grade, target in GRADE_TARGETS.items():
        grade_queue.extend([grade] * target)

    rng.shuffle(grade_queue)
    grade_queue = grade_queue[:count]

    for grade in grade_queue:
        # 종 선택 (등급에 맞는 종 가중치)
        species_weights = _get_species_weights(grade)
        species = _weighted_choice(rng, SPECIES_POOL, species_weights)

        # 고유 (grade, species, theme) 조합 보장
        for _ in range(50):
            theme = rng.choice(THEMES)
            combo = (grade, species, theme)
            if combo not in seen_combos:
                seen_combos.add(combo)
                break
        else:
            # 50번 시도 후 실패 시 다른 종으로
            theme = rng.choice(THEMES)

        element = _pick_element(rng, species)
        environment = _pick_environment(rng, grade)

        concepts.append(BeastConcept(
            grade=grade,
            species=species,
            theme=theme,
            element=element,
            environment=environment,
        ))

    return concepts


def _get_species_weights(grade: str) -> list[float]:
    """등급에 따른 종 가중치"""
    # 고등급(1~3급, 특급)에 강력한 종 우대
    if grade in ("1급", "특급"):
        #          괴수종 악마종 거신 재앙 해수종 충왕종 인외종 유령종 식물종 지하종 기계종 용종
        return    [1,    3,    3,   3,   1,    1,    1,    2,    0.5,  0.5,  1,    3]
    elif grade in ("2급", "3급"):
        return    [1,    2,    2,   2,   1,    1,    1,    1,    0.5,  0.5,  1,    2]
    elif grade in ("4급", "5급"):
        return    [2,    2,    1,   1,   2,    2,    1,    1,    1,    1,    2,    1]
    elif grade in ("6급", "7급"):
        return    [3,    1,    1,   1,   2,    2,    2,    1,    2,    2,    1,    1]
    else:  # 8~9급
        return    [3,    0.5,  0.5, 0.5, 2,    2,    2,    1,    2,    3,    1,    0.5]


def _weighted_choice(rng: random.Random, items: list, weights: list[float]) -> str:
    """가중치 기반 랜덤 선택"""
    total = sum(weights)
    r = rng.random() * total
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def _pick_element(rng: random.Random, species: str) -> str:
    """종에 어울리는 속성 선택"""
    species_element_affinities = {
        "악마종": ["어둠", "화염", "독"],
        "해수종": ["수속성", "빙결"],
        "충왕종": ["독", "물리"],
        "거신": ["물리", "지속성", "화염"],
        "재앙": ["화염", "빙결", "전기", "어둠"],
        "유령종": ["어둠", "신성", "빙결"],
        "식물종": ["독", "지속성", "수속성"],
        "기계종": ["전기", "물리"],
        "용종": ["화염", "빙결", "전기"],
    }
    affinities = species_element_affinities.get(species)
    if affinities and rng.random() < 0.6:
        return rng.choice(affinities)
    return rng.choice(ELEMENTS)


def _pick_environment(rng: random.Random, grade: str) -> str:
    """등급에 어울리는 환경 선택"""
    if grade in ("1급", "특급", "2급"):
        high_grade_envs = ["마계", "차원균열", "심해", "화산", "빙하"]
        if rng.random() < 0.5:
            return rng.choice(high_grade_envs)
    elif grade in ("8급", "9급"):
        low_grade_envs = ["지하철", "폐건물", "하수도", "도심", "숲"]
        if rng.random() < 0.5:
            return rng.choice(low_grade_envs)
    return rng.choice(ENVIRONMENTS)


def print_concepts(concepts: list[BeastConcept]) -> None:
    """컨셉 목록 출력"""
    grade_counts: dict[str, int] = {}
    species_counts: dict[str, int] = {}
    theme_counts: dict[str, int] = {}

    for i, c in enumerate(concepts, 1):
        print(f"  [{i:3d}] {c.prompt}")
        grade_counts[c.grade] = grade_counts.get(c.grade, 0) + 1
        species_counts[c.species] = species_counts.get(c.species, 0) + 1
        theme_counts[c.theme] = theme_counts.get(c.theme, 0) + 1

    print(f"\n  === 등급 분포 ({len(concepts)}개) ===")
    for g in ["9급", "8급", "7급", "6급", "5급", "4급", "3급", "2급", "1급", "특급"]:
        bar = "#" * grade_counts.get(g, 0)
        print(f"  {g:4s}: {grade_counts.get(g, 0):2d} {bar}")

    print(f"\n  === 종 분포 ===")
    for sp, cnt in sorted(species_counts.items(), key=lambda x: -x[1]):
        print(f"  {sp}: {cnt}")

    print(f"\n  === 테마 분포 ===")
    for th, cnt in sorted(theme_counts.items(), key=lambda x: -x[1]):
        print(f"  {th}: {cnt}")
