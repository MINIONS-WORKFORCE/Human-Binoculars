# Frontend API integration guide

This guide matches the Day 6 backend on branch `dong/frames-jobs-cache`
and API contract v0.2.0. Use the backend's /docs page to try requests.

## Connection settings

Set VITE_API_BASE_URL in the frontend environment to the backend origin,
including its port, and restart Vite after changes. Use the backend address
agreed with Dong. For example, if the backend listens on port 3000,
set VITE_API_BASE_URL=http://localhost:3000.

Dong configures these values in the backend's root .env.

```dotenv
FRAMES_MODE=pipeline
PIPELINE_SOURCE=live
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Restart the backend after changes. CORS origins must match the frontend's
actual scheme, hostname and port. The public training configuration can use
CORS_ALLOW_ORIGINS=*. Requests use GET and omit credentials.

When sharing a deployed frontend, configure a backend origin reachable by its
users. In a browser, localhost refers to the computer running that browser.

## Request parameters

| Parameter | Required for frames | Meaning |
| --- | --- | --- |
| s_ra | Yes | Requested ICRS centre in degrees, 0 inclusive to 360 exclusive |
| s_dec | Yes | Requested ICRS centre in degrees, -90 to +90 |
| obs_collection | Yes | spherex_qr2, spherex_qr2_deep, spherex_qr3 or spherex_qr3_deep |
| energy_bandpassname | Yes | SPHEREx-D1 through SPHEREx-D6 |
| cutout_size_deg | Yes | Square cutout side in degrees, greater than 0 and at most 0.2 |
| t_min, t_max | No | Time bounds in MJD days. Omit unset bounds. Send t_min <= t_max |

Map a UI field for square FOV to cutout_size_deg. Convert arcminutes to degrees
when necessary. Source metadata's s_fov represents the original detector image
coverage. The application endpoints accept the parameter names in this table.

## Barnard and WISE 0855 presets

Both target fields can be processed by the parameterized pipeline.
Use these bounded queries for initial integration.

| Parameter | Barnard's Star | WISE 0855 |
| --- | --- | --- |
| s_ra | 269.44636864652 | 133.73716032408367 |
| s_dec | 4.766880108377093 | -7.240318556371518 |
| obs_collection | spherex_qr2 | spherex_qr2 |
| energy_bandpassname | SPHEREx-D6 | SPHEREx-D6 |
| cutout_size_deg | 0.05 | 0.05 |
| t_min | 60902.8 | 60800.6 |
| t_max | 60903.2 | 60801.2 |
| Expected result | 5 exposures combined into 1 frame | 3 exposures combined into 1 frame |

These centres come from the existing fixture search coordinates and are useful
for reproducing this training setup. Coordinate epoch and target identification
require science review before presenting a measured object position.

One frame represents a time group. The current experimental grouping splits at
gaps greater than 30 days. These short presets exercise loading and display.
Choose a wider observation interval to explore multiple groups. Live requests
selecting more than 40 exposures fail; narrow the time range if that happens.

With PIPELINE_SOURCE=fixture the same presets process local FITS from the
prepared Day 5 pack. The fixture has limited time coverage. With
PIPELINE_SOURCE=live the backend queries IRSA and downloads the selected cutouts.

## Frames request and job polling

1. Send GET /api/frames with URL-encoded parameters.
2. HTTP 200 contains the completed frames response directly.
3. HTTP 202 contains job_id, status and status_url. Poll status_url about
   every two seconds. Continue while status is queued or running.
4. When status becomes succeeded, consume the job response's result.
5. When status becomes failed, display error.message and offer a user-triggered
   retry of the original frames request.

A pending response looks like this. The ID is illustrative.

```json
{
  "job_id": "example-job-id",
  "status": "queued",
  "status_url": "/api/jobs/example-job-id"
}
```

GET /api/jobs/{job_id} returns HTTP 200 for all existing job states, including
failed. Always inspect the status field. A succeeded response wraps the frames
response in result. A warm GET /api/frames returns that frames response directly.
The API exposes states rather than percentage progress.

The following browser module handles direct results, polling, errors,
cancellation and an overall timeout.

```javascript
export async function loadFrames(
  apiOrigin,
  params,
  { signal, timeoutMs = 600_000 } = {},
) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) abort();
  signal?.addEventListener("abort", abort, { once: true });
  const timer = setTimeout(abort, timeoutMs);
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(name, String(value));
    }
  }
  const url = (path) => new URL(path, apiOrigin).href;
  async function get(path) {
    const response = await fetch(url(path), {
      signal: controller.signal,
      credentials: "omit",
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(
        body.error?.message ?? body.detail ?? `HTTP ${response.status}`,
      );
    }
    return { response, body };
  }
  async function pause() {
    await new Promise((resolve, reject) => {
      if (controller.signal.aborted) {
        reject(new DOMException("Request cancelled or timed out", "AbortError"));
        return;
      }
      const cancel = () => {
        clearTimeout(wait);
        reject(new DOMException("Request cancelled or timed out", "AbortError"));
      };
      const wait = setTimeout(() => {
        controller.signal.removeEventListener("abort", cancel);
        resolve();
      }, 2000);
      controller.signal.addEventListener("abort", cancel, { once: true });
    });
  }
  try {
    const { response, body } = await get(`/api/frames?${query}`);
    if (response.status === 200) return body;
    const statusUrl = body.status_url;
    for (;;) {
      await pause();
      const { body: job } = await get(statusUrl);
      if (job.status === "succeeded") return job.result;
      if (job.status === "failed") {
        throw new Error(job.error?.message ?? "Frame processing failed");
      }
      if (!["queued", "running"].includes(job.status)) {
        throw new Error("Unexpected job status");
      }
    }
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}
```

Call it with import.meta.env.VITE_API_BASE_URL and a preset above. On target
changes, abort the previous call and ignore its stale completion. Cancellation
stops the browser waiting; an accepted backend job can continue processing.

## Displaying frames

Use result.frames for the player. Each item includes frame_id, image_url,
observation_time, t_min/t_max, n_images, detector, collection and source IDs.
Resolve each image_url against VITE_API_BASE_URL, even when it starts with
/mock/. Paths are supplied by the backend and can change between modes.

```javascript
const imageUrl = new URL(frame.image_url, import.meta.env.VITE_API_BASE_URL).href;
```

Preload the images, then blink them in the returned time order. Maintain the
selected frame index as player state. Resolve frame.source_obs_publisher_dids
against result.sources to display provenance. Source s_ra/s_dec describe source
images, while result.query describes the requested centre.

The returned PNG is 30 by 30 pixels for the pipeline's 0.05 degree preset.
It can be displayed larger while preserving pixel boundaries.

```css
.sky-frame {
  width: 360px;
  max-width: 100%;
  height: auto;
  image-rendering: pixelated;
  background: #080b18;
}
```

Missing coverage is transparent, so the background also controls the appearance
of excluded edges. Show frame time, n_images and warnings near the image.
data_kind distinguishes mock fixtures from observational input. Current live
frames retain an EXPERIMENTAL_GROUPING warning because grouping and wavelength
comparison require science validation.

## Empty data, failures and cache

| Situation | Frontend action |
| --- | --- |
| Completed result has frames=[] | Show an empty state. Read warnings such as NO_DATA |
| HTTP 422 | Display error.message and identify invalid fields from error.fields |
| HTTP 503 from /api/frames | Worker capacity reached. Offer retry after a delay |
| Job status failed | Display error.message. A deliberate new request can retry |
| Job or image returns HTTP 404 | Cache expired/evicted. Resubmit the original frames request and reload new URLs |
| Fetch/network error | Check backend availability, base URL and CORS; keep retry available |
| AbortError | The request was cancelled or its browser-side timeout elapsed |

Successful nonempty pipeline results remain cached for up to one hour, empty
results for 60 seconds, subject to cache eviction. Successful jobs include their
PNG bytes in the same cache item. Keep the original query so an expired image
can be requested again. Use onError for an img element or check fetch status
when loading image blobs.

X-Cache reports HIT or MISS on completed/cache-miss frame requests.
Server-Timing measures HTTP response preparation. Initial HTTP 202 timing covers
job admission; background processing durations appear in backend stage logs.
The backend currently admits two active jobs per worker. Poll an existing job
instead of repeatedly submitting new requests while it is pending.

## Spectrum and lightcurve

GET /api/spectrum requires s_ra, s_dec and obs_collection.
GET /api/lightcurve additionally requires energy_bandpassname.
Both accept optional t_min/t_max and currently return synchronous mock JSON.

For these Day 4 chart fixtures use s_ra=133.79513, s_dec=-7.24515,
obs_collection=spherex_qr2, and SPHEREx-D6 for lightcurve. The charts'
fixture coordinates differ from the Day 6 frames presets. Valid queries for
other targets may return empty points with MOCK_TARGET_ONLY and NO_DATA.
Use the chart responses' unit, measurement_method, data_kind and warnings.
Current fluxes and chart wavelengths are synthetic UI examples.

## Frontend acceptance checklist

- Both presets can complete loading and open their PNG URLs.
- HTTP 200 and HTTP 202 flows both reach the player.
- One-frame results keep a valid selected frame and show exposure count.
- Empty results and failed/expired jobs have visible states.
- A changed target cancels polling for the previous selection.
- The deployed frontend uses a reachable backend origin and allowed CORS origin.

See the [OpenAPI contract](openapi.yaml) for response schemas and
[Day 6 delivery](../../members/dong/docs/day06-frames-jobs-cache.md)
for backend setup and processing limits.
