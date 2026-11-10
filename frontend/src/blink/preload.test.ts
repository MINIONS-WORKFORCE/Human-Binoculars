import { describe, expect, it } from "vitest";
import { PreloadError, preloadImages, type DecodableImage } from "./preload";

/**
 * Fake images whose decode() the test settles by hand, so the order of events
 * is fixed instead of depending on timers (which made an earlier version flaky).
 */
function controlledImages() {
  const pending = new Map<
    string,
    { resolve: () => void; reject: (error: Error) => void }
  >();
  const create = (): DecodableImage => {
    const image: DecodableImage = {
      src: "",
      decode: () =>
        new Promise<void>((resolve, reject) => {
          pending.set(image.src, { resolve, reject });
        }),
    };
    return image;
  };
  const flush = () => new Promise((r) => setTimeout(r, 0));
  return { create, pending, flush };
}

describe("preloadImages", () => {
  it("waits for every decode, keeps input order, reports progress", async () => {
    const { create, pending, flush } = controlledImages();
    const progress: number[] = [];
    const urls = ["/a1.png", "/a2.png", "/a3.png"];
    let settled = false;

    const result = preloadImages(urls, (n) => progress.push(n), create).then(
      (images) => {
        settled = true;
        return images;
      },
    );
    expect([...pending.keys()]).toEqual(urls); // all requested in parallel

    // Finish in reverse order; nothing resolves until the last decode is done.
    pending.get("/a3.png")!.resolve();
    pending.get("/a2.png")!.resolve();
    await flush();
    expect(progress).toEqual([1, 2]);
    expect(settled).toBe(false);

    pending.get("/a1.png")!.resolve();
    const images = await result;
    expect(images.map((i) => i.src)).toEqual(urls);
    expect(progress).toEqual([1, 2, 3]);
  });

  it("rejects with the url of the image that failed", async () => {
    const { create, pending } = controlledImages();
    const result = preloadImages(
      ["/ok1.png", "/broken2.png"],
      () => {},
      create,
    );
    pending.get("/ok1.png")!.resolve();
    pending.get("/broken2.png")!.reject(new Error("decode failed"));
    await expect(result).rejects.toBeInstanceOf(PreloadError);
    await expect(result).rejects.toMatchObject({ url: "/broken2.png" });
  });

  it("resolves an empty list immediately", async () => {
    const { create } = controlledImages();
    await expect(preloadImages([], () => {}, create)).resolves.toEqual([]);
  });
});
