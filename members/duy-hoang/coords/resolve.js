// Turn what the user typed (coordinates or an object name) into a sky position.
// Rules and examples: see COORDINATES.md next to this file.

import { CoordError, looksLikeCoordinates, parseCoordinates } from "./parse.js";
import { findTarget } from "./targets.js";

// MAST has no CORS headers, so the browser goes through the Vite proxy (/mast -> mast.stsci.edu).
// From Node, pass endpoint: MAST_URL.
export const DEFAULT_ENDPOINT = "/mast/api/v0/invoke";
export const MAST_URL = "https://mast.stsci.edu/api/v0/invoke";

async function lookupMast(
  name,
  { fetch = globalThis.fetch, endpoint = DEFAULT_ENDPOINT, timeoutMs = 15000 },
) {
  const request = {
    service: "Mast.Name.Lookup",
    params: { input: name, format: "json" },
  };

  let body;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `request=${encodeURIComponent(JSON.stringify(request))}`,
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    body = await response.json();
  } catch (error) {
    throw new CoordError(
      "RESOLVER_UNAVAILABLE",
      `Name lookup failed: ${error.message}`,
    );
  }

  const hit = body?.resolvedCoordinate?.[0];
  if (!hit || !Number.isFinite(hit.ra) || !Number.isFinite(hit.decl)) {
    throw new CoordError("NAME_NOT_FOUND", `No object named "${name}"`);
  }
  return {
    raDeg: hit.ra,
    decDeg: hit.decl,
    name: hit.canonicalName ?? name,
    objectType: hit.objectType ?? null,
    source: "mast",
    epoch: 2000,
  };
}

/**
 * Object name -> { raDeg, decDeg, name, objectType, source, epoch }.
 * The 5 challenge targets come from targets.js (offline); anything else goes to MAST.
 */
export async function resolveName(name, options = {}) {
  const trimmed = String(name ?? "").trim();
  if (trimmed === "") {
    throw new CoordError("EMPTY", "Enter coordinates or an object name");
  }

  const target = findTarget(trimmed);
  if (target) {
    const { raDeg, decDeg, name: canonical, objectType, epoch } = target;
    return {
      raDeg,
      decDeg,
      name: canonical,
      objectType,
      source: "local",
      epoch,
    };
  }
  return lookupMast(trimmed, options);
}

/**
 * The one function the UI calls: coordinates are parsed, names are resolved.
 * Coordinates typed by the user have no known epoch, so epoch is null.
 */
export async function locate(input, options = {}) {
  if (looksLikeCoordinates(input)) {
    const { raDeg, decDeg } = parseCoordinates(input);
    return {
      raDeg,
      decDeg,
      name: null,
      objectType: null,
      source: "input",
      epoch: null,
    };
  }
  return resolveName(input, options);
}
