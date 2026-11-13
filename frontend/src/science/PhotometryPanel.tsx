// Photometry panel: loads E6 /api/photometry for the position on screen and hands the
// response to the shared PhotometryChart (light curve, spectrum, data table).
import { useEffect, useState } from "react";
import { PhotometryChart } from "../../../shared/charts/Charts.jsx";
import { api, ApiError, friendlyMessage, type Photometry } from "../api";
import { useMock } from "../config";
import "./science.css";

export interface PhotometryPanelProps {
  ra: number;
  dec: number;
  /** Only known targets have one; the API still answers without it. */
  targetKey?: string;
}

type State =
  | { status: "loading" }
  | { status: "error"; message: string; code: string }
  | { status: "ready"; data: Photometry };

async function fetchPhotometry(props: PhotometryPanelProps): Promise<State> {
  try {
    // No detector: the chart has its own D1-D6 filter and needs every point.
    const data = await api.photometry({
      ra: props.ra,
      dec: props.dec,
      targetKey: props.targetKey,
    });
    return { status: "ready", data };
  } catch (error) {
    return {
      status: "error",
      message: friendlyMessage(error),
      code: error instanceof ApiError ? error.code : "UNKNOWN",
    };
  }
}

/** The backend's data mode, from /api/health; null until known or if it cannot be read. */
function useDataMode(): string | null {
  const [mode, setMode] = useState<string | null>(null);
  useEffect(() => {
    let current = true;
    api
      .health()
      .then((health) => {
        if (current) setMode(health.mode);
      })
      .catch(() => {});
    return () => {
      current = false;
    };
  }, []);
  return mode;
}

export function PhotometryPanel({ ra, dec, targetKey }: PhotometryPanelProps) {
  const mode = useDataMode();
  // An answer belongs to the position it was fetched for; any other position is "loading".
  const key = `${ra}|${dec}|${targetKey ?? ""}`;
  const [answer, setAnswer] = useState<{ key: string; state: State } | null>(
    null,
  );
  const state: State =
    answer?.key === key ? answer.state : { status: "loading" };

  // Only the latest request may update the panel; a slower earlier one is ignored.
  useEffect(() => {
    let current = true;
    void fetchPhotometry({ ra, dec, targetKey }).then((next) => {
      if (current) setAnswer({ key, state: next });
    });
    return () => {
      current = false;
    };
  }, [key, ra, dec, targetKey]);

  return (
    <section className="panel" aria-labelledby="photometry-heading">
      <h2 id="photometry-heading" className="panel-title">
        Photometry
      </h2>
      {state.status === "loading" && (
        <p className="muted" role="status">
          Loading photometry…
        </p>
      )}
      {state.status === "error" && (
        <p className="error" role="alert">
          {state.message} <code>{state.code}</code>
        </p>
      )}
      {state.status === "ready" &&
        (state.data.points.length === 0 ? (
          <p className="muted" role="status">
            No photometry measurements for this position.
          </p>
        ) : (
          <>
            <PhotometryChart data={state.data} />
            {mode === "fixture" && (
              <p className="panel-note">
                {useMock
                  ? "Fixture data: synthetic example values that test the interface."
                  : "Fixture data: measurements from local FITS where available. Example values may appear when FITS are missing."}
              </p>
            )}
          </>
        ))}
    </section>
  );
}
