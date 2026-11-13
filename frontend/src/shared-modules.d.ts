// Types for Thạch's plain-JS components in <repo>/shared, so TypeScript can check
// how the frontend calls them. (An ambient module cannot import by relative path,
// so `data` stays a plain object here; the panels pass the typed API response.)
declare module "*/shared/charts/Charts.jsx" {
  import type { ReactElement } from "react";

  export function PhotometryChart(props: {
    /** An E6 /api/photometry response. */
    data: object;
    defaultXAxis?: "time" | "wavelength";
  }): ReactElement;
}

declare module "*/shared/skymap/SkyMap.jsx" {
  import type { ReactElement } from "react";

  export function SkyMap(props: {
    /** Centre in ICRS degrees. */
    raDeg: number;
    decDeg: number;
    /** Width of the view in degrees. */
    fovDeg?: number;
    /** "vizier" is real Gaia DR3, "mock" is synthetic stars, "off" hides the layer. */
    gaia?: "vizier" | "mock" | "off";
    survey?: string;
  }): ReactElement;
}
