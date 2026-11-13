// /api/frames warnings are codes. Each one gets a sentence a visitor can act on (SRS FR-12).
// A warning does not block the result: the frames are still shown.

const MESSAGES: Record<string, string> = {
  SATURATION_POSSIBLE:
    "Some pixels may be saturated, so the brightest star can look flatter than it is.",
  FEW_FRAMES:
    "Fewer than 3 frames, so there is little to blink. Try another detector or a larger field of view.",
  TRUNCATED:
    "Only the first frames are shown because the list was cut at the frame limit.",
  MIXED_WAVELENGTH:
    "These frames differ in wavelength, so a brightness change between them may be colour, not motion.",
  TARGET_OUTSIDE_COVERAGE:
    "Some observations were omitted because they do not cover the predicted target position.",
};

/** The sentence for a warning code; an unknown code is shown as it came. */
export function describeWarning(code: string): string {
  return MESSAGES[code] ?? `The API reported ${code}.`;
}
