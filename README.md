# tls123의 괴수 백과

전지적 독자 시점 세계관 기반 괴수 정보 검색 시스템

## 프로젝트 구조

```
sentence-space/
├── back/           # FastAPI 백엔드 서버
└── front/          # React + TypeScript 프론트엔드
```

## 시스템 요구사항

- **백엔드**: Python 3.11+
- **프론트엔드**: Node.js 18+
- **패키지 매니저**: uv (백엔드), npm (프론트엔드)

## 백엔드 설치 및 실행

### 1. 의존성 설치

```bash
cd back
uv sync
```

### 2. 환경변수 설정

`back/.env` 파일을 생성하고 다음 내용을 설정:

```env
DEBUG=true
HOST=0.0.0.0
PORT=8000

# LLM API 키 (둘 중 하나 필수)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# 또는 OpenRouter 사용
OPENROUTER_API_KEY=your_openrouter_api_key_here
LLM_MODEL=anthropic/claude-3.5-sonnet
```

### 3. 서버 실행

```bash
cd back
uv run python main.py
```

서버는 http://localhost:8000 에서 실행됩니다.

## 프론트엔드 설치 및 실행

### 1. 의존성 설치

```bash
cd front
npm install
```

### 2. 개발 서버 실행

```bash
cd front
npm run dev
```

프론트엔드는 http://localhost:5173 에서 실행됩니다.

## 주요 기능

- **괴수 정보 검색**: 자연어로 괴수 정보 질문 및 검색
- **괴수 목록**: 등급별/종별 괴수 목록 열람
- **RAG 기반 응답**: ChromaDB 벡터 검색 + LLM 응답 생성

## 기술 스택

### 백엔드
- **FastAPI**: Python 웹 프레임워크
- **ChromaDB**: 벡터 데이터베이스
- **LangChain**: LLM 통합

### 프론트엔드
- **React 18**: UI 라이브러리
- **TypeScript**: 정적 타입
- **Vite**: 빌드 도구
