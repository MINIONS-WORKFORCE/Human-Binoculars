# Synthetic API examples for Issue 14

All JSON values and PNG pixels in this directory are synthetic UI/schema
examples. The catalog-shaped values are not verified measurements.
Six JSON files are validated by members/dong/scripts/validate_api_samples.py.
Six 39 by 39 grayscale PNGs are marked FIX and use PNG top-left coordinates.
The artificial source moves along y=19, x=17,19,21. predicted_px matches this
position. Difference images subtract the first sample with gray 128 at zero.

E3 echoes valid request coordinates, detector and target label. All five
target keys reuse these illustrative pixels and science examples. size and
aperture_arcsec are validated but do not perform new crops or measurements.
The fixture resolver covers Barnard aliases only. Additional authoritative
resolver entries belong to Khoi. Live adapters await later team integration.

These small synthetic assets are explicitly required by Issue 14 and are
committed for MSW/schema checks. Observational FITS and local data/cache files
continue to belong under ignored data/ storage.
