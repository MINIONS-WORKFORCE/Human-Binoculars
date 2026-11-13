// Failure states from the API contract's error table. The real fixture backend never
// returns 502 / 504, so these tests answer the API themselves with page.route().
// MSW's service worker would answer first, so it is blocked here; main.tsx then
// renders without mocks and every /api call reaches the routes below.
import { readFileSync } from "node:fs";
import { expect, test, type Page, type Route } from "@playwright/test";

test.use({ serviceWorkers: "block" });

const samples = new URL("../../api_samples/", import.meta.url);
const framesSample = JSON.parse(
  readFileSync(new URL("frames_barnard_d6.json", samples), "utf8"),
);

function contractError(route: Route, status: number, code: string) {
  return route.fulfill({
    status,
    json: {
      api_version: "0.1",
      error: { code, message: `Example ${code}.`, details: {} },
    },
  });
}

/** Serves the sample PNGs for /api/frames/<id>.png and /api/frames/<id>/diff.png. */
async function serveImages(page: Page, ok: () => boolean) {
  await page.route(
    (url) => url.pathname.startsWith("/api/frames/"),
    (route) => {
      if (!ok()) return contractError(route, 404, "FRAME_NOT_FOUND");
      const path = new URL(route.request().url()).pathname;
      const [, index, diff] = path.match(/-(\d+)(\/diff)?\.png$/)!;
      const file = `png/frame-${index}${diff ? "_diff" : ""}.png`;
      return route.fulfill({
        contentType: "image/png",
        body: readFileSync(new URL(file, samples)),
      });
    },
  );
}

test("504 UPSTREAM_TIMEOUT: loading, then the contract message, then Try again blinks", async ({
  page,
}) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  let failing = true;
  await page.route(
    (url) => url.pathname === "/api/frames",
    async (route) => {
      if (!failing) return route.fulfill({ json: framesSample });
      await held;
      return contractError(route, 504, "UPSTREAM_TIMEOUT");
    },
  );
  await serveImages(page, () => true);

  await page.goto("/");

  // While the request is pending the page says so; there is no error yet.
  await expect(page.getByTestId("frames-loading")).toBeVisible();
  await expect(page.getByTestId("frames-error")).toHaveCount(0);
  release();

  // The visitor sees the sentence for the code, never the server's raw message.
  const alert = page.getByTestId("frames-error");
  await expect(alert).toHaveAttribute("role", "alert");
  await expect(alert).toContainText("The request to the NASA archive timed out.");
  await expect(alert).toContainText("UPSTREAM_TIMEOUT");
  await expect(alert).not.toContainText("Example UPSTREAM_TIMEOUT.");
  await expect(page.getByTestId("frames-loading")).toHaveCount(0);

  // A timeout is worth retrying; once the archive answers, the blink plays.
  failing = false;
  await alert.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByTestId("frames-error")).toHaveCount(0);
  await expect(page.getByTestId("frame-counter")).toHaveText(/^Frame \d \/ 3$/);
});

test("400 BAD_COORDS offers no retry; an expired image offers Reload frames", async ({
  page,
}) => {
  let badCoords = true;
  let imagesOk = false;
  await page.route(
    (url) => url.pathname === "/api/frames",
    (route) =>
      badCoords
        ? contractError(route, 400, "BAD_COORDS")
        : route.fulfill({ json: framesSample }),
  );
  await serveImages(page, () => imagesOk);

  await page.goto("/");
  const alert = page.getByTestId("frames-error");
  await expect(alert).toContainText("coordinates are out of range");
  await expect(alert).toContainText("BAD_COORDS");
  // Sending the same bad request again cannot help.
  await expect(alert.getByRole("button")).toHaveCount(0);

  // Frames load but their images are gone (backend restarted: FRAME_NOT_FOUND).
  badCoords = false;
  await page.getByRole("button", { name: "Barnard's Star" }).click();
  const overlay = page.getByRole("alert").filter({ hasText: "image failed" });
  await expect(overlay).toBeVisible();

  imagesOk = true;
  await overlay.getByRole("button", { name: "Reload frames" }).click();
  await expect(overlay).toHaveCount(0);
  await expect(page.getByTestId("frame-counter")).toHaveText(/^Frame \d \/ 3$/);
});

test("one visit only: the viewer explains why there is nothing to blink", async ({
  page,
}) => {
  // What the real-FITS fixture gives today: every cutout falls in one visit.
  const oneFrame = {
    ...framesSample,
    frames: framesSample.frames.slice(0, 1),
    warnings: ["FEW_FRAMES"],
  };
  await page.route(
    (url) => url.pathname === "/api/frames",
    (route) => route.fulfill({ json: oneFrame }),
  );
  await serveImages(page, () => true);

  await page.goto("/");
  await expect(page.getByTestId("frame-counter")).toHaveText("Frame 1 / 1");
  await expect(page.getByTestId("frame-summary")).toContainText("1 frame ·");
  await expect(page.getByTestId("single-frame")).toContainText(
    "nothing to blink yet",
  );
  await expect(page.getByRole("button", { name: "Play" })).toBeDisabled();
});
