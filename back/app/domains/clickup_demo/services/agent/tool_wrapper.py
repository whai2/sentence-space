"""Tool Response Filtering Wrapper

MCP 도구의 응답을 필터링하여 토큰 사용량을 대폭 줄입니다.
"""

import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import BaseTool, ToolException


class CompactToolWrapper:
    """도구 응답을 압축하여 토큰 사용량을 줄이는 래퍼"""

    # 태스크에서 유지할 필수 필드만 선택
    TASK_ESSENTIAL_FIELDS = {
        "id",
        "custom_id",
        "name",
        "status",
        "assignees",
        "priority",
        "due_date",
        "url",
        "description",
    }

    # Assignee에서 유지할 필드
    ASSIGNEE_FIELDS = {"id", "username", "email"}

    # Status에서 유지할 필드
    STATUS_FIELDS = {"status", "color", "type"}

    @classmethod
    def _compact_assignee(cls, assignee: Dict[str, Any]) -> Dict[str, Any]:
        """Assignee 정보를 압축"""
        return {k: v for k, v in assignee.items() if k in cls.ASSIGNEE_FIELDS}

    @classmethod
    def _compact_status(cls, status: Dict[str, Any]) -> Dict[str, Any]:
        """Status 정보를 압축"""
        return {k: v for k, v in status.items() if k in cls.STATUS_FIELDS}

    @classmethod
    def _compact_task(cls, task: Dict[str, Any]) -> Dict[str, Any]:
        """태스크 정보를 필수 필드만 남기고 압축"""
        compact = {}

        for field in cls.TASK_ESSENTIAL_FIELDS:
            if field in task:
                value = task[field]

                # Assignees 압축
                if field == "assignees" and isinstance(value, list):
                    compact[field] = [cls._compact_assignee(a) for a in value]
                # Status 압축
                elif field == "status" and isinstance(value, dict):
                    compact[field] = cls._compact_status(value)
                # 기타 필드는 그대로
                else:
                    compact[field] = value

        return compact

    @classmethod
    def filter_response(cls, tool_name: str, response: str) -> str:
        """도구 응답을 필터링하여 토큰 사용량 줄이기

        Args:
            tool_name: 도구 이름
            response: 원본 응답

        Returns:
            필터링된 응답
        """
        try:
            # ClickUp 태스크 리스트 응답 감지 및 필터링
            if "Retrieved" in response and ("tasks" in response.lower() or "Details:" in response):
                # "Details: [...]" 패턴에서 JSON 추출
                import re
                json_match = re.search(r'Details:\s*(\[[\s\S]*\])', response)
                if json_match:
                    try:
                        tasks = json.loads(json_match.group(1))
                        if isinstance(tasks, list) and len(tasks) > 0:
                            # 태스크 압축
                            compact_tasks = [cls._compact_task(task) for task in tasks]

                            # 원본 크기 vs 압축 크기
                            original_size = len(response)
                            compact_json = json.dumps(compact_tasks, ensure_ascii=False)
                            new_size = len(compact_json)

                            # 요약 정보 생성
                            summary = f"Retrieved {len(compact_tasks)} tasks (compressed {original_size} → {new_size} bytes, -{round((1-new_size/original_size)*100)}%).\n"
                            summary += compact_json
                            return summary
                    except json.JSONDecodeError as e:
                        print(f"JSON parsing failed: {e}")

            # 응답이 너무 길면 (5KB 이상) 필터링 시도
            if len(response) > 5000:
                # JSON 파싱 시도
                try:
                    data = json.loads(response)
                    if isinstance(data, list) and len(data) > 0:
                        # 리스트인 경우 각 항목 압축
                        if isinstance(data[0], dict):
                            compact = [cls._compact_task(item) for item in data]
                            compact_json = json.dumps(compact, ensure_ascii=False)
                            return f"Compressed response ({len(response)} → {len(compact_json)} bytes):\n{compact_json}"
                    elif isinstance(data, dict):
                        # 단일 객체인 경우 압축
                        compact_json = json.dumps(cls._compact_task(data), ensure_ascii=False)
                        return f"Compressed response ({len(response)} → {len(compact_json)} bytes):\n{compact_json}"
                except json.JSONDecodeError:
                    # JSON이 아니면 길이 제한
                    return response[:5000] + f"\n\n[응답이 너무 길어 {len(response) - 5000}자 생략됨]"

            return response

        except Exception as e:
            # 필터링 실패 시 원본 반환
            print(f"Response filtering failed: {e}")
            return response

    @classmethod
    def wrap_tool(cls, tool: BaseTool) -> BaseTool:
        """도구를 래핑하여 응답 필터링 적용

        Args:
            tool: 원본 도구

        Returns:
            필터링이 적용된 도구
        """
        # StructuredTool은 _run과 _arun을 오버라이드
        # (Pydantic 모델이므로 invoke/ainvoke를 직접 할당할 수 없음)

        # 동기 함수 래핑
        if hasattr(tool, "_run"):
            original_run = tool._run

            def filtered_run(*args, **kwargs):
                result = original_run(*args, **kwargs)
                if isinstance(result, str):
                    return cls.filter_response(tool.name, result)
                return result

            # __dict__를 통해 직접 설정 (Pydantic 검증 우회)
            object.__setattr__(tool, "_run", filtered_run)

        # 비동기 함수 래핑
        if hasattr(tool, "_arun"):
            original_arun = tool._arun

            async def filtered_arun(*args, **kwargs):
                result = await original_arun(*args, **kwargs)
                if isinstance(result, str):
                    return cls.filter_response(tool.name, result)
                return result

            # __dict__를 통해 직접 설정 (Pydantic 검증 우회)
            object.__setattr__(tool, "_arun", filtered_arun)

        return tool

    @classmethod
    def wrap_tools(cls, tools: List[BaseTool]) -> List[BaseTool]:
        """여러 도구를 한번에 래핑

        Args:
            tools: 도구 리스트

        Returns:
            필터링이 적용된 도구 리스트
        """
        return [cls.wrap_tool(tool) for tool in tools]
