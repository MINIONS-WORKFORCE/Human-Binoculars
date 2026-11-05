import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BlinkViewer } from "../../blink/BlinkViewer.jsx";
import { loadFrames, releaseFrames } from "../../blink/loadFrames.js";
import { makeSampleFrames } from "../../blink/sampleFrames.js";

function App() {
  const [frames, setFrames] = useState([]);
  const [message, setMessage] = useState(null);
  const [dragging, setDragging] = useState(false);

  // Free the old bitmaps only after the new frames are on screen.
  useEffect(() => () => releaseFrames(frames), [frames]);

  useEffect(() => {
    loadSamples();
  }, []);

  async function loadSamples() {
    setFrames(await makeSampleFrames());
    setMessage(null);
  }

  async function openFiles(files) {
    const { frames: loaded, rejected } = await loadFrames(files);
    const skipped = rejected.length
      ? `Skipped (not PNG or unreadable): ${rejected.join(", ")}`
      : null;
    if (loaded.length === 0) {
      setMessage(skipped ?? "No PNG files selected");
      return;
    }
    setFrames(loaded);
    setMessage(skipped);
  }

  return (
    <main
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        openFiles(event.dataTransfer.files);
      }}
      style={{
        fontFamily: "system-ui",
        padding: 16,
        minHeight: "100vh",
        boxSizing: "border-box",
        colorScheme: "light dark",
        outline: dragging ? "3px dashed #3b82f6" : "none",
        outlineOffset: -8,
      }}
    >
      <h1 style={{ fontSize: 24, marginTop: 0 }}>Blink viewer demo</h1>
      <p style={{ maxWidth: 512 }}>
        Shows images of the same patch of sky one after another. Look for the
        star that moves and the one that changes brightness. Choose or drop your
        own PNG files (ordered by file name).
      </p>

      <div
        style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}
      >
        <input
          type="file"
          accept="image/png"
          multiple
          aria-label="Choose PNG files"
          onChange={(event) => {
            openFiles(event.target.files);
            event.target.value = ""; // allow picking the same files again
          }}
        />
        <button type="button" onClick={loadSamples}>
          Use sample frames
        </button>
      </div>

      {message && <p style={{ color: "#c0392b", maxWidth: 512 }}>{message}</p>}

      <BlinkViewer frames={frames} />
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
