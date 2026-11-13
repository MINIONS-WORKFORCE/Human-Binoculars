// What the page keeps in its URL, so a reload or a shared link reopens the same view:
//   ?q=Barnard%27s+Star&fov=5&det=D6
// q is the text typed in the target field, fov the width of the cutout in arcminutes,
// det the detector as D1 to D6. A missing fov means "the API's default size".

/** FOV choices in arcminutes (SRS FR-02). Anything over 18' exceeds the API's 0.3 degree limit. */
export const FOV_OPTIONS = [2, 5, 10] as const;
export type Fov = (typeof FOV_OPTIONS)[number];

export interface UrlState {
  q: string | null;
  fov: Fov | null;
  detector: number | null;
}

/** Arcminutes to the API's `size` in degrees: 2' is 0.0333, 5' is 0.0833, 10' is 0.1667. */
export function fovToSize(fov: Fov): number {
  return Math.round((fov / 60) * 10000) / 10000;
}

export function parseUrlState(search: string): UrlState {
  const params = new URLSearchParams(search);

  const q = params.get("q")?.trim() || null;

  const fovValue = Number(params.get("fov"));
  const fov = FOV_OPTIONS.find((option) => option === fovValue) ?? null;

  const det = /^d?([1-6])$/i.exec(params.get("det")?.trim() ?? "");
  const detector = det ? Number(det[1]) : null;

  return { q, fov, detector };
}

/** The query string for a state, starting with "?", or "" when nothing is set. */
export function buildSearch({ q, fov, detector }: UrlState): string {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (fov !== null) params.set("fov", String(fov));
  if (detector !== null) params.set("det", `D${detector}`);
  const text = params.toString();
  return text ? `?${text}` : "";
}
