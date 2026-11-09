// SYNTHETIC responses in the shape of the API contract, for building the charts before
// real JSON exists. No value here is a SPHEREx measurement; each carries MOCK_DATA.

const MOCK_WARNING = {
  code: "MOCK_DATA",
  message: "Synthetic example only; not a SPHEREx measurement.",
};
const SATURATED = {
  code: "SATURATED",
  message: "Star core is saturated in this image.",
};
const DIDS = ["ivo://example.org/spherex/mock-001"];

const QUERY = {
  s_ra: 248.16761,
  s_dec: 66.75498,
  obs_collection: "spherex_qr2",
};

function bandFor(wavelength) {
  if (wavelength <= 1.09) return "SPHEREx-D1";
  if (wavelength <= 1.62) return "SPHEREx-D2";
  if (wavelength <= 2.41) return "SPHEREx-D3";
  if (wavelength <= 3.82) return "SPHEREx-D4";
  if (wavelength <= 4.41) return "SPHEREx-D5";
  return "SPHEREx-D6";
}

const SPECTRUM_WAVELENGTHS = Array.from(
  { length: 42 },
  (_, index) => 0.8 + index * 0.1,
);

// A smooth made-up curve with a little fixed scatter, so every run looks the same.
function syntheticFlux(wavelength, index) {
  const curve = 40 * Math.exp(-((wavelength - 1.9) ** 2) / 1.6) + 6;
  return curve + 1.4 * Math.sin(index * 2.4);
}

function spectrumPoint(wavelength, index, overrides = {}) {
  const flux = syntheticFlux(wavelength, index);
  return {
    wavelength_um: wavelength,
    flux: Number(flux.toFixed(2)),
    flux_error: Number((0.6 + flux * 0.03).toFixed(2)),
    energy_bandpassname: bandFor(wavelength),
    t_min: 61000,
    t_max: 61000.1,
    source_obs_publisher_dids: DIDS,
    warnings: [],
    ...overrides,
  };
}

const spectrumResponse = (points, extraWarnings = []) => ({
  data_kind: "mock",
  query: QUERY,
  wavelength_unit: "um",
  flux_unit: "mJy",
  measurement_method: "mock_fixture",
  points,
  sources: [],
  warnings: [MOCK_WARNING, ...extraWarnings],
});

export const SPECTRUM_SAMPLE = spectrumResponse(
  SPECTRUM_WAVELENGTHS.map((wavelength, index) =>
    spectrumPoint(wavelength, index),
  ),
);

export const SPECTRUM_WITH_WARNINGS = spectrumResponse(
  SPECTRUM_WAVELENGTHS.map((wavelength, index) => {
    if (index === 30) return spectrumPoint(wavelength, index, { flux: null });
    if (index === 34) {
      return spectrumPoint(wavelength, index, { flux_error: null });
    }
    if (index >= 9 && index <= 13) {
      return spectrumPoint(wavelength, index, { warnings: [SATURATED] });
    }
    return spectrumPoint(wavelength, index);
  }),
);

const LIGHTCURVE_TIMES = [
  60812, 60816, 60821, 60825, 60990, 60995, 61001, 61006, 61150, 61156, 61162,
  61168,
];

function lightcurvePoint(mjd, index, overrides = {}) {
  const flux = 22 + 14 * Math.sin((mjd / 245) * 2 * Math.PI);
  return {
    time_mjd: mjd,
    t_min: mjd - 0.05,
    t_max: mjd + 0.05,
    flux: Number((flux + 0.5 * Math.sin(index * 2.4)).toFixed(2)),
    flux_error: 0.9,
    source_obs_publisher_dids: DIDS,
    warnings: [],
    ...overrides,
  };
}

const lightcurveResponse = (points, extraWarnings = []) => ({
  data_kind: "mock",
  query: { ...QUERY, energy_bandpassname: "SPHEREx-D3" },
  time_unit: "MJD day",
  flux_unit: "mJy",
  measurement_method: "mock_fixture",
  wavelength_min_um: 2.1,
  wavelength_max_um: 2.2,
  points,
  sources: [],
  warnings: [MOCK_WARNING, ...extraWarnings],
});

export const LIGHTCURVE_SAMPLE = lightcurveResponse(
  LIGHTCURVE_TIMES.map((mjd, index) => lightcurvePoint(mjd, index)),
);

export const LIGHTCURVE_WITH_WARNINGS = lightcurveResponse(
  LIGHTCURVE_TIMES.map((mjd, index) => {
    if (index === 5) return lightcurvePoint(mjd, index, { flux: null });
    if (index === 9) {
      return lightcurvePoint(mjd, index, { warnings: [SATURATED] });
    }
    return lightcurvePoint(mjd, index);
  }),
);

const NO_DATA = {
  code: "NO_DATA",
  message: "No suitable observations match the query.",
};

export const SPECTRUM_EMPTY = {
  data_kind: "observational",
  query: QUERY,
  wavelength_unit: "um",
  flux_unit: null,
  measurement_method: null,
  points: [],
  sources: [],
  warnings: [NO_DATA],
};

export const LIGHTCURVE_EMPTY = {
  data_kind: "observational",
  query: { ...QUERY, energy_bandpassname: "SPHEREx-D3" },
  time_unit: "MJD day",
  flux_unit: null,
  measurement_method: null,
  wavelength_min_um: null,
  wavelength_max_um: null,
  points: [],
  sources: [],
  warnings: [NO_DATA],
};
