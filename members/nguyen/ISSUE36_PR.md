## What

Refs #36. Add original-FITS aperture photometry and Gaussian-centroid astrometry,
CSV measurement exports, and projections validated against main's API 0.1 models.
Choose aperture_arcsec=12.3 as a radius; preserve rejected rows and diagnostics.
Keep the existing frontend API samples, OpenAPI, routes and shared target table.

## How to try it

From the repo root with Python 3.12 dependencies installed:

```powershell
python -m pytest members/nguyen/tests -q
python members/dong/scripts/validate_api_samples.py
python members/nguyen/build_samples.py
python members/nguyen/issue36.py data/science_acceptance_mock/rdra-manifest.json --output data/issue36/rdra
python members/nguyen/issue36.py data/science_acceptance_mock/barnard-manifest.json --output data/issue36/barnard
```

See members/nguyen/ISSUE36_HANDOFF.md for the real-data replay and full handoff.

## Output and limits

Real Barnard: 8 centroids, 196.558 days, pmdec=+8745.199 +/-571.065 mas/yr,
matching Gaia's positive direction. pmra disagrees with Gaia; warning retained.
R Dra: real CSV has 32 rejected rows (31 saturated, 1 coverage), zero valid fluxes.
The separate mock CSV has 20 valid target points and 40 control-star points.
No real R Dra variability or valid saturated-core flux is claimed. E6 requires
an integer survey/visit index; the real snapshot needs that team metadata before
an API payload can be exported. Detailed tables remain available meanwhile.

## Checklist

- [x] Science tests pass; current 6 team API samples validate.
- [x] No FITS, cutouts, database, secrets or notebook outputs in submission.
- [x] Receiver has inputs, units, run commands and explicit scientific limits.
- [x] No endpoint fields or existing frontend samples changed.
- [ ] Nguyen completes rebase and repeats checks on the resulting branch.
- [ ] Owner reviews shared modules and accepts the rejected-real/mock table distinction.
- [ ] Dong connects science functions to HTTP routes; this PR supplies functions only.

Review reference: main f8541d106894b6e921eb8a165cb7fbcadfe66908, checked 2026-11-12.
