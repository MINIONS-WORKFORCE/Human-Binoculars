import { expect, test, type Page } from "@playwright/test";

/** Opens the page and waits until all images are decoded and the blink is ready. */
async function openViewer(page: Page) {
  await page.goto("/");
  await expect(page.getByText(/Loading images/)).toBeHidden();
  await expect(page.getByTestId("frame-counter")).toHaveText(/^Frame \d \/ 3$/);
}

test("blinks the mock frames: play, step, difference image", async ({
  page,
}) => {
  await openViewer(page);
  const counter = page.getByTestId("frame-counter");
  const date = page.getByTestId("frame-date");

  // The blink starts on its own once preloading is done; pause it.
  await page.getByRole("button", { name: "Pause" }).click();
  const paused = await counter.textContent();

  // Play: the frame changes by itself.
  await page.getByRole("button", { name: "Play" }).click();
  await expect(counter).not.toHaveText(paused!);
  await page.getByRole("button", { name: "Pause" }).click();

  // Step with the keyboard: next frame, and its date and wavelength line updates.
  const before = Number((await counter.textContent())!.match(/Frame (\d)/)![1]);
  const dateBefore = await date.textContent();
  await page.keyboard.press("ArrowRight");
  await expect(counter).toHaveText(`Frame ${(before % 3) + 1} / 3`);
  await expect(date).not.toHaveText(dateBefore!);
  await expect(date).toHaveText(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC$/);
  await expect(page.getByTestId("frame-wavelength")).toHaveText("4.70 µm");

  // Switch to the difference image.
  const difference = page.getByRole("button", { name: "Difference" });
  await difference.click();
  await expect(difference).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("img", { name: /^Difference image, frame/ }),
  ).toBeVisible();
});

test("draws the crosshair on the star at (x + 0.5) * pixel size", async ({
  page,
}) => {
  await openViewer(page);
  await page.getByRole("button", { name: "Pause" }).click();
  await page.getByRole("slider", { name: /Frame/ }).fill("0");
  await expect(page.getByTestId("frame-counter")).toHaveText("Frame 1 / 3");

  // Frame 1 has predicted_px (17, 19). Read canvas pixels around that spot.
  const probe = await page
    .locator("canvas.blink-canvas")
    .evaluate((canvas: HTMLCanvasElement) => {
      const ctx = canvas.getContext("2d")!;
      const size = canvas.width / 39; // canvas pixels per SPHEREx pixel
      const at = (x: number, y: number) =>
        Array.from(ctx.getImageData(Math.floor(x), Math.floor(y), 1, 1).data);
      const cx = 17.5 * size;
      const cy = 19.5 * size;
      return {
        size,
        star: at(cx, cy), // centre left open by the gap: the star's own pixel
        // The ticks start 1.5 pixels from the centre. Probing just inside and just
        // outside that edge on both sides catches a crosshair off by half a pixel.
        gap: [
          at(cx + 1.25 * size, cy),
          at(cx - 1.25 * size, cy),
          at(cx, cy + 1.25 * size),
        ],
        arms: [
          at(cx + 1.75 * size, cy),
          at(cx - 1.75 * size, cy),
          at(cx, cy + 1.75 * size),
        ],
        farAway: at(3 * size, 3 * size), // empty sky
      };
    });

  // Marker colour #ffc46b: strong red, clearly less blue. Star and sky are grey.
  const isMarker = ([r, , b]: number[]) => r > 200 && r - b > 80;

  expect(Number.isInteger(probe.size)).toBe(true);
  expect(probe.star[0]).toBeGreaterThanOrEqual(200); // bright, grey star pixel
  expect(probe.star[0]).toBe(probe.star[2]);
  expect(probe.gap.map(isMarker)).toEqual([false, false, false]);
  expect(probe.arms.map(isMarker)).toEqual([true, true, true]);
  expect(probe.farAway[0]).toBeLessThan(40); // dark sky, no marker there
});
