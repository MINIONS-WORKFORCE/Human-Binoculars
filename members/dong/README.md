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
For known targets with indexed FITS, E6 and E7 measure the original exposures
using `shared.science`. The detector filter applies before measurement, and E6
uses `aperture_arcsec` as a radius. E6 uses the same visit numbering as E3 and
publishes only rows with a valid wavelength. Science points identify source
exposures. Astrometry leaves `measured_px` null when no matching display grid is
provided. If FITS are unavailable, the endpoints serve the existing examples.
The application translates service errors into the shared JSON error shape.
The historical app remains available through app.legacy_main because existing
team guides still link to that entry point.

Shared files used by the team remain at the repository root under api_samples/
and shared/api-contract/. Real FITS, local metadata and caches belong in ignored
data/cache locations. See the [sample notes](../../api_samples/README.md) for
the distinction between synthetic examples and observed data.

## Run

Run commands from the repository root with dependencies installed in .venv.
Configure API_HOST and API_PORT in the root .env, set DATA_MODE=live and
VITE_USE_MOCK=false, and
set CORS_ALLOW_ORIGINS to the frontend origins. Start with npm run dev:be.
Restart the launcher after editing .env.

In live mode, E3, E6 and E7 fetch FITS cutouts from IRSA on demand. The default
collection is `spherex_dr1`, with `spherex_qr3` used when discovery is empty.
The downloader samples up to six visits and one exposure per detector per visit.
The upstream deadline is 65 seconds. FITS are written to a temporary workspace
under `DATA_DIR/cache` and removed after processing. Live responses are cached
on disk in `DATA_DIR/cache/api-0.1-live` before any new archive lookup.
The cache key includes the endpoint, collection settings and all validated
query parameters. Results expire after 15 minutes, or after 1 minute when
frames report `FEW_FRAMES` or science returns no points. Frame responses expose
`X-Cache: HIT` or `X-Cache: MISS`. Reloading frames after a backend restart
republishes PNGs from the cached response if it is still available.

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

## MVP v1 acceptance backend

The [SRS](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/wiki/System-Requirement-Specific-Of-The-SphereX-website)
describes a different wire contract from the current public API 0.1. Start
`app.mvp_main:app` to try the SRS contract. The public entry point
`app.main:app` and its OpenAPI schema are still available for the existing
frontend. The [MVP v1 OpenAPI snapshot](../../shared/api-contract/openapi-mvp-v1.yaml)
is checked against the generated schema.

Run from the repository root. On Windows PowerShell:

```powershell
$env:API_MODE = "mock"
.venv/Scripts/python.exe -m uvicorn app.mvp_main:app --app-dir members/dong --port 8001
```

Open `/docs` on port 8001. GET `/health` checks liveness. GET `/api/targets`
returns the five target centers propagated to the midpoint of the QR2 period
in the SRS. For GET `/api/frames`, use a target's `ra_deg` and `dec_deg` as
`s_ra` and `s_dec`, use `spherex_qr2` or `spherex_qr3` as
`obs_collection`, use a band such as `SPHEREx-D6`, and send the FOV in degrees
as `cutout_size_deg` (arcminutes divided by 60). The maximum is 0.2 degrees.
Open each returned `image_url` on the same backend.

- **Mock.** Works without FITS. Results carry `data_kind: mock` and a
  `MOCK_DATA` warning. Synthetic frames have no observational source IDs.
- **Real.** Set `API_MODE=real` and restart. The backend reads a matching
  prebuilt bundle first, then the disk cache, then IRSA SIA2 and the cutout
  service. Up to six cutouts are used per visit. The renderer masks flags,
  aligns onto one TAN grid and uses one asinh stretch. Each frame records
  the contributing ObsCore product IDs. No matching archive data returns
  `200` with `NO_DATA`; a release is never substituted. The API maps invalid
  inputs to `422`, archive errors to `502`, and timeouts to `504`. A request
  has a 120-second budget and the logs record timing per stage.
- **Cache.** PNG and metadata are published in the same disk-cache record
  under `DATA_DIR/cache/mvp`. `X-Cache` reports `PREBUILT`, `HIT`, or `MISS`.
  Keys include release, detector, FOV, and time bounds. Exact coordinates
  distinguish different TAN centers within the SRS's rounded sky bucket.

To prepare a bundle from the local v1 notebook pack, run:

```powershell
.venv/Scripts/python.exe members/dong/scripts/prepare_mvp_bundle.py barnard
```

Use `--manifest data/fixtures/manifest.json` for the team's FITS manifest.
Select the target, `--detector`, `--fov-arcmin` and `--collection` for each
bundle. The script writes PNG files and `bundle.json` under
`DATA_DIR/prebuilt/<target>/<D>/<key>/`. It requires actual FITS of the selected
release, detector and field size. Keep the prebuilt and cache directories,
FITS and environment values out of Git.

Run `python -m pytest members/dong/tests/test_mvp_api.py -q` for the MVP
checks, including both response modes, offline bundle delivery, source IDs,
cache reuse, validation and upstream failures. Full offline acceptance for
five targets across six detectors depends on the corresponding team FITS
or prebuilt bundles.

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
