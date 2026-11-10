// Shows a position in every notation at once, so the visitor can check what was
// understood: coordinates typed in one notation appear in the other one too, and a
// name appears with both.
import { formatDec, formatDegrees, formatRa } from "./format";
import type { Location, Preview } from "./locate";
import type { CoordError } from "./parse";

export type Lookup =
  | { status: "idle" }
  | { status: "looking" }
  | { status: "found"; location: Location }
  | { status: "error"; error: CoordError };

function Typed() {
  return <span className="coord-typed">typed</span>;
}

function LocationRows({ location }: { location: Location }) {
  const typed = location.kind === "coordinates" ? location.format : null;
  return (
    <dl className="coord-rows">
      {location.kind === "name" && (
        <div data-testid="coord-name">
          <dt>Name</dt>
          <dd>
            <strong>{location.name}</strong>
            {location.objectType && (
              <span className="coord-note"> · {location.objectType}</span>
            )}
            <span className="coord-note">
              {location.source === "local"
                ? " · challenge target"
                : " · found by name lookup"}
            </span>
          </dd>
        </div>
      )}
      <div data-testid="coord-decimal">
        <dt>Decimal degrees {typed === "decimal" && <Typed />}</dt>
        <dd>
          RA {formatDegrees(location.raDeg)} · Dec{" "}
          {formatDegrees(location.decDeg, { signed: true })}
        </dd>
      </div>
      <div data-testid="coord-sexagesimal">
        <dt>Hours / degrees {typed === "sexagesimal" && <Typed />}</dt>
        <dd>
          RA {formatRa(location.raDeg)} · Dec {formatDec(location.decDeg)}
        </dd>
      </div>
    </dl>
  );
}

/**
 * preview: what can be read from the text right away.
 * lookup: the result of resolving a name on submit, for the same text.
 */
export function CoordinatePreview({
  preview,
  lookup,
}: {
  preview: Preview;
  lookup: Lookup;
}) {
  let content;
  if (preview.status === "ready") {
    content = <LocationRows location={preview.location} />;
  } else if (preview.status === "invalid") {
    content = <p className="coord-error">{preview.error.message}</p>;
  } else if (preview.status === "needs-lookup") {
    if (lookup.status === "found") {
      content = <LocationRows location={lookup.location} />;
    } else if (lookup.status === "error") {
      content = <p className="coord-error">{lookup.error.message}</p>;
    } else if (lookup.status === "looking") {
      content = <p className="muted">Looking up “{preview.name}”…</p>;
    } else {
      content = (
        <p className="muted">
          “{preview.name}” is not one of the challenge targets. Press Load
          frames to look it up by name.
        </p>
      );
    }
  } else {
    content = (
      <p className="muted">
        The position appears here in decimal degrees and in hours / degrees.
      </p>
    );
  }

  return (
    <div
      className="coord-preview"
      aria-live="polite"
      data-testid="coord-preview"
    >
      {content}
    </div>
  );
}
