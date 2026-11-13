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
    // A proxy or a wrong VITE_API_BASE_URL can answer 200 with an HTML page.
    if (typeof body !== "object" || body === null) {
      throw new ApiError(
        response.status,
        "HTTP_ERROR",
        `Expected JSON from ${path} but got something else.`,
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

/**
 * The error table of the API contract (wiki "The API contract", section 4), plus the
 * two codes this client adds: NETWORK (no answer at all, including a CORS refusal)
 * and HTTP_ERROR (an answer that is not the contract's JSON).
 */
export const ERROR_CODES = [
  "BAD_COORDS",
  "BAD_PARAM",
  "UNKNOWN_TARGET",
  "NO_FRAMES",
  "FRAME_NOT_FOUND",
  "UPSTREAM_ERROR",
  "UPSTREAM_TIMEOUT",
  "INTERNAL",
  "NETWORK",
  "HTTP_ERROR",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];

export interface ErrorInfo {
  /** The contract code, or UNKNOWN for something that is not an ApiError. */
  code: string;
  /** A sentence a visitor can act on, instead of a raw status code. */
  message: string;
  /** True when sending the same request again may work (server or network trouble). */
  retry: boolean;
}

const ERRORS: Record<ErrorCode, Omit<ErrorInfo, "code">> = {
  BAD_COORDS: {
    message:
      "Those coordinates are out of range. RA must be 0 to 360 degrees and Dec -90 to 90.",
    retry: false,
  },
  BAD_PARAM: {
    message:
      "One of the settings is invalid. Check the detector and frame options.",
    retry: false,
  },
  UNKNOWN_TARGET: {
    message:
      "That target is not in our list yet. Try one of the five preset targets.",
    retry: false,
  },
  NO_FRAMES: {
    message:
      "SPHEREx has no images of this spot yet. Try another target or detector.",
    retry: false,
  },
  FRAME_NOT_FOUND: {
    message: "The images expired on the server. Load the frames again.",
    retry: true,
  },
  UPSTREAM_ERROR: {
    message:
      "The NASA archive (IRSA) returned an error. Try again in a moment.",
    retry: true,
  },
  UPSTREAM_TIMEOUT: {
    message:
      "The request to the NASA archive timed out. Try again in a moment.",
    retry: true,
  },
  INTERNAL: {
    message:
      "Something went wrong on our server. Try again; if it keeps failing, tell the team.",
    retry: true,
  },
  NETWORK: {
    message:
      "The data server is not reachable. Check your connection or try again shortly.",
    retry: true,
  },
  HTTP_ERROR: {
    message: "The data server sent an unexpected answer. Try again shortly.",
    retry: true,
  },
};

function isKnownCode(code: string): code is ErrorCode {
  return code in ERRORS;
}

/** What to tell the visitor about a failed request, and whether to offer "Try again". */
export function describeError(error: unknown): ErrorInfo {
  if (!(error instanceof ApiError))
    return {
      code: "UNKNOWN",
      message: "Something unexpected happened. Please reload the page.",
      retry: false,
    };
  if (isKnownCode(error.code))
    return { code: error.code, ...ERRORS[error.code] };
  // A code newer than this table: fall back on the HTTP status class.
  return {
    code: error.code,
    message: "Something went wrong on the server. Please try again.",
    retry: error.status === 0 || error.status >= 500,
  };
}

/** A sentence a visitor can act on, instead of a raw status code. */
export function friendlyMessage(error: unknown): string {
  return describeError(error).message;
}
