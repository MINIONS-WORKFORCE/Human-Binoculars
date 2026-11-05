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
