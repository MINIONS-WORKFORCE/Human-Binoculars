# Frontend (SPHEREx Sky Viewer)

Vite + React + TypeScript. Owner: Duy Hoàng. Issue 18.

In dev, Mock Service Worker answers every `/api/*` call from the synthetic
samples in [`api_samples/`](../api_samples/README.md), so the frontend runs
without the backend. Tests reuse the same handlers.

## Run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, console shows "[MSW] Mocking enabled."
```

| Command             | What it does                                                             |
| ------------------- | ------------------------------------------------------------------------ |
| `npm run dev`       | Dev server with MSW mocks on                                             |
| `npm test`          | Vitest: API client + MSW, and the `api_samples/` schema check            |
| `npm run lint`      | ESLint                                                                   |
| `npm run typecheck` | `tsc -b`                                                                 |
| `npm run build`     | Typecheck, then production build into `dist/`                            |
| `npm run gen:types` | Regenerate `src/api/schema.d.ts` from `shared/api-contract/openapi.yaml` |

## Real backend vs mocks

Vite reads `VITE_*` variables from the repo-root `.env`.

| Variable                                  | Effect                                                         |
| ----------------------------------------- | -------------------------------------------------------------- |
| `VITE_USE_MOCK=false`                     | Dev server calls the real API instead of MSW                   |
| `VITE_API_BASE_URL=http://127.0.0.1:8000` | Backend origin when mocks are off                              |
| `VITE_USE_MOCK=true`                      | A production build ships with the mocks (demo without backend) |

To use the real fixture backend: set `DATA_MODE=fixture` and `VITE_USE_MOCK=false`
in `.env`, run `npm run dev:be` from the repo root, then `npm run dev` here.

## Layout

```
src/api/schema.d.ts     generated from openapi.yaml, do not edit
src/api/client.ts       typed fetch client, ApiError, friendly messages
src/mocks/samples.ts    loads api_samples/ JSON and PNGs
src/mocks/handlers.ts   MSW handlers mirroring members/dong/app/fixture_api.py
src/mocks/browser.ts    service worker setup for dev
src/test/setup.ts       MSW server for Vitest
src/App.tsx             temporary page: loads /api/frames and lists the frames
```

## When the API contract changes

1. Đông updates `shared/api-contract/openapi.yaml` and `api_samples/`.
2. Run `npm run gen:types` and commit `src/api/schema.d.ts`.
3. CI fails if the generated types are stale, if a sample breaks the OpenAPI
   schema (`src/mocks/samples.test.ts`), or if a sample breaks the backend's
   Pydantic models (`members/dong/scripts/validate_api_samples.py`).
