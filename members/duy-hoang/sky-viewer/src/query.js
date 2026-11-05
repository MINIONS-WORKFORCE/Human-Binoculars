// The search lives in the URL (?q=&fov=&src=) so a view can be shared or embedded.

export const FOV_CHOICES = [2, 5, 10, 20]; // arcminutes
export const SOURCE_IDS = ["unwise", "sample"];
export const DEFAULTS = { q: "", fov: 5, src: "unwise" };

/** "?q=Barnard%27s%20Star&fov=10" -> { q, fov, src }; unknown values fall back to DEFAULTS. */
export function readQuery(search) {
  const params = new URLSearchParams(search);
  const fov = Number(params.get("fov"));
  const src = params.get("src");
  return {
    q: (params.get("q") ?? DEFAULTS.q).trim(),
    fov: FOV_CHOICES.includes(fov) ? fov : DEFAULTS.fov,
    src: SOURCE_IDS.includes(src) ? src : DEFAULTS.src,
  };
}

/** { q, fov, src } -> "?q=...&fov=...&src=..." (spaces as %20, not +, so links read well). */
export function writeQuery({ q, fov, src }) {
  const parts = [
    ["q", q],
    ["fov", fov],
    ["src", src],
  ].map(([key, value]) => `${key}=${encodeURIComponent(value)}`);
  return `?${parts.join("&")}`;
}
