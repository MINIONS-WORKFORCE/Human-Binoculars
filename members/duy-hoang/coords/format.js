// Degrees -> sexagesimal text for display. Rounding happens on the total number of
// seconds first, so 59.996s becomes the next minute instead of "60.00s".

const pad = (n, width) => String(n).padStart(width, "0");

function split(totalSeconds, decimals) {
  const scale = 10 ** decimals;
  const rounded = Math.round(totalSeconds * scale) / scale;
  const units = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded - units * 3600) / 60);
  const seconds = rounded - units * 3600 - minutes * 60;
  const [whole, fraction] = seconds.toFixed(decimals).split(".");
  return {
    units,
    minutes,
    seconds: fraction ? `${pad(whole, 2)}.${fraction}` : pad(whole, 2),
  };
}

/** 133.795129 -> "08h55m10.83s". 360 wraps to "00h00m00.00s". */
export function formatRa(raDeg, decimals = 2) {
  const { units, minutes, seconds } = split((raDeg / 15) * 3600, decimals);
  return `${pad(units % 24, 2)}h${pad(minutes, 2)}m${seconds}s`;
}

/**
 * -7.245147 -> "−07°14′42.5″" (style "symbols", for display, Unicode minus)
 *           or "-07d14m42.5s" (style "letters", readable by parseCoordinates).
 */
export function formatDec(decDeg, { decimals = 1, style = "symbols" } = {}) {
  const { units, minutes, seconds } = split(Math.abs(decDeg) * 3600, decimals);
  const isZero = units === 0 && minutes === 0 && Number(seconds) === 0;
  if (style === "letters") {
    const sign = decDeg < 0 && !isZero ? "-" : "+";
    return `${sign}${pad(units, 2)}d${pad(minutes, 2)}m${seconds}s`;
  }
  const sign = decDeg < 0 && !isZero ? "−" : "+";
  return `${sign}${pad(units, 2)}°${pad(minutes, 2)}′${seconds}″`;
}
