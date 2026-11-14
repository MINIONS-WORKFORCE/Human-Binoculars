"""Adapt indexed FITS exposures to the science measurements in API 0.1."""

import math
from functools import lru_cache

from shared.pipeline.irsa import group_images_into_visits
from shared.science import astrometry, photometry
from shared.science_api import photometry_payload

from .observed_frames import verify_cutouts


@lru_cache(maxsize=32)
def measure(operation, cutouts, catalog_items, detector, aperture_arcsec=None):
    groups = group_images_into_visits(
        [{"t_min": cutout.mjd, "cutout": cutout} for cutout in cutouts]
    )
    # Match the visit numbering used by the API 0.1 renderer.
    selected = [
        (survey, entry["cutout"])
        for survey, group in enumerate(groups, start=1)
        for entry in group
        if detector is None or entry["cutout"].detector == detector
    ]
    verify_cutouts(cutout for _, cutout in selected)
    entries = [
        {
            "path": cutout.path,
            "mjd": cutout.mjd,
            "detector": cutout.detector,
            "release": cutout.release,
            "survey": survey,
            "data_kind": "observational",
        }
        for survey, cutout in selected
    ]
    catalog = dict(catalog_items)
    if operation == "astrometry":
        return astrometry(entries, catalog)
    result = photometry(entries, catalog, aperture_arcsec, diagnostics=True)
    # API 0.1 requires a wavelength for each point. A failed wavelength
    # evaluation cannot be published using a nominal detector wavelength.
    result["points"] = [
        point for point in result["points"]
        if (wave := point["wavelength_um"]) is not None and math.isfinite(wave) and wave > 0
    ]
    return photometry_payload(result)
