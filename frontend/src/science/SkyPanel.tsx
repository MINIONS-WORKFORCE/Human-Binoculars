// Sky panel: the shared Aladin Lite map centred on the target, with a Gaia DR3 layer.
import { useState } from "react";
import { SkyMap } from "../../../shared/skymap/SkyMap.jsx";
import "./science.css";

export interface SkyPanelProps {
  ra: number;
  dec: number;
  /** Width of the map in degrees. */
  fovDeg: number;
}

type GaiaSource = "vizier" | "mock" | "off";

const GAIA_OPTIONS: { value: GaiaSource; label: string }[] = [
  { value: "vizier", label: "Gaia DR3 (VizieR)" },
  { value: "mock", label: "Synthetic stars (offline)" },
  { value: "off", label: "Off" },
];

export function SkyPanel({ ra, dec, fovDeg }: SkyPanelProps) {
  const [gaia, setGaia] = useState<GaiaSource>("mock");

  return (
    <section className="panel" aria-labelledby="sky-heading">
      <div className="panel-head">
        <h2 id="sky-heading" className="panel-title">
          Sky map
        </h2>
        <label className="panel-field">
          Gaia layer
          <select
            value={gaia}
            onChange={(e) => setGaia(e.target.value as GaiaSource)}
          >
            {GAIA_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <SkyMap
        raDeg={ra}
        decDeg={dec}
        fovDeg={fovDeg}
        gaia={gaia}
        onSwitchGaia={setGaia}
      />
      <p className="panel-note">
        Gaia positions are for epoch 2016.0, so a fast-moving star such as
        Barnard&rsquo;s Star sits away from where it appears in SPHEREx images.
      </p>
    </section>
  );
}
