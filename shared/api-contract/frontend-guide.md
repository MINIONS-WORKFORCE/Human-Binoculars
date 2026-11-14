# Frontend integration for Issue 14

The normal launcher uses app.main and the seven-endpoint API 0.1 wiki contract.
Historical training examples use app.legacy_main.

## Setup

Set DATA_MODE=fixture in the root .env and restart with npm run dev:be.
API_HOST and API_PORT still determine the backend origin. Set the frontend
VITE_API_BASE_URL to that origin and restart Vite. CORS_ALLOW_ORIGINS contains
the actual frontend origins separated by commas. Credentials are omitted.
Use /docs or /openapi.json on the backend for schema details.

## Seven endpoints

| Route | Required query | Optional query |
| --- | --- | --- |
| /api/health | None | None |
| /api/resolve | name | None |
| /api/frames | ra, dec | detector=6, size=0.1, max_frames=60, target_key |
| /api/frames/{id}.png | None | None |
| /api/frames/{id}/diff.png | None | None |
| /api/photometry | ra, dec | target_key, detector, aperture_arcsec=12.3 |
| /api/astrometry | ra, dec | target_key, detector |

RA/Dec use ICRS degrees. Detector is integer 1 through 6. size is a degree
value in [0.02, 0.3]. max_frames is 1 through 200. An omitted science detector
means all available sample detectors. The new entry point returns synchronous
JSON. Previous s_ra/s_dec queries and polling apply to legacy_main.

## Integration presets

For Barnard, send ra=269.4521, dec=4.6934, detector=6, size=0.1,
target_key=barnard. For WISE send ra=133.7951, dec=-7.2451,
target_key=wise0855. Other supported keys are epsindib, rwaur and rdra.
Fixture E3 returns three artificial frames for every target key and accepts
arbitrary valid coordinates. The numbers test UI behavior, not target science.

Fetch /api/frames with URLSearchParams. Read its JSON, check response.ok and
handle error.code. Use frames in mjd order. Resolve each png and diff_png with
new URL(path, import.meta.env.VITE_API_BASE_URL).href.
Call E3 first to publish images before opening their PNG URLs.
Frame IDs are opaque strings. max_frames=1 returns FEW_FRAMES and TRUNCATED.
Without target_key, predicted_px is null.

All PNGs are 39 by 39, 8-bit grayscale. Difference PNGs use gray 128 for zero.
Use image-rendering: pixelated or disable canvas image smoothing.
predicted_px has the top-left PNG origin and zero-based pixel centres.
Draw a scaled marker at (x+0.5)*scale and (y+0.5)*scale.
PNG responses include Cache-Control: public, max-age=86400.
The image registry is in-process and bounded. If an image was evicted or the
server restarted, reissue the frames request after FRAME_NOT_FOUND.

## JSON and failures

Each JSON body includes api_version=0.1. The common error has code, message,
and details. Use code for UI decisions. BAD_COORDS and BAD_PARAM use HTTP 400.
UNKNOWN_TARGET and FRAME_NOT_FOUND use HTTP 404. error_no_frames.json
illustrates NO_FRAMES; an empty filtered list should instead use FEW_FRAMES.
Unexpected failures use HTTP 500 INTERNAL with safe public messages.

The resolver uses the bundled five-target catalog. Other names return
UNKNOWN_TARGET. With DATA_MODE=live, frames, photometry and astrometry use
SPHEREx cutouts fetched from IRSA. Empty discovery yields NO_FRAMES for E3
and empty measurements for E6/E7. Upstream failures return 502 UPSTREAM_ERROR
or 504 UPSTREAM_TIMEOUT.

## Samples and handoff

The six JSON files and six PNGs under api_samples/ are shared with frontend MSW.
Read api_samples/README.md for the synthetic-data rules. Run the schema validator
before updating samples. Duy Hoang can connect this validator to CI for Issue 18
and generate TypeScript from /openapi.json. The model field names and units
follow the new wiki, which supersedes the historical SRS snapshot.
