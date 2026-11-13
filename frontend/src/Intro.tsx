// The first thing a visitor reads: what the page is for, how to use it in three
// steps, and (on request) what each part of the viewer means.
export function Intro() {
  return (
    <section className="intro" aria-labelledby="intro-title">
      <h2 id="intro-title" className="intro-title">
        Watch nearby stars move across the sky
      </h2>
      <p className="intro-lead">
        NASA&apos;s SPHEREx telescope photographs the whole sky in infrared
        about every six months. This page lines up its pictures of one small
        patch of sky and flips between them, the way astronomers have long
        &ldquo;blinked&rdquo; photographs: a star that moved, or changed
        brightness, jumps out while everything else stays still.
      </p>
      <ol className="intro-steps">
        <li>
          <strong>Pick a star</strong> from the buttons below, or type a name or
          coordinates.
        </li>
        <li>
          <strong>Watch the blink.</strong> The crosshair marks where the star
          should be in each picture. Zoom in to look closer.
        </li>
        <li>
          <strong>Read the charts</strong> for its brightness over time and
          across infrared colours.
        </li>
      </ol>
      <details className="intro-more">
        <summary>What am I looking at?</summary>
        <dl>
          <dt>Frames</dt>
          <dd>
            Pictures of the same patch taken on different dates, all aligned to
            one grid so the background stays put.
          </dd>
          <dt>Crosshair</dt>
          <dd>
            Where the star is predicted to be at each date, from its catalogue
            motion. It is a prediction, not a detection.
          </dd>
          <dt>Original / Difference</dt>
          <dd>
            Difference shows each frame minus the first: grey is no change, a
            bright and dark pair next to each other suggests motion.
          </dd>
          <dt>Detector D1 to D6</dt>
          <dd>
            Six infrared bands, from 0.75 µm (D1) to 5 µm (D6). Cool objects
            such as brown dwarfs are brightest in D6.
          </dd>
          <dt>Field of view and zoom</dt>
          <dd>
            The frames are loaded once for a 10′ patch. Field of view, the + and
            − buttons, the mouse wheel or a pinch only zoom in the browser, so
            they are instant.
          </dd>
          <dt>Warnings</dt>
          <dd>
            Notes from the data, such as saturated pixels or too few dates. The
            frames are still shown.
          </dd>
        </dl>
      </details>
    </section>
  );
}
