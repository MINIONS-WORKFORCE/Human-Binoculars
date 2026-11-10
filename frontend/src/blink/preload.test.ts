import { describe, expect, it } from "vitest";
import { PreloadError, preloadImages, type DecodableImage } from "./preload";

/** Fake image: decode() settles on a later tick, rejecting for urls containing "broken". */
function fakeImageFactory(order: string[]) {
  return (): DecodableImage => {
    const image = {
      src: "",
      decode: () =>
        new Promise<void>((resolve, reject) => {
          // Later urls finish first, to prove the result keeps the input order.
          const delay = 10 - Number(image.src.match(/\d+/)?.[0] ?? 0);
          setTimeout(() => {
            order.push(image.src);
            if (image.src.includes("broken"))
              reject(new Error("decode failed"));
            else resolve();
          }, delay);
        }),
    };
    return image;
  };
}

describe("preloadImages", () => {
  it("decodes every image before resolving, in input order, reporting progress", async () => {
    const decoded: string[] = [];
    const progress: number[] = [];
    const urls = ["/a1.png", "/a2.png", "/a3.png"];

    const images = await preloadImages(
      urls,
      (n) => progress.push(n),
      fakeImageFactory(decoded),
    );

    expect(images.map((i) => i.src)).toEqual(urls);
    expect(decoded).toHaveLength(3); // nothing resolved before all decodes ran
    expect(decoded).toEqual(["/a3.png", "/a2.png", "/a1.png"]);
    expect(progress).toEqual([1, 2, 3]);
  });

  it("rejects with the url of the image that failed", async () => {
    const result = preloadImages(
      ["/ok1.png", "/broken2.png"],
      () => {},
      fakeImageFactory([]),
    );
    await expect(result).rejects.toBeInstanceOf(PreloadError);
    await expect(result).rejects.toMatchObject({ url: "/broken2.png" });
  });

  it("resolves an empty list immediately", async () => {
    await expect(
      preloadImages([], () => {}, fakeImageFactory([])),
    ).resolves.toEqual([]);
  });
});
