"""
Notion → JSON 변환 스크립트

Notion MCP 도구를 통해 가져온 데이터를 파싱하여
data/ 폴더에 JSON 파일로 저장한다.

이 스크립트는 직접 실행하지 않고, 서비스의 seed 엔드포인트에서
Notion MCP fetch 결과를 받아 파싱하는 유틸리티로 사용한다.

Usage:
    서버의 POST /api/run/seed 엔드포인트 호출 시 내부적으로 사용됨
"""
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Notion 페이지 ID 매핑
NOTION_PAGES = {
    "root": "32a8114296a980708e8fe32758218851",
    "worldbuilding": "32a8114296a9817289b9d74119312e54",
    "events": "32a8114296a981958234e95346d113e1",
    "characters": "32a8114296a98134b23ed423674840e1",
    "concepts": "3358114296a98180a3d3c10c111516e7",
}


def parse_worldbuilding(markdown: str) -> list[dict]:
    """세계관 페이지를 섹션별 WorldSetting으로 파싱"""
    settings = []
    current_h1 = ""
    current_h2 = ""
    current_content_lines: list[str] = []
    order = 0

    def flush():
        nonlocal order
        if current_h2 and current_content_lines:
            content = "\n".join(current_content_lines).strip()
            if content:
                setting_id = f"run_ws_{_slugify(current_h2)}"
                category = _categorize_setting(current_h1, current_h2)
                settings.append({
                    "id": setting_id,
                    "entity_type": "world_setting",
                    "title": current_h2,
                    "content": content,
                    "category": category,
                    "tags": [category, current_h1] if current_h1 != current_h2 else [category],
                    "sub_items": _extract_sub_items(content),
                    "order": order,
                })
                order += 1

    for line in markdown.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            flush()
            current_h1 = line[2:].strip()
            current_h2 = current_h1
            current_content_lines = []
        elif line.startswith("## "):
            flush()
            current_h2 = line[3:].strip()
            current_content_lines = []
        elif line.strip() == "---":
            flush()
            current_content_lines = []
        else:
            current_content_lines.append(line)

    flush()
    return settings


def parse_characters(markdown: str) -> list[dict]:
    """인물 페이지를 Character 엔티티로 파싱"""
    characters = []
    sections = re.split(r"\n# (?!인물)", markdown)

    for section in sections:
        if not section.strip() or "인물 데이터베이스" in section[:30] or "데이터베이스" in section[:30]:
            continue

        lines = section.strip().split("\n")
        title = lines[0].strip().rstrip("#").strip()
        if title.startswith("# "):
            title = title[2:]

        # (본명 미상) 등 괄호 제거하여 깔끔한 이름
        clean_title = re.sub(r"\s*\(.*?\)\s*$", "", title).strip()

        char_data = {
            "id": f"run_char_{_slugify(clean_title)}",
            "entity_type": "character",
            "title": clean_title,
            "content": "\n".join(lines[1:]).strip(),
            "role": "",
            "traits": [],
            "abilities": [],
            "affiliations": [],
            "timeline": [],
            "status": "",
            "tags": [],
        }

        # 기본 정보 파싱
        in_basic = False
        in_timeline = False

        for line in lines[1:]:
            stripped = line.strip()

            if "## 기본 정보" in stripped:
                in_basic = True
                in_timeline = False
                continue
            elif "## 사건 연표" in stripped:
                in_basic = False
                in_timeline = True
                continue
            elif stripped.startswith("## "):
                in_basic = False
                in_timeline = False
                continue

            if in_basic and stripped.startswith("- **"):
                key, _, value = stripped[2:].partition("**: ")
                key = key.strip("*").strip()
                value = value.strip()

                if key == "직업":
                    char_data["role"] = value
                elif key in ("외모", "신체 특징", "이미지", "성격", "특징"):
                    char_data["traits"].append(value)
                elif key == "능력":
                    char_data["abilities"] = [a.strip() for a in value.split(",")]
                elif key in ("전 소속", "소속", "근무지"):
                    char_data["affiliations"].append(value)
                elif key in ("상태", "현재 상태"):
                    char_data["status"] = value
                elif key in ("보이스", "동기", "정체", "성별", "기록", "기억 데이터",
                             "신체 위치", "소유 변동", "외모", "음악", "정보 가치",
                             "신념", "유산", "경호", "활동 범위", "거주지"):
                    char_data["traits"].append(f"{key}: {value}")

            elif in_timeline and re.match(r"^\d+\.", stripped):
                event_text = re.sub(r"^\d+\.\s*", "", stripped)
                char_data["timeline"].append(event_text)

        # 태그 생성
        if char_data["role"]:
            char_data["tags"].append(char_data["role"].split("/")[0].split(",")[0].split("(")[0].strip())
        for aff in char_data["affiliations"]:
            char_data["tags"].append(aff)

        characters.append(char_data)

    return characters


def parse_events(markdown: str) -> list[dict]:
    """사건 페이지를 Event 엔티티로 파싱"""
    events = []
    current_period = ""
    current_event_title = ""
    current_content_lines: list[str] = []
    order = 0

    def flush():
        nonlocal order
        if current_event_title and current_content_lines:
            content = "\n".join(current_content_lines).strip()
            if content:
                event_id = f"run_evt_{order:03d}_{_slugify(current_event_title)}"
                events.append({
                    "id": event_id,
                    "entity_type": "event",
                    "title": current_event_title,
                    "content": content,
                    "time_period": current_period,
                    "location": _extract_location(content),
                    "participants": _extract_participants(content),
                    "concepts_used": [],
                    "outcome": _extract_outcome(content),
                    "order_index": order,
                    "tags": [current_period] if current_period else [],
                })
                order += 1

    for line in markdown.split("\n"):
        stripped = line.strip()

        if stripped.startswith("# ") and not stripped.startswith("## "):
            h1 = stripped[2:].strip()
            if h1 in ("사건 타임라인",):
                continue
            flush()
            current_period = _normalize_period(h1)
            current_content_lines = []
            current_event_title = ""

        elif stripped.startswith("## "):
            flush()
            raw_title = stripped[3:].strip()
            # [1], [2] 등의 번호 제거
            current_event_title = re.sub(r"^\\\[(\d+)\\\]\s*", "", raw_title)
            current_event_title = re.sub(r"^\[(\d+)\]\s*", "", current_event_title)
            current_content_lines = []

        elif stripped == "---":
            flush()
            current_content_lines = []
            current_event_title = ""

        else:
            current_content_lines.append(line)

    flush()
    return events


def parse_concept(title: str, markdown: str, source_url: str) -> dict:
    """개별 개념 페이지를 Concept 엔티티로 파싱"""
    definition = ""
    purpose = ""
    world_position = ""
    current_section = ""

    for line in markdown.split("\n"):
        stripped = line.strip()

        if stripped.startswith("## 정의"):
            current_section = "definition"
            continue
        elif stripped.startswith("## 왜 존재하는가"):
            current_section = "purpose"
            continue
        elif stripped.startswith("## 세계에서의 위치") or stripped.startswith("## 세계에서의 윂치"):
            current_section = "world_position"
            continue
        elif stripped.startswith("## "):
            current_section = ""
            continue

        if current_section == "definition":
            definition += line + "\n"
        elif current_section == "purpose":
            purpose += line + "\n"
        elif current_section == "world_position":
            world_position += line + "\n"

    # 아이콘 제거
    clean_title = re.sub(r"^[^\w가-힣]+", "", title).strip()

    return {
        "id": f"run_concept_{_slugify(clean_title)}",
        "entity_type": "concept",
        "title": clean_title,
        "content": markdown.strip(),
        "definition": definition.strip(),
        "purpose": purpose.strip(),
        "world_position": world_position.strip(),
        "related_concepts": [],
        "tags": _extract_concept_tags(clean_title, definition),
        "source_url": source_url,
    }


# === 헬퍼 함수 ===

def _slugify(text: str) -> str:
    """한글/영문 슬러그 생성"""
    text = re.sub(r"[^\w가-힣\s]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text.lower()[:50]


def _categorize_setting(h1: str, h2: str) -> str:
    """세계관 섹션 카테고리 분류"""
    text = f"{h1} {h2}"
    if any(k in text for k in ("기술", "바늘", "수면", "활강", "의안", "신체", "커넥톰")):
        return "기술"
    elif any(k in text for k in ("조직", "런", "염적", "노르드", "SFI")):
        return "조직"
    elif any(k in text for k in ("장소", "잔상", "페르디도", "영종도")):
        return "장소"
    elif any(k in text for k in ("토큰", "메모리얼", "기억세", "경제")):
        return "경제"
    elif any(k in text for k in ("오펀", "보이스", "문장 공간")):
        return "핵심개념"
    return "사회"


def _extract_sub_items(content: str) -> list[dict]:
    """마크다운 리스트에서 하위 항목 추출"""
    items = []
    for line in content.split("\n"):
        match = re.match(r"^- \*\*(.+?)\*\*:\s*(.+)", line.strip())
        if match:
            items.append({"name": match.group(1), "description": match.group(2)})
    return items


def _normalize_period(h1: str) -> str:
    """시간대 정규화"""
    if "원과거" in h1:
        return "원과거"
    elif "근과거" in h1:
        return "근과거"
    elif "미해결" in h1:
        return "미해결"
    elif "현재" in h1 or "날" in h1:
        return "현재_날1"
    return h1


def _extract_location(content: str) -> str:
    """사건 내용에서 장소 추출"""
    for line in content.split("\n"):
        if "장소:" in line or "장소 :" in line:
            return line.split(":", 1)[1].strip()
    return ""


def _extract_participants(content: str) -> list[str]:
    """사건 내용에서 참여자 추출"""
    for line in content.split("\n"):
        if "참여자:" in line or "참여자 :" in line:
            names = line.split(":", 1)[1].strip()
            return [n.strip() for n in names.split(",")]
    return []


def _extract_outcome(content: str) -> str:
    """사건 내용에서 결과/의미 추출"""
    for line in content.split("\n"):
        if any(k in line for k in ("의미:", "결과:", "특이점:", "핵심 정보:")):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_concept_tags(title: str, definition: str) -> list[str]:
    """개념에서 태그 추출"""
    tags = []
    keywords = ["커넥톰", "기억", "오펀", "문장 공간", "바늘", "보이스", "신체", "경매", "법"]
    text = f"{title} {definition}"
    for kw in keywords:
        if kw in text:
            tags.append(kw)
    return tags


def save_json(data: dict | list, filename: str) -> Path:
    """JSON 파일 저장"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return filepath
