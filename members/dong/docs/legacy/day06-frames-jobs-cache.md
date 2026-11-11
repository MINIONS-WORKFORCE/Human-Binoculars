# Day 6 delivery and Day 7 plan

## Delivered behavior

Branch `dong/frames-jobs-cache` was created from `dong/mock-fixture-api`,
including the existing uncommitted Day 5 work.

`GET /api/frames` supports an opt-in pipeline mode. A first request returns
HTTP 202 with a job ID and status URL. Poll that URL until the status becomes
`succeeded` or `failed`. A successful status response contains `result`,
using the existing frames response shape. A repeated completed request returns
HTTP 200 and `X-Cache: HIT`. PNG URLs are included in the result.

The current implementation supports two active jobs per server process.
Additional distinct requests receive HTTP 503 while capacity is occupied.
Identical pending requests reuse a job ID through a DiskCache transaction.
Run one Uvicorn worker for this training implementation.

## Input and processing ownership

The shared pipeline adapts the SIA2/cutout approach in Khoi's
`notebook272cc76da9.ipynb`, with explicit collection selection and complete
source metadata. Its masking, WCS reprojection and shared display scale follow
Huu Hoang's `reproject_demo.py` at commit `9c30daf`.

The integration adds parameterized processing, a fixed TAN grid centered on the
requested ICRS coordinates, a 6.2 arcsecond pixel size, and median stacking.
The output side is rounded up to whole pixels. A 0.05 degree request produces
a 30 by 30 image. Non-finite pixels and rejected flags are masked, and missing
output coverage remains transparent. Flags are read from FITS MP_* definitions,
with SOURCE and FULLSAMPLE preserved, following the supplied demo.

The provisional grouping rule splits successive exposures when the time gap
exceeds 30 days. PNGs use a shared 2nd to 99.5th percentile asinh stretch.
Results include an EXPERIMENTAL_GROUPING warning. Nguyen must review grouping,
wavelength compatibility, PSF and background matching before scientific use.
Motion validation and scientifically qualified difference images remain team
integration work.

Live mode queries the selected SIA2 collection, uses actual column names and
publisher IDs, and downloads cutouts with a 120 second timeout and three
attempts. Requests selecting more than 40 images fail and should be narrowed
with t_min/t_max. This training bound keeps individual jobs manageable.
Fixture mode reads the prepared pack index and processes the original local
FITS again. Its available time coverage is limited to the pack.

## Cache and job lifetime

The request key includes validated coordinates at their existing precision,
cutout side, detector, collection, time bounds, data source mode and pipeline
version. Fixture identity hashes its index, CSV and FITS contents.

Live results represent an archive snapshot cached for one hour. Source
product revision URLs remain in response metadata. Source refresh and separate
raw-product caching can be expanded when the archive integration matures.
Successful empty results expire after 60 seconds. Failed jobs remain visible
for five minutes and a repeated frames request can start a fresh attempt.

DiskCache stores the JSON result and all PNG bytes together as a single bundle.
Publishing is atomic and eviction removes the bundle together. The configured
cache has a 512 MiB limit. Evicted or expired jobs/images return 404, prompting
the frontend to submit its frames request again.

An active job record has a 30 minute lease refreshed at processing stages.
Work runs in an in-process thread pool. A killed server loses active execution.
After the lease expires, submit the request again. Completed cache entries
survive a restart until expiry or eviction. Automatic job resumption and
coordination across multiple worker processes are further work.

## Stage timing

Each job logs its ID, stage, outcome and duration in milliseconds. Stages are
`discovery`, `download`, `reproject`, `stack`, `render`, `publish` and
`total`. The repeated download/reproject entries measure individual images.
Cache hits and misses are logged separately. The existing request middleware
continues to measure HTTP response preparation time.

For asynchronous work, Server-Timing on the first HTTP 202 measures accepting
the request. Job stage logs measure the subsequent background processing.

## Try it in Swagger

Set these values in the root .env and restart with `npm run dev:be`.

```dotenv
FRAMES_MODE=pipeline
PIPELINE_SOURCE=live
```

Open /docs on the API host and port configured in .env. In GET /api/frames,
use this bounded Barnard example.

| Field | Value |
| --- | --- |
| s_ra | 269.44636864652 |
| s_dec | 4.766880108377093 |
| obs_collection | spherex_qr2 |
| energy_bandpassname | SPHEREx-D6 |
| cutout_size_deg | 0.05 |
| t_min | 60902.8 |
| t_max | 60903.2 |

Expect HTTP 202 on a cold cache. Copy job_id into GET /api/jobs/{job_id}
and execute until status is succeeded. Open result.frames[0].image_url
against the backend origin. This example combines five exposures into one
frame from the same time group. Request /api/frames again to see HTTP 200 and
X-Cache HIT.

For an offline run set PIPELINE_SOURCE=fixture, using the Day 5 prepared pack.
That mode returns data_kind mock. Live mode returns data_kind observational
and retains the experimental processing warning.

API changes are described in shared/api-contract/openapi.yaml version 0.2.0
and generated Swagger. Duy Hoang's frontend needs to handle HTTP 202,
polling, failed jobs, HTTP 503 and expired image URLs when enabling pipeline
mode. FRAMES_MODE=mock provides the previous synchronous fixture behavior.

## Verification

The existing 25 tests and six additional pipeline/job/cache tests pass. The new tests
cover pending request deduplication, persistent completed results, safe public
failures with retry, key separation for time bounds and unknown job/image URLs.
They also cover VOTable field-name mapping and fixed-grid alignment/grouping
with synthetic FITS inputs.
The local Barnard integration produced one 30 by 30 PNG from five D6 FITS files,
then reused the completed result on a subsequent request.

The same API flow was also run against live IRSA for the bounded Barnard query
above. It queried SIA2, downloaded five D6 cutouts, created the registered median
PNG and returned a cache hit on repeat. The observed cold pipeline took about
75 seconds, dominated by downloads. This is one measured run and will vary with
network and archive latency.

## Day 7 analysis

Dong's primary task is cache plus simultaneous requests, and wrapping Nguyen's
spectrum and lightcurve functions. The secondary task is pairing with Khoi to
optimize parallel downloads.

The Day 6 job and cache provide a base for Day 7 concurrency work. Extend it
with cross-process admission limits, robust recovery from interrupted jobs,
and measured concurrent requests. Verify that different time bounds, releases,
detectors and data revisions retain distinct results.

For spectrum and lightcurve, receive Nguyen's callable functions, flux unit,
uncertainty handling, measurement method and comparable wavelength rules.
Connect their outputs to the existing response models and preserve source IDs.
The current chart endpoints still use the Day 4 synthetic fixture calculations.

For download optimization, add a bounded pool with retry/timeout behavior
that can be benchmarked against the sequential downloader. Record image count,
elapsed time and failures for the same input selection.

The group's Day 7 objective also requires data and image processing for all
five targets. Test the full frontend flow for each target after those inputs
are available. Scientific expectations and checks come from Nguyen.
