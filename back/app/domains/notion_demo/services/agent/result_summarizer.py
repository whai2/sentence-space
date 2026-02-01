"""Notion MCP Tool Result Summarizer

도구 실행 결과를 요약하여 LLM이 중요한 정보(ID, name 등)를 놓치지 않도록 합니다.
"""

import json
from typing import Any


def summarize_tool_result(tool_name: str, result: Any) -> str:
    """도구 실행 결과를 요약합니다.

    Args:
        tool_name: 실행된 도구 이름
        result: 도구 실행 결과

    Returns:
        요약된 결과 문자열
    """
    # 결과가 문자열인 경우 JSON 파싱 시도
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, ValueError):
            return _truncate_string_result(result)

    # 도구별 요약 전략
    if "search" in tool_name.lower():
        return _summarize_search_results(result)
    elif "database" in tool_name.lower() and "query" in tool_name.lower():
        return _summarize_database_query(result)
    elif "page" in tool_name.lower() and "get" in tool_name.lower():
        return _summarize_page(result)
    elif "page" in tool_name.lower() and "create" in tool_name.lower():
        return _summarize_created_page(result)
    elif "block" in tool_name.lower():
        return _summarize_blocks(result)
    elif "user" in tool_name.lower():
        return _summarize_users(result)
    else:
        return _summarize_default(result)


def _summarize_search_results(result: Any) -> str:
    """검색 결과 요약"""
    if not isinstance(result, dict) or "results" not in result:
        return _summarize_default(result)

    results = result.get("results", [])
    items_info = []
    for item in results[:15]:
        if isinstance(item, dict):
            obj_type = item.get("object", "unknown")
            item_id = item.get("id", "")

            # 제목 추출
            title = "제목 없음"
            if obj_type == "page":
                properties = item.get("properties", {})
                for prop in properties.values():
                    if prop.get("type") == "title":
                        title_list = prop.get("title", [])
                        if title_list:
                            title = title_list[0].get("plain_text", "제목 없음")
                        break
            elif obj_type == "database":
                title_list = item.get("title", [])
                if title_list:
                    title = title_list[0].get("plain_text", "제목 없음")

            items_info.append({
                "id": item_id,
                "type": obj_type,
                "title": title,
            })

    summary = f"✅ {len(results)}개의 항목을 찾았습니다.\n\n"
    summary += "**검색 결과 (ID, 타입, 제목):**\n"
    for item in items_info:
        summary += f"- ID: `{item['id']}`, 타입: {item['type']}, 제목: \"{item['title']}\"\n"

    if len(results) > 15:
        summary += f"\n... 외 {len(results) - 15}개 항목"

    return summary


def _summarize_database_query(result: Any) -> str:
    """데이터베이스 쿼리 결과 요약"""
    if not isinstance(result, dict) or "results" not in result:
        return _summarize_default(result)

    results = result.get("results", [])
    rows_info = []
    for row in results[:20]:
        if isinstance(row, dict):
            row_id = row.get("id", "")
            properties = row.get("properties", {})

            # 첫 번째 title 속성 추출
            title = "제목 없음"
            for prop in properties.values():
                if prop.get("type") == "title":
                    title_list = prop.get("title", [])
                    if title_list:
                        title = title_list[0].get("plain_text", "제목 없음")
                    break

            rows_info.append({
                "id": row_id,
                "title": title,
            })

    summary = f"✅ {len(results)}개의 행을 찾았습니다.\n\n"
    summary += "**데이터베이스 행 목록 (ID와 제목):**\n"
    for row in rows_info:
        summary += f"- ID: `{row['id']}`, 제목: \"{row['title']}\"\n"

    if len(results) > 20:
        summary += f"\n... 외 {len(results) - 20}개 행"

    return summary


def _summarize_page(result: Any) -> str:
    """페이지 정보 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    page_id = result.get("id", "")
    obj_type = result.get("object", "page")
    url = result.get("url", "")

    # 제목 추출
    title = "제목 없음"
    properties = result.get("properties", {})
    for prop in properties.values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            title_list = prop.get("title", [])
            if title_list:
                title = title_list[0].get("plain_text", "제목 없음")
            break

    summary = f"✅ 페이지 정보를 가져왔습니다.\n\n"
    summary += f"- **Page ID:** `{page_id}`\n"
    summary += f"- **제목:** \"{title}\"\n"
    summary += f"- **타입:** {obj_type}\n"
    if url:
        summary += f"- **URL:** {url}\n"

    return summary


def _summarize_created_page(result: Any) -> str:
    """생성된 페이지 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    page_id = result.get("id", "")
    url = result.get("url", "")

    summary = f"✅ 페이지가 생성되었습니다.\n\n"
    summary += f"- **Page ID:** `{page_id}`\n"
    if url:
        summary += f"- **URL:** {url}\n"

    return summary


def _extract_block_content(block: dict) -> str:
    """블록에서 텍스트 내용을 추출"""
    block_type = block.get("type", "")
    type_data = block.get(block_type, {})

    # rich_text 배열에서 텍스트 추출
    if isinstance(type_data, dict):
        rich_text = type_data.get("rich_text", [])
        if rich_text:
            texts = [rt.get("plain_text", "") for rt in rich_text if isinstance(rt, dict)]
            return " ".join(texts).strip()

        # title (child_page, child_database 등)
        title = type_data.get("title", "")
        if title:
            return title

    return ""


def _summarize_blocks(result: Any) -> str:
    """블록 목록 요약"""
    if isinstance(result, dict) and "results" in result:
        blocks = result.get("results", [])
    elif isinstance(result, list):
        blocks = result
    else:
        return _summarize_default(result)

    blocks_info = []
    for block in blocks[:15]:
        if isinstance(block, dict):
            block_id = block.get("id", "")
            block_type = block.get("type", "unknown")
            content = _extract_block_content(block)
            blocks_info.append({
                "id": block_id,
                "type": block_type,
                "content": content[:100] if content else "",  # 내용 100자 제한
            })

    summary = f"✅ {len(blocks)}개의 블록을 찾았습니다.\n\n"
    summary += "**블록 목록:**\n"
    for block in blocks_info:
        content_str = f', 내용: "{block["content"]}"' if block["content"] else ""
        summary += f"- ID: `{block['id']}`, 타입: {block['type']}{content_str}\n"

    if len(blocks) > 15:
        summary += f"\n... 외 {len(blocks) - 15}개 블록"

    return summary


def _summarize_users(result: Any) -> str:
    """사용자 정보 요약"""
    if isinstance(result, dict) and "results" in result:
        users = result.get("results", [])
    elif isinstance(result, list):
        users = result
    elif isinstance(result, dict) and "id" in result:
        users = [result]
    else:
        return _summarize_default(result)

    users_info = []
    for user in users[:10]:
        if isinstance(user, dict):
            user_id = user.get("id", "")
            name = user.get("name", "이름 없음")
            user_type = user.get("type", "unknown")
            users_info.append({
                "id": user_id,
                "name": name,
                "type": user_type,
            })

    summary = f"✅ {len(users)}명의 사용자를 찾았습니다.\n\n"
    summary += "**사용자 목록 (ID, 이름, 타입):**\n"
    for user in users_info:
        summary += f"- ID: `{user['id']}`, 이름: \"{user['name']}\", 타입: {user['type']}\n"

    return summary


def _summarize_default(result: Any) -> str:
    """기본 요약: JSON을 축약하여 반환"""
    if isinstance(result, dict):
        important_fields = ["id", "name", "title", "object", "type", "url", "message"]
        summary_dict = {}

        for key in important_fields:
            if key in result:
                summary_dict[key] = result[key]

        if not summary_dict:
            summary_dict = dict(list(result.items())[:5])

        json_str = json.dumps(summary_dict, ensure_ascii=False, indent=2)

        if len(result) > len(summary_dict):
            json_str += f"\n\n... (전체 {len(result)}개 필드 중 {len(summary_dict)}개만 표시)"

        return f"✅ 요청이 성공했습니다.\n\n**주요 정보:**\n```json\n{json_str}\n```"

    elif isinstance(result, list):
        count = len(result)
        if count == 0:
            return "✅ 요청이 성공했습니다. (결과: 빈 목록)"

        preview = result[:3]
        preview_str = json.dumps(preview, ensure_ascii=False, indent=2)

        summary = f"✅ {count}개의 항목을 찾았습니다.\n\n"
        summary += f"**처음 {min(3, count)}개 항목:**\n```json\n{preview_str}\n```"

        if count > 3:
            summary += f"\n\n... 외 {count - 3}개 항목"

        return summary

    else:
        return _truncate_string_result(str(result))


def _truncate_string_result(result_str: str, max_length: int = 2000) -> str:
    """문자열 결과를 길이 제한"""
    if len(result_str) <= max_length:
        return result_str

    return result_str[:max_length] + f"\n\n... (총 {len(result_str)}자 중 {max_length}자만 표시)"
