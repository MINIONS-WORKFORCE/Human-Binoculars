# Dong backend API

The active application implements the API 0.1 fixture contract. Issue 24
connects the frame endpoints to local SPHEREx FITS cutouts.
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
          fixtures.py            Route orchestration, sample fallback and PNG cache
          observed_frames.py     Local FITS discovery and cached frame bundles
          frame_rendering.py     TAN reprojection, visit median, frame and difference PNGs
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
        test_observed_frames.py  Frame contract tests with generated and local archive FITS
        legacy/                  Earlier mock, job and pipeline regression tests
      docs/
        legacy/                  SIA2 notes, cache design and Day 6 delivery history

The router calls the fixture service, which prepares model-validated results.
The application translates service errors into the shared JSON error shape.
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

## Try observed Barnard frames

Set `DATA_MODE=fixture` and `DATA_DIR=data` in the root .env. For Khôi's pack,
place the index at `data/fixtures/manifest.json` and keep the FITS at the paths
listed in it. The backend calls `shared.pipeline.irsa.find_frames()` against
this index. The older `data/fixture_pack_v1` layout also works with its
`metadata.csv`, `rendered/frames.json` and original FITS files.

In Swagger at `/docs`, execute `GET /api/frames` with these values for the
local Barnard pack.

| Parameter | Value |
| --- | --- |
| `ra` | `269.44636864652` |
| `dec` | `4.766880108377093` |
| `target_key` | `barnard` |
| `detector` | `6` |
| `size` | `0.05` |

Open the returned `png` and `diff_png` paths on the same backend. IDs starting
with `observed-` identify images rendered from local FITS. If matching FITS
are unavailable, IDs starting with `fixture-` identify the synthetic samples.

The renderer reuses Hữu Hoàng's FITS and TAN helpers. It masks flagged and
non-finite input pixels, aligns cutouts on one TAN grid, and takes a median per
visit. Gaps over 30 days start a new visit, and `survey` is
the index of that visit in the selected data. Wavelength, bandwidth and time
are medians of the contributing cutouts. The bad pixel fraction averages the
input fractions rejected by FLAGS. For a named target, E2 reads the team target
table and E3 propagates its catalog position to the middle of the observation
sequence for the grid center and to each frame's MJD for `predicted_px`. The
prediction includes angular proper motion. With coordinates alone, E3 uses the
request center and returns `predicted_px: null`.

If an indexed fixture covers the grid but its frames are filtered out, E3
returns `200` with `frames: []` and `FEW_FRAMES`. If indexed FITS are available
but none cover the grid, E3 returns `404 NO_FRAMES`.

The PNGs share an asinh stretch. Each difference image uses the first frame
as its reference, with gray 128 at zero. The local v1 Barnard D6 cutouts cover
one visit, so the single difference image is neutral and E3 reports
`FEW_FRAMES`. Differences are for visual comparison. Wavelength and PSF can
vary across observations.

E3 caches each rendered bundle in memory using the query and FITS revisions.
E4 and E5 read their PNGs from the bounded image cache. If the process restarts
or an image is evicted, call E3 again to republish its image URLs.

## Validate

    .venv/Scripts/python.exe members/dong/scripts/validate_api_samples.py
    .venv/Scripts/python.exe -m pytest members/dong/tests -q

The tests include current API behavior and the isolated historical regression
tests. Moving a legacy file is not a reason to remove tests for behavior that
the historical entry point still supports.

`test_observed_frames.py` exercises a deterministic FITS manifest, cache
reuse and invalidation, and the observed Barnard pack when available locally.

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
