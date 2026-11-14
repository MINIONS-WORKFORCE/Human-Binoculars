# NASA resource alignment — 14 November 2026

## Official resources

The challenge resources identify IRSA for SPHEREx data, Caltech-IPAC tutorial notebooks for Python access, WiseView as a time-domain viewer reference, and Gaia DR3 for astrometric cross-checks. The current IRSA archive lists DR1 and QR3 as the November 2026 products. QR2 remains an older Quick Release for historical coverage.

## Repository comparison

| Area | Before | After this update |
| --- | --- | --- |
| Live collection | `.env` selected DR1, but shared query helper defaulted to QR2 | Shared live query helper follows `SPHEREX_COLLECTION`, defaulting to DR1 |
| Target survey utility | QR2, epoch J2025.5 | Configured collection, epoch J2026.0 default |
| Five-target fixture builder | Hardcoded QR2 queries and manifest | Uses configured collection and records actual release |
| Existing fixture manifest | QR2 IDs and local files | Retained as historical QR2 fixture with explicit release metadata |
| API samples | Synthetic schema examples | Retained and labelled mock, never presented as NASA observations |
| Science snapshot | QR2 D1 selected 10/11 | Retained as reproducible historical validation. New live queries use DR1/QR3 configuration |

## Data policy

Competition live mode uses `SPHEREX_COLLECTION=spherex_dr1` and
`SPHEREX_COLLECTION_FALLBACK=spherex_qr3`. QR2 can be selected explicitly for
historical coverage. Manifests and responses must preserve the actual collection.
Synthetic JSON is mock. FITS returned by IRSA is observational.

## References

- Challenge resources: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources
- IRSA releases: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/
- SPHEREx products: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/
- Tutorials: https://caltech-ipac.github.io/irsa-tutorials/
- IRSA: https://irsa.ipac.caltech.edu/
- Gaia DR3: https://www.cosmos.esa.int/web/gaia/dr3
- WiseView: https://byw.tools/wiseview/


## Live IRSA comparison performed on 14 November 2026

The same propagated J2026.0 positions were queried against DR1 and QR3.

| Target | DR1 total | QR3 total | Observation |
| --- | ---: | ---: | --- |
| Barnard's Star | 265 | 130 | Both releases have coverage. DR1 is deeper for this query. |
| WISE 0855-0714 | 288 | 0 | QR3 has no coverage at the propagated position in this query. |
| Epsilon Indi B | 372 | 121 | QR3 has zero D1 and D4 frames. |
| RW Aurigae | 242 | 126 | Both releases have coverage. |
| R Draconis | 461 | 131 | Both releases have coverage. |

This is a live IRSA coverage query, not a detection claim. Counts depend on the
position, search radius, detector and archive state. The fixture files in the repo
are still a reproducible local pack and do not become DR1 automatically.
