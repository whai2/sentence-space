# ClickUp Demo with LangGraph

LangChain MCP Adapters를 사용한 ClickUp MCP 서버 통합 에이전트입니다.

## 설정 방법

### 1. ClickUp API Key 발급

1. ClickUp 설정 페이지로 이동: https://app.clickup.com/settings/apps
2. "Apps" 섹션에서 "API Token" 생성
3. 생성된 토큰을 복사
4. ClickUp에서 Team ID 확인 (워크스페이스 설정에서 확인 가능)

### 2. Node.js 설치 확인

MCP 서버는 Node.js를 사용하므로 Node.js가 설치되어 있어야 합니다:

```bash
node --version  # v16 이상 권장
```

### 3. 환경 변수 설정

`.env` 파일에 다음을 추가:

```bash
# ClickUp 설정
CLICKUP_API_KEY=your_api_key_here
CLICKUP_TEAM_ID=your_team_id_here
```

### 4. 사용 가능한 도구

ClickUp MCP 서버는 다음과 같은 작업을 지원합니다:

- **워크스페이스 조회**: 팀, 스페이스, 폴더, 리스트 계층 구조 조회
- **작업 관리**:
  - 작업 조회 및 검색
  - 작업 생성, 수정, 삭제
  - 작업 상태 및 우선순위 변경
  - 담당자 할당
- **고급 기능**:
  - 사용자 정보 조회
  - 작업 코멘트 추가
  - 커스텀 필드 관리

## 사용 예시

```python
from app.domains.clickup_demo.services.clickup_chat_service import ClickUpChatService

service = ClickUpChatService()

# 작업 조회
response = service.chat("내 스페이스에 있는 모든 작업을 보여줘", thread_id="user_123")

# 작업 생성
response = service.chat(
    "새 작업을 만들어줘: 'API 문서 작성', 리스트 ID는 123456789",
    thread_id="user_123"
)

# 작업 업데이트
response = service.chat(
    "작업 987654321의 상태를 'in progress'로 변경해줘",
    thread_id="user_123"
)
```

## 주의사항

- ClickUp API는 rate limiting이 있으므로 과도한 요청은 피하세요
- Access token은 일정 기간 후 만료될 수 있으므로 갱신이 필요할 수 있습니다
- OAuth 앱을 사용하는 경우, 토큰 갱신 로직을 구현해야 합니다

## 공식 문서

- [LangChain ClickUp Toolkit](https://docs.langchain.com/oss/python/integrations/tools/clickup)
- [ClickUp API Documentation](https://clickup.com/api)
