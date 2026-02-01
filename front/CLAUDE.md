# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development

- `npm run dev` or `yarn dev`: Start development server with hot reload on port 5173
- `npm run build` or `yarn build`: Build the application (compiles i18n messages, TypeScript, and bundles with Vite)
- `npm run lint` or `yarn lint`: Run ESLint on all files
- `npm run preview` or `yarn preview`: Preview the built application locally

### Internationalization

- `npm run paraglide:compile`: Compile i18n message files from `messages/*.json` to `src/paraglide`
  - This is automatically run before build
  - Source files: `messages/ko.json` (source), `messages/en.json`, `messages/de.json`

### Testing

- `npm run test:e2e`: Run Playwright E2E tests
- `npm run test:e2e:ui`: Run E2E tests with Playwright UI
- `npm run test:e2e:headed`: Run E2E tests in headed mode (visible browser)
- `npm run test:e2e:report`: Show the last test report
  - Tests are located in `e2e/tests/`
  - Configured to run on Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari, and iPad

### Design System

- `cd design-system && npm run storybook`: Launch Storybook on port 6006 for component development
- `cd design-system && npm run build-storybook`: Build static Storybook site

## Architecture

This is a React + TypeScript application using **Feature-Sliced Design (FSD)** architecture with strict layer separation.

### FSD Layers (src/)

Layers are ordered by dependency hierarchy (lower layers can't import from higher layers):

1. **app/**: Application initialization, global providers, and routing

   - `App.tsx`: Root component that wraps providers (`I18nProvider` → `GlobalStyleProvider` → `QueryProvider` → `RouterProvider`)
   - `providers/`: Global providers (i18n, React Query, Emotion global styles)
   - `routers/`: React Router v7 configuration with protected routes

2. **pages/**: Route-level components, page compositions, and layouts

   - Each page directory corresponds to a route
   - Pages compose features and widgets

3. **widgets/**: Complex UI components that combine multiple features

   - Self-contained, reusable component compositions

4. **features/**: Business logic features and user interactions

   - Domain-specific functionality (e.g., authentication, customer management)
   - Can use entities, shared, and other features

5. **entities/**: Business entities and domain models

   - Core domain types and business logic
   - Navigation constants and route definitions

6. **shared/**: Reusable utilities, UI components, APIs, hooks, and stores
   - `shared/apis/`: Axios HTTP client setup with interceptors
     - Base client configured with `VITE_BACKEND_URL` and `VITE_API_VERSION`
     - Request interceptor adds Authorization header from Zustand store (except auth routes)
     - Response interceptor handles 401 errors by clearing auth store
   - `shared/store/`: Zustand stores for global state management
     - `useAuthStorageStore`: Authentication state with encrypted token storage
   - `shared/hooks/`: Reusable custom hooks
   - `shared/ui/`: Base UI components (buttons, inputs, etc.)
   - `shared/utils/`: Utility functions
   - `shared/types/`: TypeScript type definitions

### Path Aliases

All FSD layers have TypeScript and Vite path aliases configured:

```typescript
'@/app/*' → 'src/app/*'
'@/pages/*' → 'src/pages/*'
'@/widgets/*' → 'src/widgets/*'
'@/features/*' → 'src/features/*'
'@/entities/*' → 'src/entities/*'
'@/shared/*' → 'src/shared/*'
'@/paraglide/*' → 'src/paraglide/*'
```

### Key Technologies

- **React 18** with TypeScript (strict mode enabled)
- **Vite 7** as build tool with **SWC** for fast compilation
- **React Router v7** for routing with protected routes
- **TanStack Query v5** for server state management
- **Zustand** for client state management (see `shared/store/`)
- **Emotion** for styling (CSS-in-JS)
- **React Hook Form + Zod** for form handling and validation
- **Axios** for HTTP requests with interceptors
- **Paraglide.js** for type-safe i18n (compiles JSON messages to TypeScript)
- **Playwright** for E2E testing across browsers

### Internationalization (i18n)

- Uses **Paraglide.js** with **Inlang** for type-safe i18n
- Source language: Korean (`ko`)
- Supported languages: Korean, English, German
- Message files in `messages/{languageTag}.json`
- Compiled to `src/paraglide/` (do not edit directly)
- Build-time compilation ensures type safety and zero runtime overhead
- `VITE_LANGUAGE` environment variable controls the default language and HTML lang/title attributes

### SVG Handling

- **SVGR plugin** enabled: Import SVGs as React components
- Example: `import LogoIcon from './logo.svg'` (imported as component)

### Development Tools

- **Husky**: Git hooks for pre-commit linting
- **lint-staged**: Runs `eslint --fix` on staged `.{js,jsx,ts,tsx}` files
- **ESLint**: Flat config with TypeScript, React Hooks, and React Refresh rules
  - Note: Some rules set to `warn` instead of `error` (see TODO in `eslint.config.js`)

### Proxy Configuration

Development server proxies `/logo-proxy/*` requests to `https://files.edutap.ai` for loading external assets.

### Design System

Separate package in `design-system/` directory:

- Independent build pipeline with Vite
- Storybook for component documentation and development
- Shared UI components built with Emotion
- Peer dependencies: React 18, Emotion

### Environment Variables

Required environment variables (see `.env` files):

- `VITE_BACKEND_URL`: Backend API base URL
- `VITE_API_VERSION`: API version path segment (e.g., `v1`)
- `VITE_LANGUAGE`: Default language (`korean` or `english`)

### TypeScript Configuration

- Strict mode enabled with additional checks:
  - `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`
  - `noUncheckedSideEffectImports`, `erasableSyntaxOnly`
- Target: ES2022 with bundler module resolution
