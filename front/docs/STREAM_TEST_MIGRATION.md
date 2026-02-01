# Stream Test HTML to React Migration

## 개요

`test_stream.html` 파일을 React와 FSD(Feature-Sliced Design) 패턴으로 마이그레이션했습니다.

## 아키텍처

### FSD (Feature-Sliced Design) 구조

```
src/
├── shared/              # 공유 리소스
│   ├── ui/             # 재사용 가능한 UI 컴포넌트
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Container.tsx
│   │   ├── Status.tsx
│   │   └── index.ts
│   ├── lib/            # 유틸리티 및 설정
│   │   ├── theme.ts
│   │   └── globalStyles.ts
│   ├── types/          # 타입 정의
│   │   └── stream.ts
│   └── api/            # API 통신 로직
│       └── streamApi.ts
├── features/           # 기능별 컴포넌트
│   └── stream-viewer/
│       ├── EventCard.tsx
│       ├── Statistics.tsx
│       ├── OutputSection.tsx
│       └── index.ts
└── pages/              # 페이지 컴포넌트
    └── stream-test/
        ├── StreamTestPage.tsx
        └── index.ts
```

## 주요 기능

### 1. Emotion 기반 스타일링

- `@emotion/react`와 `@emotion/styled`를 사용한 CSS-in-JS
- 테마 시스템으로 일관된 디자인 유지
- 타입 안전한 스타일 props

### 2. 타입 안전성

- TypeScript로 모든 컴포넌트 타입 정의
- Stream Event, Status, Stats 등 명확한 타입 정의

### 3. 컴포넌트 분리

- **UI 컴포넌트**: 재사용 가능한 기본 컴포넌트 (Button, Input, etc.)
- **Feature 컴포넌트**: 스트림 뷰어 관련 기능 (EventCard, Statistics)
- **Page 컴포넌트**: 전체 페이지 구성

### 4. API 추상화

- `StreamApi` 클래스로 스트리밍 API 통신 캡슐화
- AsyncGenerator를 활용한 이벤트 스트리밍

## 실행 방법

### 개발 서버 실행

```bash
cd front
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

### 프로덕션 빌드

```bash
npm run build
npm run preview
```

## 주요 변경사항

### HTML → React 변환

| 기존 (HTML)                      | 변환 후 (React)                     |
| -------------------------------- | ----------------------------------- |
| 인라인 CSS                       | Emotion styled components           |
| 전역 함수 (`testStream()`)       | React hooks (`useState`, `useEffect`) |
| DOM 직접 조작                    | 선언적 상태 관리                    |
| `fetch` + 수동 스트림 처리       | `StreamApi` 클래스                   |

### 주요 개선사항

1. **타입 안전성**: TypeScript로 런타임 에러 방지
2. **컴포넌트 재사용**: UI 컴포넌트 모듈화
3. **상태 관리**: React hooks를 통한 명확한 상태 관리
4. **자동 스크롤**: `useEffect`를 활용한 자동 스크롤 기능
5. **키보드 단축키**: Ctrl/Cmd + Enter로 스트리밍 시작

## 사용 예시

```tsx
// 스트리밍 시작
const streamApi = new StreamApi('http://localhost:8000/api/v2/clickup/chat/stream');

for await (const event of streamApi.streamChat({ message: '메시지' })) {
  // 이벤트 처리
  console.log(event);
}
```

## 스타일 테마

테마는 `src/shared/lib/theme.ts`에 정의되어 있으며, 다음과 같은 값들을 포함합니다:

- **Colors**: Primary gradient, status colors, event colors
- **Spacing**: 일관된 간격 시스템
- **Border Radius**: 다양한 모서리 반경
- **Shadows**: 깊이감을 위한 그림자
- **Fonts**: 시스템 폰트 및 monospace

## 향후 개선 사항

- [ ] 에러 바운더리 추가
- [ ] 로딩 스켈레톤 UI
- [ ] 이벤트 필터링 기능
- [ ] 다크모드 지원
- [ ] 이벤트 내보내기 기능
