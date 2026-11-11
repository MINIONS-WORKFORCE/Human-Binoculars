// E6 /api/photometry responses for trying the chart before real measurements exist.
// SHARED_SAMPLE is the team's api_samples/photometry_rdra.json. SYNTHETIC_RDRA is made up
// here to exercise every rule (upper limits, flags, reference star, missing values,
// several surveys); none of its values is a SPHEREx or R Draconis measurement.

import SHARED_SAMPLE from "../../../../api_samples/photometry_rdra.json";

export { SHARED_SAMPLE };

// Three surveys about six months apart inside the QR2 period (MJD 60800–61174).
const SURVEYS = [
  { survey: 1, mjd: 60812, brightness: 1.0 },
  { survey: 2, mjd: 60996, brightness: 0.42 },
  { survey: 3, mjd: 61165, brightness: 0.8 },
];
// Detector, a wavelength inside its band (it shifts a little between surveys
// because of the LVF), and a made-up flux at full brightness.
const DETECTORS = [
  { detector: 1, wavelength: 0.93, flux: 8 },
  { detector: 2, wavelength: 1.36, flux: 20 },
  { detector: 3, wavelength: 2.02, flux: 34 },
  { detector: 4, wavelength: 3.1, flux: 26 },
  { detector: 5, wavelength: 4.1, flux: 15 },
  { detector: 6, wavelength: 4.7, flux: 11 },
];

const round = (value, digits = 2) => Number(value.toFixed(digits));

function measure(flux, err) {
  const snr = round(flux / err, 1);
  return {
    flux_mjy: round(flux),
    err_mjy: round(err),
    snr,
    detected: snr >= 3,
  };
}

function point(survey, detector, values, extra = {}) {
  return {
    frame_id: `synthetic-s${survey.survey}-d${detector.detector}`,
    mjd: round(survey.mjd + detector.detector * 0.6),
    wavelength_um: round(detector.wavelength + 0.03 * survey.survey),
    detector: detector.detector,
    release: "qr2",
    survey: survey.survey,
    flagged: false,
    is_reference_star: false,
    ...values,
    ...extra,
  };
}

const target = SURVEYS.flatMap((survey) =>
  DETECTORS.map((detector) => {
    const key = `${survey.survey}-${detector.detector}`;
    // Faint at the dim phase in D1 and D6: below SNR 3, so drawn as upper limits.
    if (key === "2-1") return point(survey, detector, measure(0.9, 0.5));
    if (key === "2-6") return point(survey, detector, measure(1.1, 0.6));
    // No usable measurement at all.
    if (key === "3-2") {
      return point(survey, detector, {
        flux_mjy: null,
        err_mjy: null,
        snr: null,
        detected: false,
      });
    }
    const flux = detector.flux * survey.brightness;
    const values = measure(flux, 0.06 * flux + 0.4);
    // Bright phase in D3: the aperture touches saturated pixels.
    return point(survey, detector, values, { flagged: key === "1-3" });
  }),
);

// A steady comparison star in D3 and D4.
const reference = SURVEYS.flatMap((survey) =>
  DETECTORS.filter(({ detector }) => detector === 3 || detector === 4).map(
    (detector) =>
      point(survey, detector, measure(5 + 0.1 * survey.survey, 0.3), {
        frame_id: `synthetic-s${survey.survey}-d${detector.detector}-ref`,
        is_reference_star: true,
      }),
  ),
);

export const SYNTHETIC_RDRA = {
  api_version: "0.1",
  target: SHARED_SAMPLE.target,
  reference_star: {
    gaia_source_id: "synthetic-reference",
    ra: 248.21,
    dec: 66.73,
  },
  points: [...target, ...reference],
  variability: {
    chi2_reduced: 14.2,
    dof: 15,
    is_variable: true,
    method: "chi2_vs_reference",
  },
};
