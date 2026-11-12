# Five target notes for the team (English)

These are catalogue-based expectations, not SPHEREx detections from our pipeline.

## Barnard's Star
Barnard's Star is a nearby M dwarf with very large proper motion. Its selected Gaia
DR3 solution predicts about 10.39 arcsec of motion per year, making it useful for
checking whether the viewer preserves the direction of motion. The current real
centroid test passes the pmdec direction check, but does not reproduce Gaia pmra.
Sources: [SIMBAD](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=GJ+699),
Gaia DR3 4472832130942575872 (saved query and response in fixtures/sources).

## Epsilon Indi B
Epsilon Indi B is a brown-dwarf pair, classified T1V+T6V by SIMBAD. Its components
are blended at the angular scale of SPHEREx, so a measured position can describe
an unresolved photocentre rather than either component alone. The selected Gaia
solution has elevated RUWE and should be used as a search prediction with caution.
Source: [SIMBAD](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=2MASS+J22041052-5646577),
Gaia DR3 6412596012146801152.

## WISE 0855
WISE 0855 is an ultracool Y-type brown dwarf with large proper motion. Its infrared
nature makes it a useful test of wavelength-dependent visibility, but a position
prediction is not a detection. The adopted astrometry comes from the cited SIMBAD
literature solution; our bounded Gaia DR3 cone query returned no candidates.
Source: [SIMBAD](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=WISE+J085510.83-071442.5),
2021ApJS..253....7K, saved in fixtures/sources/wise-0855-simbad.txt.

## RW Aurigae
RW Aur is a young T Tauri multiple system. We retain the sourced system-level
SIMBAD astrometry rather than silently substituting one Gaia component. Any future
infrared variability claim must distinguish spectral differences, blending and
measurement errors from an actual change with time.
Source: [SIMBAD](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=RW+Aur),
2007A&A...474..653V; the two Gaia cone candidates are saved separately.

## R Draconis
R Draconis is classified as a Mira variable by SIMBAD. It is a useful photometry
training target, but all aperture measurements in our reviewed D1 sample are
rejected for saturation or coverage. The delivered chi-square demonstration is
explicitly simulated; it is not evidence of measured SPHEREx variability.
Source: [SIMBAD](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=R+Dra),
Gaia DR3 1648328016354496384.

## Claims we must not make

- We discovered a new object, a new period, or a new variability event.
- We measured proper motion more accurately than Gaia.
- A high chi-square alone proves astrophysical variability.
- A missing or rejected flux is zero, or a position prediction is a detection.
- Every nonzero FLAGS value is bad; SOURCE must not erase the star being measured.
- Our synthetic R Dra fixture is an observation, or a rejected saturated core is
  recovered by the aperture method.
