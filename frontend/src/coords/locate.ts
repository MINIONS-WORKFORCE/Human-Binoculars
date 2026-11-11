// Turns what the user typed into a sky position.
//   coordinates  -> parsed here (decimal degrees or hours/degrees)
//   a name       -> the five challenge targets first (offline, instant),
//                   then the backend's /api/resolve
import { ApiError, type Resolve } from "../api/client";
import { findTarget } from "../targets";
import {
  CoordError,
  looksLikeCoordinates,
  parseCoordinates,
  type CoordFormat,
} from "./parse";

export type Location =
  | {
      kind: "coordinates";
      /** The notation the user typed. */
      format: CoordFormat;
      raDeg: number;
      decDeg: number;
    }
  | {
      kind: "name";
      /** "local": one of the five presets; "api": /api/resolve. */
      source: "local" | "api";
      name: string;
      targetKey: string | null;
      objectType: string | null;
      raDeg: number;
      decDeg: number;
    };

export type Preview =
  | { status: "empty" }
  | { status: "ready"; location: Location }
  /** A name that is not one of the presets: resolved on submit. */
  | { status: "needs-lookup"; name: string }
  | { status: "invalid"; error: CoordError };

/**
 * Everything that can be worked out while the user types, without a network
 * call: parsed coordinates, a preset name, or why the input is not valid.
 */
export function previewInput(input: string): Preview {
  const text = input.trim();
  if (text === "") return { status: "empty" };

  if (looksLikeCoordinates(text)) {
    try {
      const { raDeg, decDeg, format } = parseCoordinates(text);
      return {
        status: "ready",
        location: { kind: "coordinates", format, raDeg, decDeg },
      };
    } catch (error) {
      if (error instanceof CoordError) return { status: "invalid", error };
      throw error;
    }
  }

  const preset = findTarget(text);
  if (preset) {
    return {
      status: "ready",
      location: {
        kind: "name",
        source: "local",
        name: preset.name,
        targetKey: preset.key,
        objectType: preset.objectType,
        raDeg: preset.ra,
        decDeg: preset.dec,
      },
    };
  }
  return { status: "needs-lookup", name: text };
}

export type NameResolver = (name: string) => Promise<Resolve>;

/** Like previewInput, but also looks names up. Throws CoordError. */
export async function locate(
  input: string,
  resolve: NameResolver,
): Promise<Location> {
  const preview = previewInput(input);
  switch (preview.status) {
    case "ready":
      return preview.location;
    case "invalid":
      throw preview.error;
    case "empty":
      throw new CoordError("EMPTY", "Enter coordinates or an object name");
    case "needs-lookup":
      break;
  }

  let result: Resolve;
  try {
    result = await resolve(preview.name);
  } catch (error) {
    if (error instanceof ApiError && error.code === "UNKNOWN_TARGET") {
      throw new CoordError(
        "NAME_NOT_FOUND",
        `No object named "${preview.name}" was found. Check the spelling or type its coordinates.`,
      );
    }
    throw new CoordError(
      "RESOLVER_UNAVAILABLE",
      "The name lookup is not reachable right now. Type the coordinates instead.",
    );
  }
  return {
    kind: "name",
    source: "api",
    name: result.name,
    targetKey: result.target_key,
    objectType: null,
    raDeg: result.ra,
    decDeg: result.dec,
  };
}
