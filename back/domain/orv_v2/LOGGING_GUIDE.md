# GraphRAG 로깅 가이드

프론트엔드 API가 GraphRAG를 실제로 사용하는지 확인하기 위한 로깅 시스템이 구축되었습니다.

## 로깅 아키텍처

전체 요청 흐름에 걸쳐 로깅이 추가되었습니다:

```
Frontend → API → Service → Workflow → GraphRAG/StoryPlanner
            ↓       ↓          ↓            ↓
          로깅    로깅       로깅         로깅
```

## 로깅이 추가된 파일들

### 1. API Layer
- **`routes/game_routes.py`**
  - `POST /sessions/{session_id}/continue` (Auto-Narrative)
  - `POST /sessions/{session_id}/actions` (Interactive)
  - 로그 형식: `📥 [API] POST /sessions/{session_id}/continue 호출됨`

### 2. Service Layer
- **`service/game_service.py`**
  - `process_action()` - 플레이어 행동 처리
  - `continue_auto_narrative()` - 자동 스토리 진행
  - 로그 형식: `🎮 [GameService] 플레이어 행동 처리`

### 3. Workflow Layer
- **`graph/workflow.py`**
  - `run_turn()` - 턴 실행 진입점
  - `_load_state()` - 게임 상태 로드
  - `_auto_narrative_node()` - Auto-Narrative 노드
  - **GraphRAG 호출 지점**: `🔍 [Workflow] GraphRAG 호출: scenario_id=xxx`
  - **StoryPlanner 호출 지점**: `📋 [Workflow] StoryPlanner 호출...`

### 4. Agent Layer

#### GraphRAG Retriever (`agents/graph_rag_retriever.py`)
- `retrieve_scenario_knowledge()` - 시나리오 지식 검색
- 로그 예시:
  ```
  🔍 [GraphRAG] 시나리오 지식 검색 시작: scenario_id=scenario_1, phase=active, remaining_time=15
  ✅ [GraphRAG] Neo4j 데이터 조회 완료: scenario_title=가치 증명
     - 캐릭터 데이터: 5개
     - 주인공 트릭 조회: 3개
     - 대안 솔루션 조회: 2개
  🎯 [GraphRAG] 시나리오 컨텍스트 생성 완료:
     - 캐릭터: 5개, 위치: 3개
     - 승리조건: 1개, 실패조건: 1개
     - 주인공 트릭: 3개, 대안 솔루션: 2개
     - 서술 힌트: 2개
  ```

#### Story Planner (`agents/story_planner.py`)
- `create_story_plan()` - 스토리 플랜 생성
- 로그 예시:
  ```
  📋 [StoryPlanner] 스토리 플랜 생성 시작: scenario_id=scenario_1
     - 시나리오: 가치 증명
     - Neo4j 데이터: Phase=7, Character=5, Event=10, Trick=3
  🤖 [StoryPlanner] LLM 호출 중... (model=gpt-4o)
  ✅ [StoryPlanner] 스토리 플랜 생성 완료
     - Phases: 7개
     - Initial Choices: 3개
  ```

## 로그 확인 방법

### 방법 1: 테스트 스크립트 실행

```bash
cd /Users/no-eunsu/hobby/sentence-space/back
python -m domain.orv_v2.scripts.test_graphrag_logging
```

이 스크립트는:
1. 새 게임 세션을 생성하고
2. Auto-Narrative를 실행하며 (GraphRAG 호출 발생)
3. 전체 로그 흐름을 콘솔에 출력합니다

### 방법 2: FastAPI 서버 로그 보기

서버를 실행하고 프론트엔드에서 API를 호출하면 실시간으로 로그가 출력됩니다:

```bash
cd /Users/no-eunsu/hobby/sentence-space/back
uvicorn server.app:app --reload --log-level info
```

프론트엔드에서 "진행하기" 버튼을 누르면 다음과 같은 로그가 나타납니다:

```
📥 [API] POST /sessions/abc123/continue 호출됨
🤖 [GameService] Auto-Narrative 진행: session_id=abc123
🎯 [Workflow] run_turn 호출: session_id=abc123
🎮 [Workflow] 게임 상태 로드: session_id=abc123
🤖 [Workflow] Auto-Narrative 노드 시작
🔍 [Workflow] GraphRAG 호출: scenario_id=scenario_1
🔍 [GraphRAG] 시나리오 지식 검색 시작: scenario_id=scenario_1
✅ [GraphRAG] Neo4j 데이터 조회 완료
...
```

### 방법 3: 로그 레벨 조정

특정 컴포넌트의 로그를 더 자세히 보고 싶다면 Python 코드에서 로그 레벨을 조정하세요:

```python
import logging

# GraphRAG의 DEBUG 레벨 로그까지 출력
logging.getLogger("domain.orv_v2.agents.graph_rag_retriever").setLevel(logging.DEBUG)
```

## 주요 로그 키워드

GraphRAG가 실제로 사용되는지 확인하려면 다음 키워드를 찾으세요:

1. **`[Workflow] GraphRAG 호출`** - Workflow에서 GraphRAG를 호출함
2. **`[GraphRAG] 시나리오 지식 검색 시작`** - GraphRAG가 실행됨
3. **`[GraphRAG] Neo4j 데이터 조회 완료`** - Neo4j에서 데이터를 성공적으로 가져옴
4. **`[GraphRAG] 시나리오 컨텍스트 생성 완료`** - 풍부한 컨텍스트가 생성됨

만약 다음 로그가 보인다면:

- **`⚠️ [GraphRAG] Neo4j에 데이터가 없습니다`** - Neo4j에 해당 시나리오 데이터가 없음
- **`ℹ️ [Workflow] GraphRAG retriever가 설정되지 않음`** - GraphRAG가 비활성화됨
- **`⚠️ [Workflow] GraphRAG 조회 실패`** - GraphRAG 호출 중 에러 발생

## 문제 해결

### GraphRAG가 호출되지 않는 경우

1. **컨테이너 설정 확인**
   ```python
   # container/container.py에서
   workflow = GameWorkflow(
       ...,
       graph_rag_retriever=get_graph_rag_retriever(),  # 이 줄이 있는지 확인
       ...
   )
   ```

2. **게임 모드 확인**
   - GraphRAG는 주로 AUTO_NARRATIVE 모드나 시나리오 시작 시점에 호출됩니다
   - INTERACTIVE 모드에서는 덜 자주 호출될 수 있습니다

3. **Neo4j 연결 확인**
   ```bash
   python -m domain.orv_v2.scripts.check_neo4j_scenarios
   ```

### Neo4j 데이터가 없는 경우

현재 Neo4j에는 나무위키에서 파싱한 21개 시나리오만 저장되어 있습니다:

```bash
# 저장된 시나리오 확인
python -m domain.orv_v2.scripts.check_neo4j_scenarios

# 전체 그래프 구조 확인
python -m domain.orv_v2.scripts.show_full_graph
```

**중요**: 나무위키 시나리오는 Phase/Character/Event 등 상세 데이터와 연결되어 있지 않습니다. GraphRAG는 기본 시나리오 정보만 조회할 수 있습니다.

## 로그 출력 예시

완전한 요청 흐름에서 기대되는 로그:

```
INFO - 📥 [API] POST /sessions/abc123/continue 호출됨
INFO - 🤖 [GameService] Auto-Narrative 진행: session_id=abc123
INFO -    - 턴: 5, 현재 시나리오: scenario_1
INFO - 🎯 [Workflow] run_turn 호출: session_id=abc123, player_action=None...
INFO - ▶️  [Workflow] LangGraph 워크플로우 실행 시작...
INFO - 🎮 [Workflow] 게임 상태 로드: session_id=abc123
INFO -    - 게임 모드: auto_narrative, 턴: 5
INFO -    - 현재 시나리오: scenario_1
INFO - 🤖 [Workflow] Auto-Narrative 노드 시작
INFO - 🔍 [Workflow] GraphRAG 호출: scenario_id=scenario_1
INFO - 🔍 [GraphRAG] 시나리오 지식 검색 시작: scenario_id=scenario_1, phase=active, remaining_time=10
INFO - ✅ [GraphRAG] Neo4j 데이터 조회 완료: scenario_title=가치 증명
DEBUG -    - 캐릭터 데이터: 5개
DEBUG -    - 주인공 트릭 조회: 3개
DEBUG -    - 대안 솔루션 조회: 2개
INFO - 🎯 [GraphRAG] 시나리오 컨텍스트 생성 완료:
INFO -    - 캐릭터: 5개, 위치: 3개
INFO -    - 승리조건: 1개, 실패조건: 1개
INFO -    - 주인공 트릭: 3개, 대안 솔루션: 2개
INFO -    - 서술 힌트: 2개
INFO - ✅ [Workflow] GraphRAG 컨텍스트 조회 완료
INFO - ✅ [Workflow] LangGraph 워크플로우 실행 완료
INFO - ✅ [GameService] Auto-Narrative 완료: success=True
INFO - 📤 [API] 응답 성공: success=True
```

## 참고

- 모든 로그는 `INFO` 레벨 이상으로 설정되어 있습니다
- GraphRAG의 상세 정보는 `DEBUG` 레벨로 출력됩니다
- 에러는 `ERROR` 레벨로 `exc_info=True`와 함께 출력되어 스택 트레이스를 포함합니다
