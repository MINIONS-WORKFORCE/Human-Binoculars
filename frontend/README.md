# Frontend (SPHEREx Sky Viewer)

Vite + React + TypeScript. Owner: Duy Hoàng. Issue 18 (skeleton) and the blink viewer.

In dev, Mock Service Worker answers every `/api/*` call from the synthetic
samples in [`api_samples/`](../api_samples/README.md), so the frontend runs
without the backend. Tests reuse the same handlers.

## Run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, console shows "[MSW] Mocking enabled."
```

| Command              | What it does                                                             |
| -------------------- | ------------------------------------------------------------------------ |
| `npm run dev`        | Dev server with MSW mocks on                                             |
| `npm test`           | Vitest: API client + MSW, and the `api_samples/` schema check            |
| `npm run lint`       | ESLint                                                                   |
| `npm run typecheck`  | `tsc -b`                                                                 |
| `npm run build`      | Typecheck, then production build into `dist/`                            |
| `npm run gen:types`  | Regenerate `src/api/schema.d.ts` from `shared/api-contract/openapi.yaml` |
| `npm run build:mock` | Production build with MSW baked in (`--mode mock`)                       |
| `npm run e2e`        | Playwright against the mock build (`vite preview` on port 4173)          |

First Playwright run: `npx playwright install chromium`. If that download is
blocked, reuse an installed browser: `PW_CHANNEL=msedge npm run e2e`.

## Real backend vs mocks

Vite reads `VITE_*` variables from the repo-root `.env`.

| Variable                                  | Effect                                                         |
| ----------------------------------------- | -------------------------------------------------------------- |
| `VITE_USE_MOCK=false`                     | Dev server calls the real API instead of MSW                   |
| `VITE_API_BASE_URL=http://127.0.0.1:8000` | Backend origin when mocks are off                              |
| `VITE_USE_MOCK=true`                      | A production build ships with the mocks (demo without backend) |

To use the real fixture backend: set `DATA_MODE=fixture` and `VITE_USE_MOCK=false`
in `.env`, run `npm run dev:be` from the repo root, then `npm run dev` here.
`CORS_ALLOW_ORIGINS` in `.env` must list the exact page origin (for example
`http://localhost:5173`); otherwise every call fails as `NETWORK`. Restart the
backend after changing it.

Check that the mocks still answer exactly like the backend (24 requests, all error
codes included; skipped when `LIVE_API_URL` is unset):

```bash
LIVE_API_URL=http://127.0.0.1:8000 npx vitest run src/api/parity.test.ts
```

## Loading and error states

The page reads only `error.code`, never the server's `message`
(`describeError` in `src/api/client.ts`):

| Code                                             | Shown                              | Try again |
| ------------------------------------------------ | ---------------------------------- | --------- |
| `BAD_COORDS`, `BAD_PARAM`, `UNKNOWN_TARGET`      | What to fix                        | No        |
| `NO_FRAMES`                                      | No images here, try another target | No        |
| `FRAME_NOT_FOUND`                                | Images expired, load again         | Yes       |
| `UPSTREAM_ERROR`, `UPSTREAM_TIMEOUT`             | The NASA archive failed / was slow | Yes       |
| `INTERNAL`, `HTTP_ERROR`, `NETWORK`, unknown 5xx | Server or connection trouble       | Yes       |

While `/api/frames` is pending the page shows "Loading frames…" and, after 3 s, a
seconds counter (a live IRSA query can take 2 minutes). An empty `frames` list
(`FEW_FRAMES`) shows a message instead of an empty viewer. When an image fails to
load (usually `FRAME_NOT_FOUND` after a backend restart) the viewer offers
"Reload frames", which asks `/api/frames` again.

## Layout

```
src/api/schema.d.ts     generated from openapi.yaml, do not edit
src/api/client.ts       typed fetch client, ApiError, contract error table (describeError)
src/api/parity.test.ts  MSW mock vs live backend, request by request (needs LIVE_API_URL)
src/mocks/samples.ts    loads api_samples/ JSON and PNGs
src/mocks/handlers.ts   MSW handlers mirroring members/dong/app/fixture_api.py
src/mocks/browser.ts    service worker setup for dev
src/test/setup.ts       MSW server for Vitest
src/blink/BlinkViewer.tsx       the viewer component (see below)
src/blink/player.ts             pure playback reducer + accumulated rAF clock
src/blink/preload.ts            parallel fetch + img.decode() with progress
src/blink/usePreloadedFrames.ts React hook around preload for originals and diffs
src/blink/canvas.ts             square-pixel drawing and crosshair at (x+0.5)*size
src/coords/parse.ts             decimal degrees / hours-degrees -> degrees (CoordError codes)
src/coords/format.ts            degrees -> "269.4521°", "17h57m48.50s", "+04°41′36.2″"
src/coords/locate.ts            input -> position: coordinates, the 5 targets, then /api/resolve
src/coords/CoordinatePreview.tsx shows the position in every notation while typing
src/App.tsx                     demo page: type a target, load /api/frames, blink
e2e/blink.spec.ts               Playwright: play, step, difference, crosshair pixels
e2e/target-input.spec.ts        Playwright: the three ways to type a target, errors
e2e/errors.spec.ts              Playwright: loading, 504 + Try again, 400, image failure
```

## Target input

One text field accepts a name or coordinates (RA and Dec together):

| Typed           | Example                             | Shown while typing                            |
| --------------- | ----------------------------------- | --------------------------------------------- |
| Decimal degrees | `133.795129 -7.245147`              | the same position in hours / degrees          |
| Hours / degrees | `17h57m48.5s +04d41m36s`            | the same position in decimal degrees          |
| A name          | `Barnard's Star`, `R Dra`, `GJ 699` | the name, decimal degrees and hours / degrees |

The five challenge targets (and their aliases) are found offline. Other names are
sent to `/api/resolve` when the form is submitted; the fixture backend only knows
Barnard's Star for now. Typed coordinates send no `target_key`, so the API returns
no `predicted_px` and the viewer shows no crosshair.

## Using BlinkViewer

```tsx
import { BlinkViewer } from "./blink/BlinkViewer";

const data = await api.frames({ ra, dec, targetKey, detector });
<BlinkViewer
  frames={data.frames}
  grid={data.grid}
  detector={data.detector}
  imageUrl={api.imageUrl} // stable function: png path -> URL on the API origin
  onReload={reload} // optional: offered as "Reload frames" when an image fails
/>;
```

It preloads and decodes every original and difference PNG before playing, then
loops with requestAnimationFrame. Controls: Play/Pause (Space), previous/next
(← →), frame and speed (1-10 fps) sliders, Original/Difference, crosshair on/off.
Each frame shows its UTC date, wavelength and detector. Pixels stay square
(whole device pixels per SPHEREx pixel, no smoothing) and the crosshair sits at
`predicted_px` using the PNG top-left origin.

## When the API contract changes

1. Đông updates `shared/api-contract/openapi.yaml` and `api_samples/`.
2. Run `npm run gen:types` and commit `src/api/schema.d.ts`.
3. CI fails if the generated types are stale, if a sample breaks the OpenAPI
   schema (`src/mocks/samples.test.ts`), or if a sample breaks the backend's
   Pydantic models (`members/dong/scripts/validate_api_samples.py`).
