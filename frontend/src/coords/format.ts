// Degrees -> text for display. Ported from members/duy-hoang/coords/format.js.
// Rounding happens on the total number of seconds first, so 59.996 s becomes
// the next minute instead of "60.00s".

const pad = (n: number | string, width: number) =>
  String(n).padStart(width, "0");

function split(totalSeconds: number, decimals: number) {
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
export function formatRa(raDeg: number, decimals = 2): string {
  const { units, minutes, seconds } = split((raDeg / 15) * 3600, decimals);
  return `${pad(units % 24, 2)}h${pad(minutes, 2)}m${seconds}s`;
}

export interface FormatDecOptions {
  decimals?: number;
  /** "symbols" for display (Unicode minus), "letters" for text parseCoordinates reads. */
  style?: "symbols" | "letters";
}

/** -7.245147 -> "−07°14′42.5″" or, with style "letters", "-07d14m42.5s". */
export function formatDec(
  decDeg: number,
  { decimals = 1, style = "symbols" }: FormatDecOptions = {},
): string {
  const { units, minutes, seconds } = split(Math.abs(decDeg) * 3600, decimals);
  const isZero = units === 0 && minutes === 0 && Number(seconds) === 0;
  if (style === "letters") {
    const sign = decDeg < 0 && !isZero ? "-" : "+";
    return `${sign}${pad(units, 2)}d${pad(minutes, 2)}m${seconds}s`;
  }
  const sign = decDeg < 0 && !isZero ? "−" : "+";
  return `${sign}${pad(units, 2)}°${pad(minutes, 2)}′${seconds}″`;
}

/** 269.45208 -> "269.4521°" ; -7.2451 -> "−7.2451°" (Unicode minus, explicit +). */
export function formatDegrees(
  deg: number,
  { decimals = 4, signed = false } = {},
): string {
  const text = Math.abs(deg).toFixed(decimals);
  const isZero = Number(text) === 0;
  const sign = deg < 0 && !isZero ? "−" : signed ? "+" : "";
  return `${sign}${text}°`;
}
