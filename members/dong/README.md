# Dong backend API

The active application implements the Issue 14 API 0.1 fixture contract.
Daily scope comes from GitHub Issues. Models and samples follow the
[API wiki](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/wiki/The-API-contract).

## Layout

    members/dong/
      dev.mjs                    Node launcher reading the root .env
      app/
        main.py                  FastAPI setup, CORS, errors, timing, OpenAPI
        api_models.py            Current request and response models
        fixture_api.py           Seven HTTP routes and PNG response headers
        services/
          fixtures.py            Local samples, response preparation, bounded image registry
        legacy_main.py           Compatibility entry point for earlier training links
        legacy/
          main.py                Earlier training application
          schemas.py             Earlier API models
          mock_api.py            Day 4 and Day 5 mock routes
          frame_jobs.py          Day 6 jobs and disk cache exercise
      scripts/
        validate_api_samples.py  Validate current JSON, PNG format and overlay position
        legacy/
          build_wise0855_fixture.py
          build_cutout_fixture.py
      tests/
        conftest.py
        test_api_contract.py     Current seven-endpoint contract tests
        legacy/                  Earlier mock, job and pipeline regression tests
      docs/
        legacy/                  SIA2 notes, cache design and Day 6 delivery history

The router calls the fixture service. The service reads local sample files and
prepares model-validated results; main.py translates service errors into the
shared JSON error shape. The current application does not import legacy code.
The historical app remains available through app.legacy_main because existing
team guides still link to that entry point.

Shared files used by the team remain at the repository root under api_samples/
and shared/api-contract/. Real FITS, local metadata and caches belong in ignored
data/cache locations. See the [sample notes](../../api_samples/README.md) for
the distinction between synthetic examples and observed data.

## Run

Run commands from the repository root with dependencies installed in .venv.
Configure API_HOST and API_PORT in the root .env, set DATA_MODE=fixture, and
set CORS_ALLOW_ORIGINS to the frontend origins. Start with npm run dev:be.
Restart the launcher after editing .env.

Read the [frontend guide](../../shared/api-contract/frontend-guide.md) for
the request parameters and seven endpoints exposed in /docs.

## Validate

    .venv/Scripts/python.exe members/dong/scripts/validate_api_samples.py
    .venv/Scripts/python.exe -m pytest members/dong/tests -q

The tests include current API behavior and the isolated historical regression
tests. Moving a legacy file is not a reason to remove tests for behavior that
the historical entry point still supports.

## Historical exercises

The old app entry point remains app.legacy_main:app. To run it on a separate
chosen port, invoke Uvicorn with --app-dir members/dong and the host/port
appropriate for your machine. It uses its historical FRAMES_MODE and
PIPELINE_SOURCE settings.

- [SIA2 notes](docs/legacy/sia2-notes.md)
- [Cache key design](docs/legacy/cache-key-design.md)
- [Day 6 delivery](docs/legacy/day06-frames-jobs-cache.md)

The old preparation tools now live under scripts/legacy/. Their behavior is
preserved and their documentation uses the new paths.

## Working rules

Use a dong/<task> branch and a small PR. Code imported by other members belongs
in shared/. Strip notebook outputs before committing. Keep .env and observed
FITS/cutouts/databases out of Git.
