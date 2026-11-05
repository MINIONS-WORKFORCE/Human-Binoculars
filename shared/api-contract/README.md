# API contract

Đông puts `openapi.yaml` here on 4/11, covering `/api/frames`, `/api/spectrum` and `/api/lightcurve`, with field names taken from the real SIA2 columns.

Frontend (Duy Hoàng, Thạch) and image processing (Hữu Hoàng) build against this file. Any change goes through a PR that tags all three.

## Contract v0

[openapi.yaml](openapi.yaml) describes three GET endpoints for review and mock
development. The backend now implements `/health` and all three endpoints in
mock mode. Its `/docs` page exposes the implemented Pydantic request and response
models; this YAML remains the shared contract. See
[the backend README](../../members/dong/README.md#day-4-mock-endpoints) for setup,
example requests and the WISE 0855 fixture limitations.

| Endpoint | Required parameters | Main output |
| --- | --- | --- |
| `/api/frames` | `s_ra`, `s_dec`, `obs_collection`, `energy_bandpassname`, `cutout_size_deg` | `frames`, PNG URLs, observation times and `sources` |
| `/api/spectrum` | `s_ra`, `s_dec`, `obs_collection` | Wavelength `points`, fluxes, uncertainties and `sources` |
| `/api/lightcurve` | `s_ra`, `s_dec`, `obs_collection`, `energy_bandpassname` | Time-ordered `points` in a common wavelength range and `sources` |

All three endpoints accept optional `t_min` and `t_max` bounds in MJD days.
When both are supplied, `t_min` must be less than or equal to `t_max`. A single
bound leaves the other end open. The response `query` echoes the normalized
request parameters and omits time bounds that were not supplied.

Append this example application API path to the configured backend address:

```text
/api/frames?s_ra=133.79513&s_dec=-7.24515&obs_collection=spherex_qr2&energy_bandpassname=SPHEREx-D6&cutout_size_deg=0.05
```

## Field names and IRSA mapping

Metadata names were checked against the 51 column headers in the actual SIA2
response for the WISE 0855 QR2 query. The `SourceObservation` schema preserves
names such as
`obs_id`, `obs_publisher_did`, `obs_collection`, `energy_bandpassname`, `s_ra`,
`s_dec`, `t_min`, `t_max`, `access_url`, `access_format`, `s_region`, `s_fov`,
`em_min` and `em_max`. The YAML `x-sia2-column` annotation records the source
column for each field.

| Application API parameter | Mapping to IRSA |
| --- | --- |
| `s_ra`, `s_dec` | Requested centre in ICRS degrees, used to construct `POS`. Source-image centres are stored separately in `sources[].s_ra/s_dec`. |
| `obs_collection` | Maps to SIA2 `COLLECTION`, using the exact values `spherex_qr2`, `spherex_qr2_deep`, `spherex_qr3` or `spherex_qr3_deep`. Do not silently switch releases for empty results. |
| `energy_bandpassname` | Filters the metadata column of the same name using `SPHEREx-D1` through `SPHEREx-D6`. This is not a parameter name of the SIA2 endpoint. |
| `t_min`, `t_max` | Map to a `TIME` interval in MJD. Do not send ISO strings as SIA2 TIME values. |
| `cutout_size_deg` | Application field: square cutout side length in degrees, greater than 0 and at most 0.2 degrees in v0. The constructed POS region must cover the entire cutout. |

The metadata field `s_fov` describes the source-image footprint size. Do not
repurpose it as a search radius or cutout size. `access_url` always refers to
the source data; processed PNG URLs belong in the application field `image_url`.

## Output data rules

- `frames`, `points`, `image_url`, `frame_id`, `data_kind`, `flux`, `flux_error`,
  `wavelength_um`, `time_mjd` and `measurement_method` are application-generated
  fields, not SIA2 columns.
- `sources` contains the input products. Each frame or measurement references
  them through `source_obs_publisher_dids`. Do not use `obs_id` alone as a file
  key because one observation may have multiple detectors. Product identifiers
  in `sources` must be unique.
- Each frame uses one detector and one collection. `n_images` equals the number
  of distinct source identifiers used. Its `t_min/t_max` span the earliest and
  latest contributing times. Source observations must overlap the requested
  time range when a time constraint is supplied.
- Sort `frames` and light curve points by increasing time, and spectrum points
  by increasing wavelength. A frame may combine multiple source images.
- A frame's `observation_time` is the midpoint of its time interval in ISO UTC.
  A light curve point's `time_mjd` is also the midpoint of its contributing
  time interval.
- Source `em_min/em_max` use metres; `wavelength_um` and the light curve
  wavelength range use micrometres. `flux` and `flux_error` use `flux_unit`.
- Unavailable fluxes or uncertainties are `null`, never substituted with 0.
  Available uncertainties must be nonnegative. Nonempty measurements must
  declare their unit and measurement method.
- HTTP 200 with an empty list and a `NO_DATA` warning means the query succeeded
  but found no suitable data. If no measurement has been evaluated, set
  `flux_unit`, `measurement_method` and the light curve wavelength range to `null`.
- Populated YAML examples are synthetic and carry `data_kind: mock` and a
  `MOCK_DATA` warning. The `example.org` and `/mock/` URLs are illustrative and
  do not point to real observations.

Schemas validate types, individual value ranges and required fields. The backend
must enforce cross-field rules such as time ordering, source references,
midpoint calculations and unit consistency when implementing the endpoints.

## Common errors

All errors use the same `error.code`, `error.message`, `error.fields` structure.

| HTTP | Code | When to use |
| --- | --- | --- |
| 422 | `VALIDATION_ERROR` | Invalid coordinates, detector, collection, size or time bounds. |
| 502 | `UPSTREAM_ERROR` | IRSA failed or returned an unusable response. |
| 504 | `UPSTREAM_TIMEOUT` | IRSA exceeded the request timeout. |
| 500 | `PROCESSING_ERROR` | Local pipeline processing failed. |

When implementing FastAPI, convert its default validation errors into this
structure. Never expose secrets, local file paths or tracebacks in error messages.

## Team decisions required before live data processing

1. Nguyên and Hữu Hoàng must confirm survey-pass grouping, comparable wavelength
   selection and quality checks. The same detector does not guarantee the same
   wavelength because of the LVF.
2. Nguyên must confirm the measurement method, background treatment, aperture,
   uncertainty calculation and flux unit. The mock examples' `mJy` unit does not
   prescribe the scientific measurement method.
3. The team must confirm the v0 cutout limit of 0.2 degrees using Khôi's benchmarks.
4. V0 returns results synchronously. Before integrating a slow pipeline, Đông and
   the frontend developers must extend the contract with a background job
   protocol, polling and result retention.

Sources: [IRSA SIA2](https://irsa.ipac.caltech.edu/ibe/sia.html) and
[SPHEREx Data Access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/).
