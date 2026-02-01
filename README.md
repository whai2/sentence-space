# In-House System

ClickUp 통합 기능을 포함한 사내 관리 시스템

## 프로젝트 구조

```
in-house-system/
├── back/           # FastAPI 백엔드 서버
└── front/          # React + TypeScript 프론트엔드
```

## 시스템 요구사항

- **백엔드**: Python 3.11+
- **프론트엔드**: Node.js 18+
- **패키지 매니저**: uv (백엔드), npm/yarn (프론트엔드)

## 백엔드 설치 및 실행

### 1. 가상환경 생성 및 의존성 설치

```bash
cd back
uv install
```

### 2. 환경변수 설정

`back/.env` 파일을 생성하고 다음 내용을 설정:

```env
# 서버 설정
DEBUG=True
HOST=0.0.0.0
PORT=8000

# LLM API 키
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSION=1536
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# ClickUp 설정
CLICKUP_ACCESS_TOKEN=your_clickup_access_token_here
CLICKUP_API_KEY=your_clickup_api_key_here
CLICKUP_TEAM_ID=your_clickup_team_id_here
```

### 3. 서버 실행

```bash
cd back
uv run python main.py
```

서버는 http://localhost:8000 에서 실행됩니다.

### API 문서

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 프론트엔드 설치 및 실행

### 1. 의존성 설치

```bash
cd front
npm install
# 또는
yarn install
```

### 2. 환경변수 설정

프론트엔드는 환경변수 파일이 필요하지 않지만, 백엔드 API URL이 기본적으로 개발 서버 설정과 매칭되어야 합니다.

### 3. 개발 서버 실행

```bash
cd front
npm run dev
# 또는
yarn dev
```

프론트엔드는 http://localhost:5173 에서 실행됩니다.

### 4. 빌드

```bash
cd front
npm run build
# 또는
yarn build
```

## 주요 기능

- **ClickUp 통합**: 태스크 관리 및 프로젝트 추적
- **AI 기반 처리**: OpenAI 및 Anthropic API를 활용한 지능형 기능
- **실시간 데이터**: FastAPI와 React를 통한 반응형 사용자 인터페이스

## 개발 명령어

### 백엔드
```bash
cd back
uv run python main.py    # 개발 서버 실행
```

### 프론트엔드
```bash
cd front
npm run dev        # 개발 서버 실행
npm run build      # 프로덕션 빌드
npm run lint       # 코드 린팅
npm run preview    # 빌드된 앱 미리보기
```

## 기술 스택

### 백엔드
- **FastAPI**: 고성능 Python 웹 프레임워크
- **LangChain**: AI 모델 통합
- **Dependency Injector**: 의존성 주입
- **Uvicorn**: ASGI 서버

### 프론트엔드
- **React 18**: 사용자 인터페이스 라이브러리
- **TypeScript**: 정적 타입 검사
- **Vite**: 빠른 빌드 도구
- **Emotion**: CSS-in-JS 스타일링
- **Zustand**: 상태 관리

## 라이센스

이 프로젝트는 사내 시스템으로 제작되었습니다.# in-house-system
