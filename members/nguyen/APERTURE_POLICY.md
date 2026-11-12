# Aperture decision — issues #23 / #36

- `aperture_arcsec = 12.3` means **radius**, not diameter (diameter 24.6 arcsec).
- This adopts the explicit two-nominal-pixel engineering default in the wiki E6
  draft. It is a fixed angular aperture converted through each native cutout WCS.
- Local background: annulus 49.2–86.1 arcsec (8–14 nominal pixels), with SOURCE
  pixels excluded and 3-sigma clipping. The wider annulus keeps ordinary PSF wings
  out of the background; a minimum 20 pixels and 20% annular area must survive.
- IMAGE is corrected by the supplied ZODI model when present. Its model error is
  not provided by VARIANCE and is not included in the reported random error.
- Per-pixel SAPM (arcsec2 -> sr) is used when supplied. The WCS-area fallback is
  explicitly warned. The current reviewed QR2 replay always supplies SAPM.
- Error uses squared fractional pixel weights plus the propagated uncertainty of
  the selected background mean; correlations and calibration systematics remain.
- SOURCE and FULLSAMPLE are informational for the source aperture. Background
  excludes SOURCE. Other set bits, including unknown bits, are rejected.
- Any OVERFLOW in the aperture rejects its flux with SATURATED; missing flux is
  null, never zero. This code does not fill saturated cores or infer their flux.

The 1, 1.5, 2 and 3-pixel radius sweep on the reviewed real R Dra sample produces
no acceptable aperture flux at any radius. Thus 12.3 arcsec is a documented default,
**not an empirically optimized or scientifically validated aperture for R Dra**.
Do not override FLAGS to obtain a numerical light curve. A future trustworthy
saturated-star measurement needs a separately validated PSF method or suitable
unsaturated observations, with error and quality checks.

References: [IRSA product definitions](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/),
[IRSA photometry and flags](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html).
