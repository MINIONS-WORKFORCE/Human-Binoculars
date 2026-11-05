import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { locate } from "../../coords/resolve.js";
import { TARGETS } from "../../coords/targets.js";

const EXAMPLES = [
  "08h55m10.831s-7d14m42.53s",
  "133.795 -7.245",
  ...TARGETS.map((target) => target.name),
  "M31",
  "25h00m00s +10d00m00s",
];

const SOURCE_LABEL = {
  input: "typed coordinates",
  local: "targets.js (offline)",
  mast: "MAST Name Lookup",
};

function aladinUrl({ raDeg, decDeg }) {
  const target = `${raDeg.toFixed(6)} ${decDeg.toFixed(6)}`;
  return `https://aladin.cds.unistra.fr/AladinLite/?target=${encodeURIComponent(target)}&fov=0.2`;
}

function Result({ state }) {
  if (state.status === "idle") return null;
  if (state.status === "loading") return <p>Looking up…</p>;
  if (state.status === "error") {
    return (
      <p style={{ color: "#c0392b" }}>
        <code>{state.error.code ?? "ERROR"}</code> {state.error.message}
      </p>
    );
  }

  const { result } = state;
  return (
    <table style={{ borderCollapse: "collapse", marginTop: 8 }}>
      <tbody>
        {[
          ["RA (deg)", result.raDeg.toFixed(6)],
          ["Dec (deg)", result.decDeg.toFixed(6)],
          ["Source", SOURCE_LABEL[result.source]],
          ["Name", result.name ?? "—"],
          ["Type", result.objectType ?? "—"],
          ["Epoch", result.epoch ?? "unknown"],
        ].map(([label, value]) => (
          <tr key={label}>
            <th style={{ textAlign: "left", padding: "4px 16px 4px 0" }}>
              {label}
            </th>
            <td style={{ fontFamily: "ui-monospace, monospace" }}>{value}</td>
          </tr>
        ))}
        <tr>
          <th />
          <td style={{ paddingTop: 8 }}>
            <a href={aladinUrl(result)} target="_blank" rel="noreferrer">
              Open in Aladin Lite
            </a>
          </td>
        </tr>
      </tbody>
    </table>
  );
}

function App() {
  const [input, setInput] = useState(EXAMPLES[0]);
  const [state, setState] = useState({ status: "idle" });

  async function run(text) {
    setInput(text);
    setState({ status: "loading" });
    try {
      setState({ status: "ok", result: await locate(text) });
    } catch (error) {
      setState({ status: "error", error });
    }
  }

  return (
    <main
      style={{
        fontFamily: "system-ui",
        padding: 24,
        maxWidth: 720,
        colorScheme: "light dark",
      }}
    >
      <h1 style={{ fontSize: 24 }}>Coordinate input demo</h1>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          run(input);
        }}
        style={{ display: "flex", gap: 8 }}
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={`133.795 -7.245, 08h55m10.831s -7d14m42.53s or "Barnard's Star"`}
          style={{ flex: 1, padding: 8, fontSize: 16 }}
          aria-label="Coordinates or object name"
        />
        <button type="submit" style={{ padding: "8px 16px", fontSize: 16 }}>
          Go
        </button>
      </form>

      <p style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
        {EXAMPLES.map((example) => (
          <button key={example} type="button" onClick={() => run(example)}>
            {example}
          </button>
        ))}
      </p>

      <Result state={state} />
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
