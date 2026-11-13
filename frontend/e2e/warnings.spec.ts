// FR-12: a warning code from /api/frames becomes a sentence next to the frames.
// The mock never sends warnings, so this test answers the API itself with page.route()
// (service workers blocked so MSW does not answer first), like errors.spec.ts.
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

test.use({ serviceWorkers: "block" });

const samples = new URL("../../api_samples/", import.meta.url);
const sample = JSON.parse(
  readFileSync(new URL("frames_barnard_d6.json", samples), "utf8"),
);

test("shows each warning as a sentence and keeps the frames", async ({
  page,
}) => {
  await page.route(
    (url) => url.pathname === "/api/frames",
    (route) =>
      route.fulfill({
        json: { ...sample, warnings: ["SATURATION_POSSIBLE", "TRUNCATED"] },
      }),
  );
  await page.route(
    (url) => /^\/api\/frames\/.+\.png$/.test(url.pathname),
    (route) => {
      const path = new URL(route.request().url()).pathname;
      const [, index, diff] = path.match(/-(\d+)(\/diff)?\.png$/)!;
      return route.fulfill({
        contentType: "image/png",
        body: readFileSync(
          new URL(`png/frame-${index}${diff ? "_diff" : ""}.png`, samples),
        ),
      });
    },
  );
  // Everything else the page asks for is not needed here.
  await page.route(
    (url) => /^\/api\/(health|photometry)$/.test(url.pathname),
    (route) => route.fulfill({ status: 500, json: {} }),
  );

  await page.goto("/");

  const warnings = page.getByTestId("frame-warnings");
  await expect(warnings.getByRole("status")).toHaveCount(2);
  await expect(warnings).toContainText("Some pixels may be saturated");
  await expect(warnings).toContainText("SATURATION_POSSIBLE");
  await expect(warnings).toContainText("list was cut at the frame limit");
  await expect(page.getByTestId("frame-summary")).toContainText("3 frames");
  await expect(page.getByTestId("frame-counter")).toHaveText(/^Frame \d \/ 3$/);
});
