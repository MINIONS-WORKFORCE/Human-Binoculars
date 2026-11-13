// Zooming happens in the browser on frames already loaded: no /api/frames call,
// square pixels, and the crosshair stays on the star.
import { expect, test, type Page } from "@playwright/test";

const canvas = (page: Page) => page.getByTestId("blink-canvas");

/** The viewer's window as [x0, y0, span] in SPHEREx pixels. */
async function view(page: Page) {
  const value = await canvas(page).getAttribute("data-view");
  return value!.split(",").map(Number) as [number, number, number];
}

async function openPaused(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("frame-counter")).toHaveText(/^Frame \d \/ 3$/);
  await page.getByRole("button", { name: "Pause" }).click();
  await page.getByRole("slider", { name: /Frame/ }).fill("0");
  await expect(page.getByTestId("frame-counter")).toHaveText("Frame 1 / 3");
}

function countFramesCalls(page: Page) {
  const calls: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/frames?")) calls.push(r.url());
  });
  return calls;
}

test("a smaller field of view zooms on the star with no new request", async ({
  page,
}) => {
  await openPaused(page);
  const calls = countFramesCalls(page);
  const [, , full] = await view(page);

  await page
    .locator("form.controls")
    .getByLabel("Field of view")
    .selectOption("2");
  await expect.poll(async () => (await view(page))[2]).toBeLessThan(full);
  expect(calls).toEqual([]);

  // Frame 1 predicts the star at pixel (17, 19). Find it in the zoomed window and
  // check the crosshair ticks around it, as the full-image test does.
  const [x0, y0, span] = await view(page);
  const probe = await canvas(page).evaluate(
    (el: HTMLCanvasElement, [x0, y0, span]) => {
      const ctx = el.getContext("2d")!;
      const size = el.width / span;
      const at = (x: number, y: number) =>
        Array.from(ctx.getImageData(Math.floor(x), Math.floor(y), 1, 1).data);
      const cx = (17 - x0 + 0.5) * size;
      const cy = (19 - y0 + 0.5) * size;
      return {
        size,
        star: at(cx, cy),
        gap: at(cx + 1.25 * size, cy),
        arm: at(cx + 1.75 * size, cy),
      };
    },
    [x0, y0, span],
  );
  const isMarker = ([r, , b]: number[]) => r > 200 && r - b > 80;
  expect(Number.isInteger(probe.size)).toBe(true);
  expect(probe.size).toBeGreaterThan(10); // closer than the whole image
  expect(probe.star[0]).toBeGreaterThanOrEqual(200);
  expect(isMarker(probe.gap)).toBe(false);
  expect(isMarker(probe.arm)).toBe(true);
});

test("+, −, Fit, wheel, drag and keys change only the view", async ({
  page,
}) => {
  await openPaused(page);
  const calls = countFramesCalls(page);
  const zoom = page.getByRole("group", { name: "Zoom" });
  const [, , full] = await view(page);
  await expect(zoom.getByRole("button", { name: "Fit" })).toBeDisabled();

  await zoom.getByRole("button", { name: "Zoom in" }).click();
  await zoom.getByRole("button", { name: "Zoom in" }).click();
  const zoomed = await view(page);
  expect(zoomed[2]).toBeLessThan(full);
  await expect(page.getByTestId("zoom-readout")).toContainText("×");

  // Drag to the right: the window moves left over the image.
  // Mouse coordinates are in the viewport: bring the whole canvas into it first.
  await canvas(page).scrollIntoViewIfNeeded();
  const box = (await canvas(page).boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width / 2 + box.width / 4,
    box.y + box.height / 2,
    {
      steps: 5,
    },
  );
  await page.mouse.up();
  await expect.poll(async () => (await view(page))[0]).toBeLessThan(zoomed[0]);

  await zoom.getByRole("button", { name: "Zoom out" }).click();
  expect((await view(page))[2]).toBeGreaterThan(zoomed[2]);

  await zoom.getByRole("button", { name: "Fit" }).click();
  expect((await view(page))[2]).toBe(full);

  // Wheel up over the canvas zooms in; the page itself does not scroll.
  const scrollY = await page.evaluate(() => window.scrollY);
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.wheel(0, -120);
  await expect.poll(async () => (await view(page))[2]).toBeLessThan(full);
  expect(await page.evaluate(() => window.scrollY)).toBe(scrollY);

  // Key 0 shows the whole image again; + zooms in.
  await page.locator("body").press("0");
  expect((await view(page))[2]).toBe(full);
  await page.locator("body").press("+");
  expect((await view(page))[2]).toBeLessThan(full);

  expect(calls).toEqual([]);
});
