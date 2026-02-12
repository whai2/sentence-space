"""
괴수 직접 생성 스크립트

Claude Code가 직접 JSON 데이터를 템플릿 기반으로 구성.
LLM API 호출 없음. Pinecone 임베딩 비용(~$0.15)만 발생.

Usage:
    cd back
    uv run python -m domain.myeolsal.scripts.direct_generate              # 760마리 생성
    uv run python -m domain.myeolsal.scripts.direct_generate --dry-run    # 분포만 출력
    uv run python -m domain.myeolsal.scripts.direct_generate --count 100  # 100마리만
    uv run python -m domain.myeolsal.scripts.direct_generate --no-pinecone  # JSON만 저장
"""
import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from domain.myeolsal.models import BeastEntry, BeastLayer, BeastStats, CombatPattern
from domain.myeolsal.agents.beast_validator import BeastValidatorAgent
from domain.myeolsal.container import get_myeolsal_rules, get_pinecone_repository, get_validator

# ===================================================================
# CONSTANTS
# ===================================================================

DATA_DIR = Path(__file__).parent.parent / "data"
CANON_FILE = DATA_DIR / "canon_beasts.json"

STAT_ORDER = ["E", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+", "S"]

# Grade -> stat index ranges (min_idx, max_idx into STAT_ORDER)
GRADE_STAT_RANGES = {
    "9급":  {"hp": (0, 1), "atk": (0, 1), "defense": (0, 1), "spd": (0, 2), "spc": (0, 0)},
    "8급":  {"hp": (1, 3), "atk": (1, 3), "defense": (1, 3), "spd": (2, 4), "spc": (0, 2)},
    "7급":  {"hp": (2, 5), "atk": (2, 5), "defense": (2, 5), "spd": (3, 5), "spc": (0, 5)},
    "6급":  {"hp": (5, 7), "atk": (4, 8), "defense": (5, 8), "spd": (5, 8), "spc": (2, 6)},
    "5급":  {"hp": (7, 11), "atk": (8, 11), "defense": (7, 10), "spd": (7, 11), "spc": (5, 11)},
    "4급":  {"hp": (10, 13), "atk": (10, 13), "defense": (10, 13), "spd": (10, 13), "spc": (7, 13)},
    "3급":  {"hp": (11, 13), "atk": (11, 13), "defense": (11, 13), "spd": (11, 13), "spc": (8, 13)},
    "2급":  {"hp": (12, 13), "atk": (12, 13), "defense": (12, 13), "spd": (12, 13), "spc": (10, 13)},
    "1급":  {"hp": (13, 13), "atk": (13, 13), "defense": (13, 13), "spd": (13, 13), "spc": (11, 13)},
    "특급": {"hp": (13, 13), "atk": (13, 13), "defense": (13, 13), "spd": (13, 13), "spc": (13, 13)},
}

DANGER_CLASS_MAP = {
    "9급": "안전", "8급": "안전", "7급": "보통", "6급": "보통",
    "5급": "위험", "4급": "위험", "3급": "치명", "2급": "치명",
    "1급": "치명", "특급": "치명",
}

COIN_RANGES = {
    "9급": (5, 20), "8급": (15, 50), "7급": (30, 100), "6급": (80, 250),
    "5급": (200, 600), "4급": (500, 1500), "3급": (1000, 3000),
    "2급": (2500, 7000), "1급": (5000, 15000), "특급": (10000, 50000),
}

# Target distribution for 760 new beasts (lower grades more common)
GRADE_DISTRIBUTION = {
    "9급": 80, "8급": 100, "7급": 130, "6급": 120, "5급": 100,
    "4급": 70, "3급": 55, "2급": 40, "1급": 35, "특급": 30,
}

ALL_SPECIES = [
    "괴수종", "악마종", "거신", "재앙", "해수종", "충왕종",
    "인외종", "유령종", "식물종", "지하종", "기계종", "용종",
]

SPECIES_WEIGHTS = {
    "low":   [3, 0.5, 0.5, 0.5, 2, 2, 2, 1, 2, 3, 1, 0.5],
    "mid":   [3, 1, 1, 1, 2, 2, 2, 1, 2, 2, 1, 1],
    "high":  [2, 2, 1.5, 1, 2, 1.5, 1, 1, 1, 1, 2, 1.5],
    "elite": [1, 3, 2.5, 2.5, 1, 1, 1, 2, 0.5, 0.5, 1, 3],
}

ENVIRONMENTS = [
    "지하철", "한강", "마계", "심해", "폐건물", "산악", "도심", "숲",
    "하수도", "차원균열", "화산", "빙하", "사막", "늪지", "공중",
    "동굴", "폐광", "항구", "강변", "호수", "초원", "정글", "설원",
    "지하묘지", "폐공장", "고속도로", "지하상가", "옥상", "탑", "폐교",
]

# ===================================================================
# SPECIES-SPECIFIC DATA
# ===================================================================

SPECIES_ELEMENTS = {
    "괴수종": ["물리", "독", "화염", "빙결", "전기", "무속성"],
    "악마종": ["어둠", "화염", "독", "빙결"],
    "거신":   ["물리", "지속성", "화염", "빙결"],
    "재앙":   ["화염", "빙결", "전기", "어둠", "독"],
    "해수종": ["수속성", "빙결", "독"],
    "충왕종": ["독", "물리", "화염"],
    "인외종": ["어둠", "물리", "화염", "빙결"],
    "유령종": ["어둠", "빙결", "신성"],
    "식물종": ["독", "지속성", "수속성"],
    "지하종": ["물리", "지속성", "독"],
    "기계종": ["전기", "물리", "화염"],
    "용종":   ["화염", "빙결", "전기", "독", "어둠"],
}

SPECIES_WEAKNESSES = {
    "괴수종": [["화염"], ["빙결"], ["전기"], ["독"]],
    "악마종": [["신성"], ["신성", "화염"], ["신성", "빙결"]],
    "거신":   [["빙결"], ["전기"], ["독"]],
    "재앙":   [["신성"], ["물리"], ["빙결"]],
    "해수종": [["화염", "전기"], ["전기"], ["화염"]],
    "충왕종": [["화염"], ["화염", "빙결"], ["전기"]],
    "인외종": [["화염"], ["신성"], ["물리"]],
    "유령종": [["신성"], ["신성", "화염"], ["화염"]],
    "식물종": [["화염"], ["화염", "빙결"]],
    "지하종": [["수속성"], ["빙결"], ["화염"]],
    "기계종": [["수속성"], ["전기"], ["물리"]],
    "용종":   [["빙결"], ["신성"], ["독"]],
}

SPECIES_RESISTANCES = {
    "괴수종": [[], ["물리"], ["독"]],
    "악마종": [["어둠"], ["화염"], ["독"]],
    "거신":   [["물리"], ["지속성"], []],
    "재앙":   [["물리"], [], ["화염"]],
    "해수종": [["수속성"], ["빙결"], []],
    "충왕종": [["독"], [], ["물리"]],
    "인외종": [["독"], ["어둠"], []],
    "유령종": [["물리"], ["독"], ["빙결"]],
    "식물종": [["수속성"], ["지속성"], []],
    "지하종": [["물리"], ["독"], []],
    "기계종": [["독"], ["물리"], []],
    "용종":   [["화염"], ["빙결"], ["물리"]],
}

# ===================================================================
# NAME GENERATION POOLS
# ===================================================================

ENV_PREFIXES = [
    "한강", "심해", "마계", "지하", "산악", "도심", "숲속", "폐허",
    "사막", "늪지", "화산", "빙하", "동굴", "하수도", "하늘", "항구",
    "강변", "호수", "초원", "정글", "설원", "폐광", "탑", "해안",
    "절벽", "계곡", "고원", "밀림", "극지", "열대", "심연", "폐교",
]

ATTR_PREFIXES = [
    "화염", "독", "암흑", "철", "빙결", "뇌전", "고대", "거대",
    "소형", "돌연변이", "광폭", "결정", "수정", "혈", "흑", "백",
    "적", "청", "금", "은", "녹", "맹독", "부식", "신성",
    "저주", "폭풍", "안개", "가시", "강철", "투명", "그림자", "비늘",
    "갑각", "기생", "흡혈", "변이", "야생", "서리", "용암", "진흙",
    "번개", "황산", "마력", "영혼", "뼈", "무쇠", "수은", "자수정",
]

CREATURE_CORES = {
    "괴수종": [
        "늑대", "곰", "뱀", "표범", "호랑이", "악어", "하이에나", "멧돼지",
        "들소", "독수리", "코뿔소", "도마뱀", "두꺼비", "카멜레온",
        "도롱뇽", "너구리", "오소리", "고릴라", "사슴", "코모도",
        "아나콘다", "보아", "피라냐", "비버", "족제비", "수달",
    ],
    "악마종": [
        "마귀", "악령", "임프", "서큐버스", "광대", "기사", "암살자",
        "마법사", "공작", "후작", "백작", "남작", "밀사", "심문관",
        "사형집행인", "유혹자", "계약자", "방랑악마", "무도회령",
    ],
    "거신": [
        "골렘", "거인", "타이탄", "콜로서스", "센티넬", "가디언",
        "거상", "바위거인", "얼음거인", "화염거인", "철거인",
        "대지신", "산악신", "수정거인", "토석거인", "용암거인",
    ],
    "재앙": [
        "폭풍", "해일", "지진", "역병", "가뭄", "홍수", "블리자드",
        "태풍", "쓰나미", "산사태", "혹한", "번개폭풍", "모래폭풍",
        "산성비", "화산재", "흑사병", "대홍수", "빙하기", "열파",
    ],
    "해수종": [
        "상어", "문어", "해파리", "가오리", "바다뱀", "거북", "게",
        "오징어", "가재", "불가사리", "산호", "고래", "해마", "복어",
        "아귀", "장어", "해삼", "물범", "돌고래", "갑오징어",
    ],
    "충왕종": [
        "벌", "말벌", "개미", "나방", "딱정벌레", "사마귀", "거미",
        "전갈", "지네", "메뚜기", "잠자리", "매미", "바퀴벌레",
        "파리", "모기", "진드기", "장수풍뎅이", "귀뚜라미", "노린재",
    ],
    "인외종": [
        "좀비", "구울", "리치", "뱀파이어", "가고일", "오크",
        "고블린", "트롤", "코볼트", "사티로스", "라미아", "미라",
        "인랑", "하피", "오거", "도플갱어", "망자", "변이인간",
    ],
    "유령종": [
        "유령", "레이스", "밴시", "팬텀", "스펙터", "망령",
        "원혼", "악귀", "야차", "귀불", "도깨비", "원령",
        "사령", "저주령", "배회령", "통곡령", "그림자", "혼백",
    ],
    "식물종": [
        "덩굴", "나무", "버섯", "이끼", "해초", "선인장", "연꽃",
        "독초", "가시나무", "수련", "참나무", "대나무", "포자",
        "뿌리", "넝쿨", "꽃", "칡", "씨앗", "균사체", "이파리",
    ],
    "지하종": [
        "두더지", "지렁이", "노래기", "굼벵이", "박쥐", "쥐",
        "도룡뇽", "갑충", "야광충", "굴파기", "석순충", "거머리",
        "동굴거미", "땅벌레", "혈석충", "암석충", "광석쥐", "심층어",
    ],
    "기계종": [
        "드론", "로봇", "골렘", "오토마톤", "센티널", "터렛",
        "크롤러", "스캐너", "파쇄기", "절단기", "드릴", "프레스",
        "시계", "인형", "톱니", "피스톤", "전기로봇", "증기기관",
    ],
    "용종": [
        "드래곤", "와이번", "드레이크", "린드부름", "히드라", "이무기",
        "서펀트", "바실리스크", "비룡", "흑룡", "청룡", "적룡",
        "백룡", "독룡", "뇌룡", "빙룡", "염룡", "암룡",
    ],
}

NAME_SUFFIXES = [
    "왕", "군주", "여왕", "장군", "대장", "사냥꾼", "포식자",
    "방랑자", "수호자", "감시자", "잠행자", "파괴자", "유충",
    "새끼", "성체", "변종", "고대종", "돌연변이", "진화체", "아종",
]

# Pre-crafted special names for elite beasts
ELITE_NAMES = [
    "아스모데우스", "벨리알", "메피스토", "아바돈", "발로르",
    "모르가나", "리리스", "아자젤", "에레보스", "타나토스",
    "헤카테", "칼리스토", "모르페우스", "이카루스", "프로메테우스",
    "티아마트", "파프니르", "니드호그", "요르문간드", "펜리르",
    "수르트", "아포피스", "원초의 어둠", "천년의 기아",
    "영원의 감시자", "끝없는 질투", "운명의 직조자", "심연의 군주",
    "절멸의 불꽃", "혼돈의 심장", "황혼의 사도", "종말의 수확자",
    "망각의 왕", "시간의 포식자", "공간의 균열자", "영혼의 약탈자",
]

# ===================================================================
# DESCRIPTION TEMPLATES
# ===================================================================

SIZES = {
    "9급": (0.3, 1.5), "8급": (0.5, 3), "7급": (1, 5), "6급": (2, 8),
    "5급": (3, 12), "4급": (5, 20), "3급": (8, 30), "2급": (10, 50),
    "1급": (15, 100), "특급": (20, 200),
}

COLORS = ["검은", "붉은", "푸른", "하얀", "녹색", "보라", "금색", "은색", "회색", "주황", "진홍", "청록"]
TEXTURES = ["비늘", "갑각", "털", "점액질", "키틴질", "금속", "바위", "수정", "가죽", "이끼"]
WEAPONS = ["이빨", "발톱", "뿔", "가시", "촉수", "턱", "독침", "꼬리", "날개"]
DEFENSES = ["외피", "갑각", "비늘", "껍질", "보호막", "두꺼운 지방층", "강철 피부"]
EMISSIONS = ["독안개", "냉기", "열기", "전기", "어둠 오라", "포자", "마력파", "산성 체액"]

DESC_SPECIES_INTROS = {
    "괴수종": [
        "{env}에 서식하는 {grade} 괴수종.",
        "{env}의 생태계 최상위 포식자로 분류된 {grade} 괴수.",
        "정체불명의 돌연변이로 추정되는 {grade} 괴수종.",
        "{env}에서 목격되는 흉포한 {grade} 괴수.",
        "야생에서 무리 지어 활동하는 {grade} 등급 괴수종.",
    ],
    "악마종": [
        "마계에서 넘어온 것으로 추정되는 {grade} 악마종.",
        "{env}에서 소환된 {grade}급 악마.",
        "차원 균열을 통해 출현한 지능형 {grade} 악마종.",
        "고대 의식으로 봉인되었다가 깨어난 {grade} 악마.",
        "마계 서열이 존재하는 것으로 추정되는 {grade} 악마종.",
    ],
    "거신": [
        "{env}에 자리 잡은 거대한 {grade} 거신.",
        "태초부터 존재했다고 전해지는 {grade} 거신.",
        "{env}의 지형을 바꿀 정도로 거대한 {grade} 거신.",
        "수백 년간 잠들어 있다 깨어난 {grade} 등급 거신.",
        "움직이는 산이라 불리는 {grade} 거신.",
    ],
    "재앙": [
        "{env} 일대를 초토화시킨 {grade}급 재앙.",
        "자연 현상 자체가 실체화한 {grade} 재앙.",
        "{env}에 주기적으로 발생하는 {grade}급 환경형 재앙.",
        "광역 피해를 동반하는 {grade} 등급 재앙.",
        "발생하면 주변 수 km를 휩쓸어 버리는 {grade} 재앙.",
    ],
    "해수종": [
        "{env}의 수중에서 활동하는 {grade} 해수종.",
        "깊은 물속에 서식하는 {grade} 등급 해수종.",
        "{env} 해역에서 목격되는 {grade} 해수종.",
        "수중 전투에 특화된 {grade}급 해수종.",
        "육상에서는 약해지지만 수중에서 극강인 {grade} 해수종.",
    ],
    "충왕종": [
        "{env}에 군락을 형성한 {grade} 충왕종.",
        "떼를 지어 습격하는 {grade} 등급 충왕종.",
        "페로몬으로 통신하는 {grade} 충왕종 군체.",
        "개체 하나는 약하지만 군체로 위협적인 {grade} 충왕종.",
        "진화 가능성이 확인된 {grade} 충왕종.",
    ],
    "인외종": [
        "인간과 유사한 외형을 가진 {grade} 인외종.",
        "{env}에서 발견된 인간형 {grade} 괴수.",
        "원래 인간이었으나 변이된 것으로 추정되는 {grade} 인외종.",
        "인간 사회에 잠입하기도 하는 {grade} 등급 인외종.",
        "지능이 있어 의사소통 가능성이 있는 {grade} 인외종.",
    ],
    "유령종": [
        "{env}에 출몰하는 {grade} 유령종.",
        "물리 공격이 통하지 않는 {grade} 등급 유령종.",
        "원한을 품고 떠도는 {grade} 유령종 괴수.",
        "야간에만 실체화하는 {grade} 유령종.",
        "{env}의 특정 장소에 묶여 있는 {grade} 유령종.",
    ],
    "식물종": [
        "{env}에 뿌리내린 {grade} 식물종.",
        "이동이 불가능하지만 치명적인 {grade} 식물종.",
        "포자로 번식하는 위험한 {grade} 식물종.",
        "동물을 포식하는 {grade} 식물종 괴수.",
        "{env} 전체를 뒤덮은 {grade} 등급 식물종.",
    ],
    "지하종": [
        "{env} 깊은 곳에 서식하는 {grade} 지하종.",
        "빛을 싫어하는 {grade} 등급 지하종.",
        "지하 터널을 파며 이동하는 {grade} 지하종.",
        "지상에서는 약해지는 {grade} 지하종.",
        "{env} 지하에 거대한 굴을 형성한 {grade} 지하종.",
    ],
    "기계종": [
        "{env}에서 발견된 정체불명의 {grade} 기계종.",
        "고대 문명의 유산으로 추정되는 {grade} 기계종.",
        "자가 수리 능력을 갖춘 {grade} 등급 기계종.",
        "에너지원이 밝혀지지 않은 {grade} 기계종.",
        "누가 만들었는지 모르는 {grade} 기계종.",
    ],
    "용종": [
        "{env}에서 목격된 {grade} 등급 용종.",
        "드래곤의 혈통을 이어받은 {grade} 용종.",
        "브레스 공격이 확인된 {grade} 등급 용종.",
        "고대 용의 후예로 추정되는 {grade} 용종.",
        "{env} 최강의 포식자인 {grade} 용종.",
    ],
}

DESC_BODIES = [
    "몸길이 약 {size}m에 달하며 {color} {texture}로 뒤덮여 있다.",
    "{size}m급 체구에 날카로운 {weapon}과 단단한 {defense}를 갖추고 있다.",
    "{color} 빛깔의 {texture}가 특징이며 전신에서 {emission}을 내뿜는다.",
    "외형은 일반 동물과 유사하나 {size}m에 달하는 비정상적 크기가 특징이다.",
    "{defense}로 무장한 {size}m급 개체로, {weapon}이 주 무기이다.",
    "{color} {texture}에 {emission}을 방출하며 접근하는 것만으로도 위험하다.",
    "겉보기엔 평범하나 {size}m까지 팽창하며 {weapon}을 드러낸다.",
    "{texture}로 둘러싸인 {size}m급 몸체에서 {emission}이 끊임없이 새어 나온다.",
]

DESC_BEHAVIORS = [
    "영역 내 침입자를 무차별 공격한다.",
    "야행성이며 낮에는 은신한다.",
    "먹이를 찾아 끊임없이 이동한다.",
    "특정 주기로 광폭화하여 무차별 공격을 가한다.",
    "떼를 지어 조직적으로 사냥한다.",
    "매복하여 먹이가 접근하길 기다린다.",
    "영역 표시를 하며 다른 괴수도 피해 간다.",
    "소리에 민감하게 반응하므로 조용히 접근해야 한다.",
    "지능이 높아 함정을 설치하기도 한다.",
    "번식기에는 평소보다 3배 이상 공격적이다.",
    "상처를 입으면 동족을 불러 모은다.",
    "환경에 따라 체색을 바꿔 위장한다.",
    "약점을 본능적으로 숨기는 교활함이 있다.",
    "주변 원소를 흡수하여 점점 강해진다.",
    "인간의 소리를 흉내 내어 먹이를 유인한다.",
]

# ===================================================================
# COMBAT PATTERN DATA
# ===================================================================

ATTACK_NAMES = {
    "물리": [
        "물어뜯기", "할퀴기", "들이받기", "꼬리 후려치기", "돌진", "밟기",
        "집어던지기", "조이기", "내려치기", "돌격", "박치기", "연속 할퀴기",
        "뿔 들이밀기", "몸통 박치기", "짓밟기", "찢어발기기", "베어 가르기",
    ],
    "화염": [
        "화염 브레스", "화염구", "화염 폭발", "용암 분출", "불꽃 돌진",
        "발화", "화염 회오리", "열폭풍", "연소 오라", "소이탄",
    ],
    "빙결": [
        "냉기 브레스", "얼음 가시", "냉기파", "동결 오라", "빙결 장벽",
        "눈보라", "얼음 감옥", "서리 폭발", "동토의 숨결", "빙룡파",
    ],
    "전기": [
        "번개 충격", "전기 방전", "뇌전 낙하", "연쇄 번개", "전자기 펄스",
        "뇌격", "정전기 폭발", "전기 그물", "번개 돌진", "전류 흐름",
    ],
    "독": [
        "독 분사", "독안개", "맹독 침", "독가시", "독액 투사",
        "부식액", "포자 살포", "신경독 주입", "마비 가스", "독 분진",
    ],
    "수속성": [
        "수압 발사", "물기둥", "해일", "소용돌이", "물 채찍",
        "수중 충격파", "폭류", "수벽", "익사 포박", "거품 돌격",
    ],
    "어둠": [
        "그림자 찌르기", "암흑파", "저주의 눈", "영혼 흡수", "어둠 폭발",
        "공포의 시선", "그림자 속박", "암흑 침식", "악몽 유도", "사역",
    ],
    "신성": [
        "정화의 빛", "성스러운 불꽃", "심판의 번개", "신벌", "정화 오라",
        "봉인", "빛의 창", "축복 해제", "성광 폭발", "심판의 창",
    ],
    "지속성": [
        "지진", "바위 투사", "모래 폭풍", "지면 융기", "진동파",
        "대지 함몰", "암석 갑옷", "토석류", "지면 균열", "석화 시선",
    ],
    "무속성": [
        "무속성 돌진", "에너지파", "충격파", "진동", "폭발",
        "관통", "파쇄", "집중 공격", "흡수", "반사",
    ],
}

TRIGGERS = [
    "always", "hp_below_50", "hp_below_30", "enraged",
    "group_3plus", "night_only", "cornered", "first_strike",
    "target_isolated", "defending_territory", "proximity_close",
    "after_taking_damage", "every_3_turns",
]

# ===================================================================
# SURVIVAL / WARNING / LORE TEMPLATES
# ===================================================================

SURVIVAL_TEMPLATES = [
    "{weakness} 속성 공격이 효과적이다. {tip}.",
    "{weakness}에 약하므로 해당 속성 무기를 준비하라. {tip}.",
    "핵심은 {strategy}이다. {weakness}으로 약점을 공략하면 유리하다.",
    "{tip}. {weakness} 계열 공격 시 방어력이 크게 떨어진다.",
    "단독 교전은 피하고 {strategy}. {weakness}이 유일한 약점이다.",
]

TIPS = [
    "야간 이동을 피하라", "소리를 최소화하라", "높은 지대를 확보하라",
    "장기전을 피하고 속전속결하라", "무리와 떨어진 개체를 노려라",
    "선제공격으로 기선을 제압하라", "도주 경로를 미리 확보하라",
    "파티 단위로만 교전하라", "방어 진형을 유지하라",
    "은신하여 관찰 후 약점을 파악하라", "먹이로 유인하여 매복하라",
    "측면에서 접근하라", "수중 전투는 피하라",
    "일정 거리 이상 유지하라", "화염 무기를 반드시 지참하라",
]

STRATEGIES = [
    "선제공격 후 빠른 이탈", "지휘 개체를 먼저 처리하는 것",
    "약점 부위를 집중 공격하는 것", "광역 공격으로 수를 줄이는 것",
    "속성 무기로 효과적으로 대미지를 주는 것", "범위 공격을 회피한 후 반격하는 것",
    "단기 결전으로 끝내는 것", "환경을 이용하여 이동을 제한하는 것",
    "진형을 유지하며 차례로 처리하는 것", "방어력이 낮은 부위를 노리는 것",
]

WARNING_POOL = [
    "단독 교전 금지", "야간 접근 금지", "소음 주의", "독 저항 장비 필수",
    "화염 내성 장비 권장", "수중 전투 시 극도의 주의", "광폭화 시 즉시 후퇴",
    "무리 중 대형 개체 우선 처리", "번식기 접근 금지", "함정 주의",
    "시야 확보 필수", "해독제 상비", "보호 결계 준비",
    "정신 공격 대비 필수", "퇴로 확보 후 교전", "확인 사살 필수",
    "재생 능력 확인 필수", "속성 상성 무시 불가", "먹이로 오인 주의",
]

LORE_TEMPLATES = [
    "최초 목격은 {time}경으로 {location}에서 보고되었다.",
    "멸살법 제1권에 '추정' 표시가 있는 항목이다.",
    "다수의 화신이 조우를 보고했으나 정식 기록은 없다.",
    "tls123의 메모: '{memo}'.",
    "아직 정식 등급 판정을 받지 못한 신종이다.",
    "{origin}과 관련이 있을 가능성이 제기되었다.",
    "여러 시나리오에 걸쳐 반복 등장하는 것이 확인되었다.",
    "최근 개체 수가 {trend}하는 추세이다.",
    "이 종에 대한 정보는 아직 불완전하다. 추가 조사 필요.",
    "생존자 증언: '{testimony}'.",
]

LORE_FILLS = {
    "time": ["3년 전", "최근 1년", "10년 전", "5년 전", "시나리오 초기", "2차 대규모 발생 시"],
    "location": ["서울 도심", "마계 접경", "해안 지역", "산악 깊은 곳", "지하 깊은 곳", "차원 균열 부근"],
    "memo": [
        "위험하다. 혼자 가지 마라", "생각보다 지능이 높다", "준비만 하면 된다",
        "이놈은 진짜 조심해야 한다", "확인 안 된 능력이 있을 수 있다",
        "겉보기와 다르다", "패턴만 파악하면 어렵지 않다",
    ],
    "origin": ["마계 침공", "차원 붕괴", "고대 봉인 해제", "돌연변이 발생", "인간의 실험"],
    "trend": ["증가", "감소", "급증", "안정", "불규칙 변동"],
    "testimony": [
        "그 소리를 들으면 이미 늦은 거다", "눈을 마주치면 안 된다",
        "불이 없으면 못 산다", "절대 혼자 가지 마라",
        "처음엔 작아 보이는데 실물은 상상 이상이다",
    ],
}


# ===================================================================
# GENERATION FUNCTIONS
# ===================================================================

def weighted_choice(rng: random.Random, items: list, weights: list[float]) -> str:
    total = sum(weights)
    r = rng.random() * total
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def gen_stats(grade: str, rng: random.Random) -> dict:
    ranges = GRADE_STAT_RANGES[grade]
    return {stat: STAT_ORDER[rng.randint(lo, hi)] for stat, (lo, hi) in ranges.items()}


def gen_name(species: str, grade: str, rng: random.Random, existing: set[str]) -> str:
    elite_grades = {"1급", "2급", "특급"}
    high_grades = {"3급", "4급"}
    used_elite = set()

    for _ in range(200):
        strategy = rng.random()
        elite_chance = 0.4 if grade in elite_grades else 0.15 if grade in high_grades else 0.0

        if strategy < elite_chance:
            available = [n for n in ELITE_NAMES if n not in existing and n not in used_elite]
            if available:
                name = rng.choice(available)
                used_elite.add(name)
            else:
                continue
        elif strategy < 0.30:
            env = rng.choice(ENV_PREFIXES)
            core = rng.choice(CREATURE_CORES.get(species, CREATURE_CORES["괴수종"]))
            name = f"{env} {core}"
        elif strategy < 0.55:
            attr = rng.choice(ATTR_PREFIXES)
            core = rng.choice(CREATURE_CORES.get(species, CREATURE_CORES["괴수종"]))
            name = f"{attr} {core}"
        elif strategy < 0.75:
            core = rng.choice(CREATURE_CORES.get(species, CREATURE_CORES["괴수종"]))
            suffix = rng.choice(NAME_SUFFIXES)
            name = f"{core} {suffix}"
        elif strategy < 0.90:
            env = rng.choice(ENV_PREFIXES)
            attr = rng.choice(ATTR_PREFIXES)
            core = rng.choice(CREATURE_CORES.get(species, CREATURE_CORES["괴수종"]))
            name = f"{env} {attr} {core}"
        else:
            attr = rng.choice(ATTR_PREFIXES)
            core = rng.choice(CREATURE_CORES.get(species, CREATURE_CORES["괴수종"]))
            suffix = rng.choice(NAME_SUFFIXES)
            name = f"{attr} {core} {suffix}"

        if name not in existing:
            existing.add(name)
            return name

    fallback = f"미확인 괴수 #{rng.randint(1000, 9999)}"
    existing.add(fallback)
    return fallback


def gen_description(species: str, grade: str, env: str, rng: random.Random) -> str:
    intro_templates = DESC_SPECIES_INTROS.get(species, DESC_SPECIES_INTROS["괴수종"])
    intro = rng.choice(intro_templates).format(env=env, grade=grade)

    size_range = SIZES.get(grade, (1, 5))
    size = round(rng.uniform(size_range[0], size_range[1]), 1)
    body = rng.choice(DESC_BODIES).format(
        size=size, color=rng.choice(COLORS), texture=rng.choice(TEXTURES),
        weapon=rng.choice(WEAPONS), defense=rng.choice(DEFENSES),
        emission=rng.choice(EMISSIONS),
    )

    behavior = rng.choice(DESC_BEHAVIORS)
    return f"{intro} {body} {behavior}"


def gen_combat_patterns(species: str, grade: str, element: str, rng: random.Random) -> list[dict]:
    if grade in ("9급", "8급"):
        num = rng.randint(1, 2)
    elif grade in ("7급", "6급"):
        num = rng.randint(2, 3)
    elif grade in ("5급", "4급"):
        num = rng.randint(2, 4)
    else:
        num = rng.randint(3, 4)

    phys_pool = ATTACK_NAMES["물리"]
    elem_pool = ATTACK_NAMES.get(element, phys_pool)
    patterns = []
    used = set()

    for i in range(num):
        if i == 0:
            pool, trigger, dmg = phys_pool, "always", "물리"
        elif i == 1 and element != "물리":
            pool = elem_pool
            trigger = rng.choice(["always", "hp_below_50", "enraged"])
            dmg = element
        else:
            dmg = rng.choice(["물리", element])
            pool = ATTACK_NAMES.get(dmg, phys_pool)
            trigger = rng.choice(TRIGGERS)

        for _ in range(30):
            atk = rng.choice(pool)
            if atk not in used:
                used.add(atk)
                break

        cooldown = None if trigger in ("always", "first_strike") else rng.choice([None, 2, 3, 4, 5])

        patterns.append({
            "name": atk,
            "trigger": trigger,
            "description": f"{atk}으로 공격한다.",
            "damage_type": dmg,
            "cooldown": cooldown,
        })

    return patterns


def gen_survival(weaknesses: list[str], rng: random.Random) -> str:
    tmpl = rng.choice(SURVIVAL_TEMPLATES)
    return tmpl.format(
        weakness=weaknesses[0] if weaknesses else "물리",
        tip=rng.choice(TIPS),
        strategy=rng.choice(STRATEGIES),
    )


def gen_warnings(grade: str, rng: random.Random) -> list[str]:
    num = rng.randint(1, 2) if grade in ("9급", "8급") else rng.randint(2, 3)
    return rng.sample(WARNING_POOL, min(num, len(WARNING_POOL)))


def gen_lore(rng: random.Random) -> str:
    tmpl = rng.choice(LORE_TEMPLATES)
    fills = {k: rng.choice(v) for k, v in LORE_FILLS.items()}
    return tmpl.format(**fills)


def gen_id(title: str, grade: str) -> str:
    clean = re.sub(r'[^\w가-힣]', '_', title.lower())
    grade_num = grade.replace('급', '').replace('특', 'special')
    return f"beast_d_{clean}_{grade_num}"


def generate_beast(
    grade: str,
    rng: random.Random,
    existing_names: set[str],
    validator: BeastValidatorAgent | None,
) -> BeastEntry | None:
    """단일 괴수 생성 → BeastEntry 반환"""
    tier = (
        "low" if grade in ("8급", "9급") else
        "mid" if grade in ("6급", "7급") else
        "high" if grade in ("4급", "5급") else
        "elite"
    )
    species = weighted_choice(rng, ALL_SPECIES, SPECIES_WEIGHTS[tier])
    name = gen_name(species, grade, rng, existing_names)
    element = rng.choice(SPECIES_ELEMENTS.get(species, ["물리"]))
    weaknesses = list(rng.choice(SPECIES_WEAKNESSES.get(species, [["물리"]])))
    resistances = [r for r in rng.choice(SPECIES_RESISTANCES.get(species, [[]])) if r not in weaknesses]
    env = rng.choice(ENVIRONMENTS)
    stats = gen_stats(grade, rng)

    coin_range = COIN_RANGES[grade]
    coin_min = rng.randint(coin_range[0], (coin_range[0] + coin_range[1]) // 2)
    coin_max = rng.randint(coin_min, coin_range[1])

    tags = [grade, species] + weaknesses[:2] + [element]

    try:
        beast = BeastEntry(
            id=gen_id(name, grade),
            layer=BeastLayer.GENERATED,
            confidence=0.7,
            source="generated:claude:direct",
            volume=1,
            tags=tags,
            title=name,
            grade=grade,
            species=species,
            danger_class=DANGER_CLASS_MAP[grade],
            description=gen_description(species, grade, env, rng),
            combat_patterns=[CombatPattern(**p) for p in gen_combat_patterns(species, grade, element, rng)],
            survival_guide=gen_survival(weaknesses, rng),
            warnings=gen_warnings(grade, rng),
            lore_notes=gen_lore(rng),
            stats=BeastStats(**stats),
            weaknesses=weaknesses,
            resistances=resistances,
            coin_reward_range=(coin_min, coin_max),
        )

        if validator:
            beast = validator.fix_stats(beast)
            result = validator.validate(beast)
            if not result.is_valid:
                return None

        return beast
    except Exception:
        return None


# ===================================================================
# FILE I/O
# ===================================================================

def get_existing_names() -> set[str]:
    if not CANON_FILE.exists():
        return set()
    with open(CANON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {b["title"] for b in data.get("beasts", [])}


def append_to_canon(beasts: list[BeastEntry]) -> None:
    if not CANON_FILE.exists():
        data = {"beasts": []}
    else:
        with open(CANON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    for beast in beasts:
        d = beast.model_dump(mode="json")
        for key in ("created_at", "updated_at"):
            if key in d and d[key]:
                d[key] = str(d[key])
        data["beasts"].append(d)

    with open(CANON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ===================================================================
# MAIN
# ===================================================================

async def main():
    parser = argparse.ArgumentParser(description="괴수 직접 생성 (LLM 미사용)")
    parser.add_argument("--dry-run", action="store_true", help="분포만 출력")
    parser.add_argument("--count", type=int, default=760, help="생성할 괴수 수")
    parser.add_argument("--no-pinecone", action="store_true", help="Pinecone 저장 안 함")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # Build grade queue proportionally
    total_in_dist = sum(GRADE_DISTRIBUTION.values())
    grade_queue: list[str] = []
    for grade, count in GRADE_DISTRIBUTION.items():
        adjusted = round(count * args.count / total_in_dist)
        grade_queue.extend([grade] * adjusted)
    while len(grade_queue) < args.count:
        grade_queue.append(rng.choice(list(GRADE_DISTRIBUTION.keys())))
    grade_queue = grade_queue[:args.count]
    rng.shuffle(grade_queue)

    print(f"\n{'='*60}")
    print(f"  괴수 직접 생성 ({args.count}마리, LLM 미사용)")
    print(f"{'='*60}")

    if args.dry_run:
        gc = Counter(grade_queue)
        for g in ["9급", "8급", "7급", "6급", "5급", "4급", "3급", "2급", "1급", "특급"]:
            bar = "#" * gc.get(g, 0)
            print(f"  {g:4s}: {gc.get(g, 0):3d} {bar}")
        print(f"\n  총: {sum(gc.values())}마리")
        print(f"  --dry-run: 실제 생성하지 않음")
        return

    # Dependencies
    validator = get_validator()
    pinecone_repo = get_pinecone_repository() if not args.no_pinecone else None
    existing_names = get_existing_names()

    print(f"  기존 괴수: {len(existing_names)}마리")
    if pinecone_repo:
        print(f"  Pinecone 카운트: {pinecone_repo.count()}")

    # Generate
    generated: list[BeastEntry] = []
    failed = 0
    start_time = time.time()

    for i, grade in enumerate(grade_queue):
        beast = generate_beast(grade, rng, existing_names, validator)
        if beast is None:
            # Retry once
            beast = generate_beast(grade, rng, existing_names, validator)
        if beast:
            generated.append(beast)

            # Pinecone upload
            if pinecone_repo:
                try:
                    pinecone_repo.add_beast(beast)
                except Exception as e:
                    print(f"    ! Pinecone 실패: {beast.title} - {e}")
        else:
            failed += 1

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            print(f"  [{i+1}/{args.count}] {len(generated)}마리 생성 ({elapsed:.0f}s)")

    # Save to canon_beasts.json
    if generated:
        append_to_canon(generated)

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  생성 완료!")
    print(f"  소요 시간: {elapsed:.1f}s")
    print(f"  성공: {len(generated)}마리 / 실패: {failed}마리")
    print(f"  기존 + 신규: {len(existing_names)}마리")
    if pinecone_repo:
        print(f"  Pinecone 카운트: {pinecone_repo.count()}")
    print(f"{'='*60}")

    # Grade distribution
    gc = Counter(b.grade for b in generated)
    print(f"\n  === 신규 등급 분포 ===")
    for g in ["9급", "8급", "7급", "6급", "5급", "4급", "3급", "2급", "1급", "특급"]:
        cnt = gc.get(g, 0)
        bar = "#" * min(cnt, 60)
        print(f"  {g:4s}: {cnt:3d} {bar}")

    # Species distribution
    sc = Counter(b.species for b in generated)
    print(f"\n  === 신규 종 분포 ===")
    for sp, cnt in sc.most_common():
        print(f"  {sp}: {cnt}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
