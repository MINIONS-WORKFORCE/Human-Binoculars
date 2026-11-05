// Three fake 128x128 sky frames drawn in code, so the demo works without any files:
// a fixed star field, one star moving 3 px per frame (like Barnard's Star)
// and one star changing brightness (like R Draconis).

const SIZE = 128;
const STAR_COUNT = 40;
const MOVER = { x: 40, y: 70, stepX: 3, stepY: -1, peak: 230 };
const VARIABLE = { x: 92, y: 36, peaks: [240, 70, 170] };

// Small seeded random generator (mulberry32) so every page load draws the same sky.
function random(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), a | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Add a soft Gaussian star to a grey-level buffer.
function addStar(pixels, cx, cy, peak, sigma = 1.2) {
  const r = Math.ceil(sigma * 3);
  for (let y = Math.floor(cy) - r; y <= Math.ceil(cy) + r; y++) {
    for (let x = Math.floor(cx) - r; x <= Math.ceil(cx) + r; x++) {
      if (x < 0 || y < 0 || x >= SIZE || y >= SIZE) continue;
      const d2 = (x - cx) ** 2 + (y - cy) ** 2;
      pixels[y * SIZE + x] += peak * Math.exp(-d2 / (2 * sigma * sigma));
    }
  }
}

function drawSky(frameIndex) {
  const pixels = new Float32Array(SIZE * SIZE);

  const noise = random(1000 + frameIndex); // noise changes per frame
  for (let i = 0; i < pixels.length; i++) pixels[i] = 12 + noise() * 18;

  const field = random(42); // the star field does not
  for (let i = 0; i < STAR_COUNT; i++) {
    addStar(
      pixels,
      field() * SIZE,
      field() * SIZE,
      40 + field() * 180,
      0.9 + field() * 0.8,
    );
  }

  addStar(
    pixels,
    MOVER.x + MOVER.stepX * frameIndex,
    MOVER.y + MOVER.stepY * frameIndex,
    MOVER.peak,
  );
  addStar(pixels, VARIABLE.x, VARIABLE.y, VARIABLE.peaks[frameIndex], 1.4);

  const image = new ImageData(SIZE, SIZE);
  for (let i = 0; i < pixels.length; i++) {
    const v = Math.min(255, pixels[i]);
    image.data.set([v, v, v, 255], i * 4);
  }
  return image;
}

/** Frames in the same shape loadFrames() returns: { name, bitmap, width, height }. */
export async function makeSampleFrames() {
  return Promise.all(
    [0, 1, 2].map(async (i) => ({
      name: `sample-${i + 1}.png`,
      bitmap: await createImageBitmap(drawSky(i)),
      width: SIZE,
      height: SIZE,
    })),
  );
}
