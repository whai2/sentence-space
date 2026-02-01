"""ClickUp MCP Tool Result Summarizer

도구 실행 결과를 요약하여 LLM이 중요한 정보(ID, name 등)를 놓치지 않도록 합니다.
"""

import json
from typing import Any, Dict, List, Union


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
            # JSON이 아니면 길이 제한만 적용
            return _truncate_string_result(result)

    # 도구별 요약 전략
    if tool_name == "clickup_get_spaces":
        return _summarize_spaces(result)
    elif tool_name == "clickup_get_teams":
        return _summarize_teams(result)
    elif tool_name == "clickup_get_folders":
        return _summarize_folders(result)
    elif tool_name == "clickup_get_lists":
        return _summarize_lists(result)
    elif tool_name == "clickup_search_docs":
        return _summarize_docs(result)
    elif tool_name == "clickup_get_doc_pages":
        return _summarize_doc_pages(result)
    elif tool_name == "clickup_get_doc_page_content":
        return _summarize_doc_page_content(result)
    elif tool_name == "clickup_create_doc":
        return _summarize_created_doc(result)
    elif tool_name == "clickup_create_doc_page":
        return _summarize_created_doc_page(result)
    elif tool_name == "clickup_create_task":
        return _summarize_created_task(result)
    elif tool_name == "clickup_update_task":
        return _summarize_updated_task(result)
    elif tool_name == "clickup_get_views":
        return _summarize_views(result)
    elif tool_name == "clickup_create_space":
        return _summarize_created_space(result)
    elif tool_name == "clickup_get_space":
        return _summarize_space_detail(result)
    elif tool_name == "clickup_create_folder":
        return _summarize_created_folder(result)
    elif tool_name == "clickup_create_list":
        return _summarize_created_list(result)
    else:
        # 기본 요약: 중요 필드만 추출
        return _summarize_default(result)


def _summarize_spaces(result: Any) -> str:
    """Spaces 목록 요약"""
    if not isinstance(result, list):
        return _summarize_default(result)

    spaces_info = []
    for space in result[:20]:  # 최대 20개만
        if isinstance(space, dict):
            spaces_info.append({
                "id": space.get("id"),
                "name": space.get("name"),
                "private": space.get("private", False),
            })

    summary = f"✅ {len(result)}개의 스페이스를 찾았습니다.\n\n"
    summary += "**주요 스페이스 목록 (ID와 이름):**\n"
    for space in spaces_info:
        summary += f"- ID: `{space['id']}`, 이름: \"{space['name']}\", 공개: {not space['private']}\n"

    if len(result) > 20:
        summary += f"\n... 외 {len(result) - 20}개 스페이스"

    return summary


def _summarize_teams(result: Any) -> str:
    """Teams 목록 요약"""
    if not isinstance(result, dict) or "teams" not in result:
        return _summarize_default(result)

    teams = result.get("teams", [])
    teams_info = []
    for team in teams[:10]:
        if isinstance(team, dict):
            teams_info.append({
                "id": team.get("id"),
                "name": team.get("name"),
            })

    summary = f"✅ {len(teams)}개의 팀을 찾았습니다.\n\n"
    summary += "**팀 목록 (ID와 이름):**\n"
    for team in teams_info:
        summary += f"- Team ID: `{team['id']}`, 이름: \"{team['name']}\"\n"

    return summary


def _summarize_folders(result: Any) -> str:
    """Folders 목록 요약"""
    if not isinstance(result, dict) or "folders" not in result:
        return _summarize_default(result)

    folders = result.get("folders", [])
    folders_info = []
    for folder in folders[:20]:
        if isinstance(folder, dict):
            folders_info.append({
                "id": folder.get("id"),
                "name": folder.get("name"),
                "hidden": folder.get("hidden", False),
            })

    summary = f"✅ {len(folders)}개의 폴더를 찾았습니다.\n\n"
    summary += "**폴더 목록 (ID와 이름):**\n"
    for folder in folders_info:
        status = "숨김" if folder['hidden'] else "표시"
        summary += f"- ID: `{folder['id']}`, 이름: \"{folder['name']}\" ({status})\n"

    if len(folders) > 20:
        summary += f"\n... 외 {len(folders) - 20}개 폴더"

    return summary


def _summarize_lists(result: Any) -> str:
    """Lists 목록 요약"""
    if not isinstance(result, dict) or "lists" not in result:
        return _summarize_default(result)

    lists = result.get("lists", [])
    lists_info = []
    for lst in lists[:20]:
        if isinstance(lst, dict):
            lists_info.append({
                "id": lst.get("id"),
                "name": lst.get("name"),
            })

    summary = f"✅ {len(lists)}개의 리스트를 찾았습니다.\n\n"
    summary += "**리스트 목록 (ID와 이름):**\n"
    for lst in lists_info:
        summary += f"- List ID: `{lst['id']}`, 이름: \"{lst['name']}\"\n"

    if len(lists) > 20:
        summary += f"\n... 외 {len(lists) - 20}개 리스트"

    return summary


def _summarize_docs(result: Any) -> str:
    """Docs 검색 결과 요약"""
    if not isinstance(result, dict) or "docs" not in result:
        return _summarize_default(result)

    docs = result.get("docs", [])
    docs_info = []
    for doc in docs[:15]:
        if isinstance(doc, dict):
            docs_info.append({
                "id": doc.get("id"),
                "name": doc.get("name"),
                "creator": doc.get("creator", {}).get("username", "알 수 없음"),
            })

    summary = f"✅ {len(docs)}개의 문서를 찾았습니다.\n\n"
    summary += "**문서 목록 (ID와 이름):**\n"
    for doc in docs_info:
        summary += f"- Doc ID: `{doc['id']}`, 제목: \"{doc['name']}\", 작성자: {doc['creator']}\n"

    if len(docs) > 15:
        summary += f"\n... 외 {len(docs) - 15}개 문서"

    return summary


def _summarize_doc_pages(result: Any) -> str:
    """Doc Pages 목록 요약"""
    if not isinstance(result, dict) or "pages" not in result:
        return _summarize_default(result)

    pages = result.get("pages", [])
    pages_info = []
    for page in pages[:15]:
        if isinstance(page, dict):
            pages_info.append({
                "id": page.get("id"),
                "name": page.get("name"),
            })

    summary = f"✅ {len(pages)}개의 페이지를 찾았습니다.\n\n"
    summary += "**페이지 목록 (ID와 제목):**\n"
    for page in pages_info:
        summary += f"- Page ID: `{page['id']}`, 제목: \"{page['name']}\"\n"

    if len(pages) > 15:
        summary += f"\n... 외 {len(pages) - 15}개 페이지"

    return summary


def _summarize_doc_page_content(result: Any) -> str:
    """Doc Page 내용 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    content = result.get("content", "")
    name = result.get("name", "제목 없음")

    # 내용 길이 제한 (1000자)
    content_preview = content[:1000] if len(content) > 1000 else content
    truncated = len(content) > 1000

    summary = f"✅ 페이지 내용을 가져왔습니다.\n\n"
    summary += f"**페이지 제목:** \"{name}\"\n"
    summary += f"**내용 길이:** {len(content)}자\n\n"
    summary += "**내용 미리보기:**\n```\n{}\n```".format(content_preview)

    if truncated:
        summary += f"\n\n... (총 {len(content)}자 중 1000자만 표시)"

    return summary


def _summarize_created_doc(result: Any) -> str:
    """생성된 Doc 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    doc_id = result.get("id")
    name = result.get("name", "제목 없음")

    summary = f"✅ 문서가 생성되었습니다.\n\n"
    summary += f"- **Doc ID:** `{doc_id}`\n"
    summary += f"- **제목:** \"{name}\"\n"

    return summary


def _summarize_created_doc_page(result: Any) -> str:
    """생성된 Doc Page 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    page_id = result.get("id")
    name = result.get("name", "제목 없음")

    summary = f"✅ 페이지가 생성되었습니다.\n\n"
    summary += f"- **Page ID:** `{page_id}`\n"
    summary += f"- **제목:** \"{name}\"\n"

    return summary


def _summarize_created_task(result: Any) -> str:
    """생성된 Task 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    task_id = result.get("id")
    name = result.get("name", "제목 없음")
    status = result.get("status", {}).get("status", "알 수 없음")
    url = result.get("url")

    summary = f"✅ 작업이 생성되었습니다.\n\n"
    summary += f"- **Task ID:** `{task_id}`\n"
    summary += f"- **제목:** \"{name}\"\n"
    summary += f"- **상태:** {status}\n"
    if url:
        summary += f"- **URL:** {url}\n"

    return summary


def _summarize_updated_task(result: Any) -> str:
    """업데이트된 Task 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    task_id = result.get("id")
    name = result.get("name", "제목 없음")
    status = result.get("status", {}).get("status", "알 수 없음")

    summary = f"✅ 작업이 업데이트되었습니다.\n\n"
    summary += f"- **Task ID:** `{task_id}`\n"
    summary += f"- **제목:** \"{name}\"\n"
    summary += f"- **상태:** {status}\n"

    return summary


def _summarize_views(result: Any) -> str:
    """Views 목록 요약"""
    if not isinstance(result, dict) or "views" not in result:
        return _summarize_default(result)

    views = result.get("views", [])
    views_info = []
    for view in views[:15]:
        if isinstance(view, dict):
            views_info.append({
                "id": view.get("id"),
                "name": view.get("name"),
                "type": view.get("type", "알 수 없음"),
            })

    summary = f"✅ {len(views)}개의 뷰를 찾았습니다.\n\n"
    summary += "**뷰 목록 (ID, 이름, 타입):**\n"
    for view in views_info:
        summary += f"- ID: `{view['id']}`, 이름: \"{view['name']}\", 타입: {view['type']}\n"

    if len(views) > 15:
        summary += f"\n... 외 {len(views) - 15}개 뷰"

    return summary


def _summarize_created_space(result: Any) -> str:
    """생성된 Space 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    space_id = result.get("id")
    name = result.get("name", "이름 없음")

    summary = f"✅ 스페이스가 생성되었습니다.\n\n"
    summary += f"- **Space ID:** `{space_id}`\n"
    summary += f"- **이름:** \"{name}\"\n"

    return summary


def _summarize_space_detail(result: Any) -> str:
    """Space 상세 정보 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    space_id = result.get("id")
    name = result.get("name", "이름 없음")
    private = result.get("private", False)
    statuses = result.get("statuses", [])

    summary = f"✅ 스페이스 정보를 가져왔습니다.\n\n"
    summary += f"- **Space ID:** `{space_id}`\n"
    summary += f"- **이름:** \"{name}\"\n"
    summary += f"- **공개 여부:** {'비공개' if private else '공개'}\n"
    summary += f"- **상태 개수:** {len(statuses)}개\n"

    return summary


def _summarize_created_folder(result: Any) -> str:
    """생성된 Folder 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    folder_id = result.get("id")
    name = result.get("name", "이름 없음")

    summary = f"✅ 폴더가 생성되었습니다.\n\n"
    summary += f"- **Folder ID:** `{folder_id}`\n"
    summary += f"- **이름:** \"{name}\"\n"

    return summary


def _summarize_created_list(result: Any) -> str:
    """생성된 List 요약"""
    if not isinstance(result, dict):
        return _summarize_default(result)

    list_id = result.get("id")
    name = result.get("name", "이름 없음")

    summary = f"✅ 리스트가 생성되었습니다.\n\n"
    summary += f"- **List ID:** `{list_id}`\n"
    summary += f"- **이름:** \"{name}\"\n"

    return summary


def _summarize_default(result: Any) -> str:
    """기본 요약: JSON을 축약하여 반환"""
    if isinstance(result, dict):
        # 중요 필드 우선 추출
        important_fields = ["id", "name", "title", "status", "url", "message"]
        summary_dict = {}

        for key in important_fields:
            if key in result:
                summary_dict[key] = result[key]

        # 중요 필드가 없으면 전체 dict에서 일부만
        if not summary_dict:
            # 최대 5개 필드만
            summary_dict = dict(list(result.items())[:5])

        json_str = json.dumps(summary_dict, ensure_ascii=False, indent=2)

        # 원본에 더 많은 필드가 있으면 표시
        if len(result) > len(summary_dict):
            json_str += f"\n\n... (전체 {len(result)}개 필드 중 {len(summary_dict)}개만 표시)"

        return f"✅ 요청이 성공했습니다.\n\n**주요 정보:**\n```json\n{json_str}\n```"

    elif isinstance(result, list):
        count = len(result)
        if count == 0:
            return "✅ 요청이 성공했습니다. (결과: 빈 목록)"

        # 첫 3개 항목만 표시
        preview = result[:3]
        preview_str = json.dumps(preview, ensure_ascii=False, indent=2)

        summary = f"✅ {count}개의 항목을 찾았습니다.\n\n"
        summary += f"**처음 {min(3, count)}개 항목:**\n```json\n{preview_str}\n```"

        if count > 3:
            summary += f"\n\n... 외 {count - 3}개 항목"

        return summary

    else:
        # 문자열 등 기타 타입
        return _truncate_string_result(str(result))


def _truncate_string_result(result_str: str, max_length: int = 2000) -> str:
    """문자열 결과를 길이 제한"""
    if len(result_str) <= max_length:
        return result_str

    return result_str[:max_length] + f"\n\n... (총 {len(result_str)}자 중 {max_length}자만 표시)"
