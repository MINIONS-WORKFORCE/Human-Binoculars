import type { components } from "./schema";

type Schemas = components["schemas"];
export type Health = Schemas["Health"];
export type Resolve = Schemas["Resolve"];
export type Frames = Schemas["Frames"];
export type Frame = Schemas["Frame"];
export type Photometry = Schemas["Photometry"];
export type Astrometry = Schemas["Astrometry"];
export type ErrorResponse = Schemas["ErrorResponse"];

export interface SkyQuery {
  ra: number;
  dec: number;
  targetKey?: string;
}

export interface FramesQuery extends SkyQuery {
  detector?: number;
  size?: number;
  maxFrames?: number;
}

export interface ScienceQuery extends SkyQuery {
  detector?: number;
}

/** An API failure with the contract's error code, or NETWORK when the server is unreachable. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type Params = Record<string, string | number | undefined>;

function isErrorResponse(body: unknown): body is ErrorResponse {
  return typeof body === "object" && body !== null && "error" in body;
}

/**
 * baseUrl is the backend origin. An empty string means "same origin as the page",
 * which is what MSW intercepts in dev.
 */
export function createApiClient(
  baseUrl: string,
  fetchImpl: typeof fetch = (...args) => fetch(...args),
) {
  const origin = baseUrl || globalThis.location?.origin || "http://localhost";

  function url(path: string, params: Params = {}): string {
    const target = new URL(path, origin);
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) target.searchParams.set(key, String(value));
    }
    return target.href;
  }

  async function getJson<T>(path: string, params?: Params): Promise<T> {
    let response: Response;
    try {
      response = await fetchImpl(url(path, params), {
        headers: { Accept: "application/json" },
      });
    } catch {
      throw new ApiError(0, "NETWORK", `Cannot reach the API at ${origin}.`);
    }
    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      if (isErrorResponse(body)) {
        const { code, message, details } = body.error;
        throw new ApiError(response.status, code, message, details);
      }
      throw new ApiError(
        response.status,
        "HTTP_ERROR",
        `Request failed with status ${response.status}.`,
      );
    }
    return body as T;
  }

  const sky = (q: SkyQuery) => ({
    ra: q.ra,
    dec: q.dec,
    target_key: q.targetKey,
  });

  return {
    health: () => getJson<Health>("/api/health"),
    resolve: (name: string) => getJson<Resolve>("/api/resolve", { name }),
    frames: (q: FramesQuery) =>
      getJson<Frames>("/api/frames", {
        ...sky(q),
        detector: q.detector,
        size: q.size,
        max_frames: q.maxFrames,
      }),
    photometry: (q: ScienceQuery) =>
      getJson<Photometry>("/api/photometry", {
        ...sky(q),
        detector: q.detector,
      }),
    astrometry: (q: ScienceQuery) =>
      getJson<Astrometry>("/api/astrometry", {
        ...sky(q),
        detector: q.detector,
      }),
    /** Turns a frame's png / diff_png path into an absolute URL on the API origin. */
    imageUrl: (path: string) => url(path),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

const FRIENDLY: Record<string, string> = {
  NETWORK:
    "The data server is not reachable. Check your connection or try again shortly.",
  BAD_COORDS:
    "Those coordinates are out of range. RA must be 0 to 360 degrees and Dec -90 to 90.",
  BAD_PARAM:
    "One of the settings is invalid. Check the detector and frame options.",
  UNKNOWN_TARGET:
    "That target is not in our list yet. Try one of the five preset targets.",
  NO_FRAMES: "SPHEREx has no images of this spot yet.",
  FRAME_NOT_FOUND: "The images expired on the server. Load the frames again.",
};

/** A sentence a visitor can act on, instead of a raw status code. */
export function friendlyMessage(error: unknown): string {
  if (error instanceof ApiError)
    return (
      FRIENDLY[error.code] ??
      "Something went wrong on the server. Please try again."
    );
  return "Something unexpected happened. Please reload the page.";
}
