# Day 5 cache key design

A cache key identifies a reusable result for `GET /api/frames`. Two requests
may reuse the same frame list and PNGs when their validated inputs, source data
and processing settings are equivalent. The API builds the response's `query`
field from the current request and attaches the cached artifacts.

## Fields that determine the result

| Key field | Value and meaning |
| --- | --- |
| Operation and key version | Use the prefix `spherex:frames:v1:`. Spectrum and lightcurve use separate namespaces and their own input fields. |
| `s_ra`, `s_dec`, `coordinate_policy` | Requested centre in ICRS degrees. Version the coordinate policy if epoch handling or proper motion corrections change how the centre is interpreted. |
| `cutout_size_deg` | Side of the square cutout in degrees. The SIA2 source field `s_fov` describes coverage of the source image. |
| `energy_bandpassname` | Exact SIA2 detector label, for example `SPHEREx-D6`. Include a wavelength selection if the pipeline later supports one. |
| `obs_collection`, `resolved_collection` | Requested collection and the collection actually used. They match for fixture pack v1. If the API later supports fallback, QR3 requested with QR2 used has a different result identity from QR2 requested directly. |
| `t_min`, `t_max` | Optional time bounds in MJD days. Represent an omitted bound as JSON `null`. |
| `data_mode`, `input_revision` | Distinguish the local fixture from archive data. For the fixture, use a digest of the prepared index and its associated PNG contents. For live results, identify the selected products by publisher DID and product revision. Preserve input order when it affects the result. |
| `render_version`, `format` | Identify the rendering rules and output format, currently PNG. Bump the rendering version when the stretch, alignment or masking changes. If clients can choose these settings, include their effective values in the key. |

## Normalize before hashing

1. Validate with `FramesQuery`. The current contract accepts RA in
   `[0, 360)`, Dec in `[-90, 90]`, a positive cutout side up to `0.2°`,
   finite numbers and ordered time bounds. Requests with invalid values
   fail validation before key creation.
2. Use the typed values from validation. `0.05` and `0.050` become the
   same number, and `-0.0` is normalized to `0.0`. Preserve the validated
   precision for RA, Dec, cutout size and time. Keep the exact enum strings.
3. Serialize the payload as compact JSON with sorted keys and explicit
   `null` values, encode it as UTF-8 and hash it with SHA-256. In Python use
   `json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)`.
   Append the hex digest to `spherex:frames:v1:`.

**Coordinate rounding policy for v1.** Keep the validated coordinates at their
existing precision. The mock's coordinate tolerance applies when selecting
fixture frames. It does not establish a rounding grid for new cutouts.
Rounding only in the key can make two requests share a result even though
the pipeline used different centres. If the team adopts a grid later, choose
the grid from the output pixel scale and the alignment accuracy required by
the science team. Apply the same snapped centre to both key generation and
processing, and bump the key or coordinate policy version.

## Example using WISE 0855

The following payload represents a request for the fixture's WISE 0855
centre. The revision value is illustrative. At runtime it represents the
actual prepared fixture contents.

```json
{
  "coordinate_policy": "icrs-request-centre-v1",
  "cutout_size_deg": 0.05,
  "data_mode": "fixture",
  "energy_bandpassname": "SPHEREx-D6",
  "format": "png",
  "input_revision": "example-fixture-content-digest",
  "obs_collection": "spherex_qr2",
  "render_version": "v1",
  "resolved_collection": "spherex_qr2",
  "s_dec": -7.240318556371518,
  "s_ra": 133.73716032408367,
  "t_max": null,
  "t_min": null
}
```

| Change to the example request or inputs | Expected key |
| --- | --- |
| Write the cutout size as `0.050` or reorder URL parameters | Same key |
| Change RA from `133.73716032408367` to `133.73716` | Different key, even if the mock selects the same fixture frames |
| Change the cutout side from `0.05` to `0.10` | Different key |
| Change the detector to `SPHEREx-D3` or the requested collection to `spherex_qr3` | Different key |
| Supply `t_min=60800.7015` | Different key |
| Regenerate the fixture with different PNG contents or change the render version | Different key |

## When the archive pipeline is connected

Resolve the collection and identify the selected products before computing
the rendered result key. If discovery also needs caching, give it a separate
key based on the validated search request and discovery policy. Use a short
expiry for successful empty archive searches because new observations may
appear. Store processing failures separately from successful empty searches.

References in this repository include the [OpenAPI contract](../../../../shared/api-contract/openapi.yaml)
and the [backend fixture instructions](../../README.md#day-5-png-and-json-from-fixture-pack-v1).
