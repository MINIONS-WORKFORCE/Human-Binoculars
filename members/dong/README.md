# Đông: Backend API + cache

What goes here: SIA2 column notes, FastAPI experiments, mock server, cache design. The agreed API contract goes in shared/api-contract/.

- Work on a branch named `dong/<task>` and open a small PR.
- Notebooks: clear outputs before committing (`nbstripout` does it automatically once installed).
- Never commit FITS files, cutouts or databases; put them in `data/` (gitignored) or on the team drive.
- Code that a teammate will import goes in `shared/`, not here.

## Day 3: FastAPI health endpoint

`main.py` is the minimal backend training app. `GET /health` reports that the
application can serve requests; it does not check IRSA, image processing or cache.

Use the Python 3.12 environment from the root README. FastAPI and Uvicorn are
already declared in the shared `requirements.txt`.

From the repository root, with dependencies installed in `.venv`, create local
configuration once (do not overwrite an existing `.env`):

```powershell
Copy-Item .env.example .env
```

Set `API_HOST` and `API_PORT` in `.env`, then run:

```dotenv
API_HOST=127.0.0.1
API_PORT=8000
```

```powershell
npm run dev:be
```

The launcher uses `.venv` directly on Windows, macOS and Linux, so activation is
not required. It reads `.env` from the repo root and passes `API_HOST` and
`API_PORT` to Uvicorn. Both settings are required; the launcher has no hardcoded
host or port defaults. Existing shell environment variables take precedence over
`.env`; explicit Uvicorn arguments after `--` can override the launch options.
Node loads `.env` using its built-in `loadEnvFile`, so no npm dependency is needed.

Code changes trigger reload. After changing `.env`, stop and restart the launcher.
If you change the backend address, update `VITE_API_BASE_URL` separately to match
and restart the frontend. Never commit `.env`; only `.env.example` is shared.

With the example address above, check from another terminal:

```powershell
curl.exe --fail --show-error http://127.0.0.1:8000/health
```

Expected: HTTP `200` and `{"status":"ok"}`. Open
[Swagger UI](http://127.0.0.1:8000/docs) to try the endpoint interactively, or
[OpenAPI JSON](http://127.0.0.1:8000/openapi.json) to inspect its generated schema.
Stop the server with `Ctrl+C`.

The SIA2 notes for the same day are in [sia2-notes.md](sia2-notes.md).

## WISE 0855 metadata fixture

The saved SIA2 HTML response can seed local mock development with real observation
metadata. From the repository root:

```powershell
.venv\Scripts\python.exe members/dong/build_wise0855_fixture.py "D:\Study\lol\NASA\wise0855-qr2.html"
```

This writes `data/wise0855_qr2_sources.json`, which Git ignores. By default it
selects four observations spread over time for each of the six detectors (24
total) from the 278 QR2 rows. The source fields keep the exact SIA2 column names
used by the API contract. Use `--per-band` or `--output` to change the selection
or local destination. Do not commit the generated file or the original HTML.

This is a metadata seed, not a completed `/api/frames` response: the HTML table
contains FITS access URLs but no PNG pixels. It also has no source flux, flux
uncertainty or per-object spectrum. Any temporary PNG or flux values used to
exercise the UI must be clearly marked `data_kind: mock` with `MOCK_DATA`; do not
present them as SPHEREx measurements.

## Day 4: mock endpoints

Generate the local fixture above, then start the backend with `npm run dev:be`.
Open `/docs` on your configured backend address to try all three endpoints.
For the example address in `.env.example`:

```powershell
curl.exe --fail "http://127.0.0.1:8000/api/frames?s_ra=133.79513&s_dec=-7.24515&obs_collection=spherex_qr2&energy_bandpassname=SPHEREx-D6&cutout_size_deg=0.05"
curl.exe --fail "http://127.0.0.1:8000/api/spectrum?s_ra=133.79513&s_dec=-7.24515&obs_collection=spherex_qr2"
curl.exe --fail "http://127.0.0.1:8000/api/lightcurve?s_ra=133.79513&s_dec=-7.24515&obs_collection=spherex_qr2&energy_bandpassname=SPHEREx-D6"
```

- All responses use `data_kind: mock` and a `MOCK_DATA` warning. Metadata in
  `sources` comes from the local SIA2 export. No request contacts IRSA.
- Frames use real observation times, with one synthetic PNG per source. Resolve
  `image_url` against the backend origin, not the frontend origin. Each PNG has
  a MOCK label. Pixel movement is artificial; size is fixed at 384 by 384 and
  `cutout_size_deg` does not perform an astronomical crop in this mock.
- Spectrum returns one illustrative point per available detector, using the
  earliest matching source. These may come from different dates. Wavelengths,
  fluxes and errors are synthetic; `mJy` is only a chart fixture unit.
- Lightcurve returns one illustrative point per matching source in time order.
  Its fluxes and comparison passband are synthetic. Neither chart performs
  photometry or extracts a spectrum from FITS.
- The mock matches only RA 133.79513, Dec -7.24515 (tolerance 0.000001 degrees)
  and `spherex_qr2`. Other valid targets/releases return HTTP 200 with empty
  lists, `MOCK_TARGET_ONLY` and `NO_DATA`; this says nothing about real archive
  coverage. No collection fallback is performed.
- Optional `t_min/t_max` filter the selected fixture rows by time overlap.
  Invalid inputs return contract-shaped HTTP 422 errors. Missing or malformed
  fixture data returns HTTP 500 with a safe message. `/health` stays independent.
- The server reads `wise0855_qr2_sources.json` from `DATA_DIR` (default `data`,
  relative to the repository root). Share this ignored fixture via the team
  drive or regenerate it from the original HTML. Only generator/server code
  belongs in Git.
- GET responses allow public CORS without credentials for local frontend testing.
  Responses are deterministic for a fixed fixture; there are no jobs or cache yet.

Run the behavior tests from the repository root. They create synthetic metadata
in a temporary directory and do not need real data or network access:

```powershell
.venv\Scripts\python.exe -m pytest members/dong/test_mock_api.py -q
```
