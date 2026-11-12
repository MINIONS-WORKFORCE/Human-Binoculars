// Read a sky position typed by a user into { raDeg, decDeg }.
// Rules and examples: see COORDINATES.md next to this file.

export class CoordError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "CoordError";
    this.code = code;
  }
}

const NUMBER = String.raw`[+-]?(?:\d+\.?\d*|\.\d+)`;
const DECIMAL = new RegExp(String.raw`^(${NUMBER})\s*(?:,\s*|\s+)(${NUMBER})$`);

const SECONDS = String.raw`\d{1,2}(?:\.\d*)?`;
const RA_HMS = String.raw`(\d{1,2})\s*h\s*(\d{1,2})\s*m\s*(${SECONDS})\s*s`;
const DEC_DMS = String.raw`([+-]?)\s*(\d{1,2})\s*d\s*(\d{1,2})\s*m\s*(${SECONDS})\s*s`;
const SEXAGESIMAL = new RegExp(String.raw`^${RA_HMS}\s*,?\s*${DEC_DMS}$`, "i");

// The same numbers separated by colons or spaces, as SIMBAD prints them:
// "08:55:10.831 -07:14:42.53" or "08 55 10.831 -07 14 42.53".
const RA_SEPARATED = String.raw`(\d{1,2})[: ](\d{1,2})[: ](${SECONDS})`;
const DEC_SEPARATED = String.raw`([+-]?)(\d{1,2})[: ](\d{1,2})[: ](${SECONDS})`;
const SEPARATED = new RegExp(
  String.raw`^${RA_SEPARATED}\s*(?:,\s*|\s+)${DEC_SEPARATED}$`,
);

// Unicode minus (copied from Wikipedia) and dashes become a plain hyphen.
function normalize(input) {
  return String(input ?? "")
    .replace(/[−‒–—]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

// True when the input should be read as coordinates rather than an object name:
// it starts with a digit, sign or dot and only uses digits, signs, separators and h/m/s/d.
// "M31" and "R Dra" are names; "25h00m00s +10d00m00s" is (invalid) coordinates.
export function looksLikeCoordinates(input) {
  const text = normalize(input);
  return /^[\d+\-.]/.test(text) && /^[\d\s+\-.,:hmsd]+$/i.test(text);
}

function checkMinutesSeconds(minutes, seconds, label) {
  if (minutes >= 60) {
    throw new CoordError(
      "MINUTES_OUT_OF_RANGE",
      `${label} minutes must be below 60`,
    );
  }
  if (seconds >= 60) {
    throw new CoordError(
      "SECONDS_OUT_OF_RANGE",
      `${label} seconds must be below 60`,
    );
  }
}

function checkDec(decDeg) {
  if (!(decDeg >= -90 && decDeg <= 90)) {
    throw new CoordError(
      "DEC_OUT_OF_RANGE",
      "Dec must be between -90 and +90 degrees",
    );
  }
  return decDeg === 0 ? 0 : decDeg; // turn -0 into 0
}

function parseDecimal(match) {
  const raDeg = Number(match[1]);
  const decDeg = Number(match[2]);
  if (!(raDeg >= 0 && raDeg < 360)) {
    throw new CoordError(
      "RA_OUT_OF_RANGE",
      "RA in degrees must be in [0, 360)",
    );
  }
  return { raDeg, decDeg: checkDec(decDeg) };
}

function parseSexagesimal(match) {
  const [, h, raMin, raSec, sign, d, decMin, decSec] = match;

  const hours = Number(h);
  if (hours >= 24) {
    throw new CoordError("RA_OUT_OF_RANGE", "RA hours must be below 24");
  }
  checkMinutesSeconds(Number(raMin), Number(raSec), "RA");
  checkMinutesSeconds(Number(decMin), Number(decSec), "Dec");

  // The sign comes from the text, so "-0d30m00s" stays negative.
  const decAbs = Number(d) + Number(decMin) / 60 + Number(decSec) / 3600;
  if (decAbs > 90) {
    throw new CoordError(
      "DEC_OUT_OF_RANGE",
      "Dec must be between -90 and +90 degrees",
    );
  }

  const raDeg = (hours + Number(raMin) / 60 + Number(raSec) / 3600) * 15;
  return { raDeg, decDeg: checkDec(sign === "-" ? -decAbs : decAbs) };
}

/**
 * Parse "133.795 -7.245" (decimal degrees), "08h55m10.831s -7d14m42.53s" or
 * "08:55:10.831 -07:14:42.53" / "08 55 10.831 -07 14 42.53" (RA in hours,
 * Dec in degrees) into { raDeg, decDeg }. Throws CoordError.
 */
export function parseCoordinates(input) {
  const text = normalize(input);
  if (text === "") {
    throw new CoordError("EMPTY", "Enter coordinates or an object name");
  }

  const decimal = text.match(DECIMAL);
  if (decimal) return parseDecimal(decimal);

  const sexagesimal = text.match(SEXAGESIMAL) ?? text.match(SEPARATED);
  if (sexagesimal) return parseSexagesimal(sexagesimal);

  throw new CoordError(
    "UNSUPPORTED_FORMAT",
    'Use decimal degrees ("133.795 -7.245"), h/m/s d/m/s ("08h55m10.831s -7d14m42.53s") or colons ("08:55:10.831 -07:14:42.53")',
  );
}
