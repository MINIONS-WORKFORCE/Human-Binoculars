// Blink only means something when frames switch instantly. If an image is still
// downloading or decoding when its turn comes, the canvas flickers and the viewer
// mistakes that for a real change. So every image is fetched AND decoded first.

/** The part of HTMLImageElement preloading needs; tests pass a fake. */
export interface DecodableImage {
  src: string;
  decode(): Promise<void>;
}

export class PreloadError extends Error {
  readonly url: string;
  constructor(url: string) {
    super(`Could not load image ${url}`);
    this.name = "PreloadError";
    this.url = url;
  }
}

/**
 * The PNGs come from the API origin, not the page's. Requesting them with CORS
 * (the API allows it) keeps the canvas readable: a canvas drawn from cross-origin
 * images without it is "tainted", and getImageData / toBlob (pixel tests, GIF
 * export) throw. Set before src, as the browser reads it when the request starts.
 */
function corsImage(): HTMLImageElement {
  const image = new Image();
  image.crossOrigin = "anonymous";
  return image;
}

/**
 * Loads all urls in parallel and resolves, in the same order, once every image is
 * decoded. onProgress(n) fires after each decoded image with the running count.
 * Rejects with PreloadError naming the first image that failed.
 */
export async function preloadImages<
  T extends DecodableImage = HTMLImageElement,
>(
  urls: readonly string[],
  onProgress: (done: number) => void = () => {},
  createImage: () => T = () => corsImage() as unknown as T,
): Promise<T[]> {
  let done = 0;
  return Promise.all(
    urls.map(async (url) => {
      const image = createImage();
      image.src = url;
      try {
        await image.decode(); // resolves only when the pixels are ready to draw
      } catch {
        throw new PreloadError(url);
      }
      onProgress(++done);
      return image;
    }),
  );
}
