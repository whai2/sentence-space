"""MCP 도구 결과 후처리 모듈

langchain-mcp-adapters가 MCP 도구 응답을 LangChain 형식으로 변환할 때
발생하는 ID 파싱 문제를 해결합니다.
"""

import re
import json
from typing import Any, Dict, List


def extract_clickup_ids(result: Any) -> Any:
    """MCP 도구 결과에서 ClickUp ID 추출

    langchain-mcp-adapters가 반환하는 결과에서 lc_ prefix가 붙은 내부 ID를
    실제 ClickUp ID로 변환합니다.

    Args:
        result: MCP 도구 실행 결과

    Returns:
        처리된 결과 (lc_ ID 제거 및 실제 ID 추출)
    """
    if result is None:
        return None

    # 빈 문자열인 경우
    if isinstance(result, str) and not result.strip():
        return "빈 결과가 반환되었습니다."

    # 문자열인 경우
    if isinstance(result, str):
        return _process_string_result(result)

    # 딕셔너리인 경우
    elif isinstance(result, dict):
        return _process_dict_result(result)

    # 리스트인 경우
    elif isinstance(result, list):
        # 빈 리스트는 그대로 반환
        if not result:
            return []
        return [extract_clickup_ids(item) for item in result]

    # 그 외의 경우 (숫자, bool 등)
    return result


def _process_string_result(text: str) -> str:
    """문자열 결과 처리

    lc_ prefix를 제거하고 JSON 파싱을 시도합니다.
    """
    # lc_ prefix 제거
    text = re.sub(r'\blc_([a-f0-9-]+)\b', r'\1', text)

    # JSON 파싱 시도
    try:
        parsed = json.loads(text)
        return json.dumps(extract_clickup_ids(parsed), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return text


def _process_dict_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """딕셔너리 결과 처리

    재귀적으로 모든 값을 처리하고, lc_ prefix를 제거합니다.
    """
    result = {}
    for key, value in data.items():
        # 키가 'id'인 경우 lc_ prefix 제거
        if key == 'id' and isinstance(value, str) and value.startswith('lc_'):
            # lc_ prefix 제거
            value = value[3:]

        # 값 재귀 처리
        result[key] = extract_clickup_ids(value)

    return result


def enhance_space_result(result: Any) -> str:
    """Space 조회 결과 향상

    Space 조회 결과에 실제 사용 가능한 정보를 추가합니다.
    """
    if not result:
        return result

    # 문자열이면 JSON 파싱 시도
    if isinstance(result, str):
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            return result
    else:
        data = result

    # 딕셔너리 또는 리스트 처리
    if isinstance(data, dict):
        data = _enhance_space_dict(data)
    elif isinstance(data, list):
        data = [_enhance_space_dict(item) if isinstance(item, dict) else item for item in data]

    # 문자열로 반환 (원래 문자열이었으면)
    if isinstance(result, str):
        return json.dumps(data, ensure_ascii=False)
    return data


def _enhance_space_dict(space: Dict[str, Any]) -> Dict[str, Any]:
    """Space 딕셔너리 향상"""
    # id가 lc_로 시작하면 제거
    if 'id' in space and isinstance(space['id'], str) and space['id'].startswith('lc_'):
        space['id'] = space['id'][3:]

    # name이 None이거나 없으면 'name' 필드 추가
    if not space.get('name'):
        space['name'] = space.get('id', 'Unknown')

    return space


def is_valid_clickup_id(value: str) -> bool:
    """유효한 ClickUp ID인지 확인

    Args:
        value: 확인할 값

    Returns:
        숫자로만 구성되어 있으면 True
    """
    if not isinstance(value, str):
        return False
    return value.isdigit()
