import { expect, test, type Page } from "@playwright/test";

/** The fixture only has photometry for R Draconis, as in the backend. */
async function openRDraconis(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "R Draconis" }).click();
  await expect(page.getByTestId("frame-summary")).toContainText("R Draconis");
}

test("photometry panel plots the E6 points and lists them in a table", async ({
  page,
}) => {
  await openRDraconis(page);
  const panel = page.getByRole("region", { name: "Photometry" });

  // The sample has six points, one per detector.
  await expect(
    panel.getByRole("img", { name: /^Light curve with 6 measurements/ }),
  ).toBeVisible();

  await panel.getByRole("button", { name: "By wavelength" }).click();
  await expect(
    panel.getByRole("img", { name: /^Spectrum with 6 measurements/ }),
  ).toBeVisible();

  await panel.getByText("Show data table").click();
  await expect(panel.locator("tbody tr")).toHaveCount(6);

  // Keeping one detector leaves one row.
  await panel.getByLabel("Detector").selectOption("1");
  await expect(panel.locator("tbody tr")).toHaveCount(1);
  await expect(
    panel.getByText("Fixture data: synthetic example values"),
  ).toBeVisible();
});

test("says so when a target has no photometry", async ({ page }) => {
  await page.goto("/"); // Barnard: no photometry in the fixture
  const panel = page.getByRole("region", { name: "Photometry" });
  await expect(
    panel.getByText("No photometry measurements for this position."),
  ).toBeVisible();
  await expect(panel.locator(".flux-chart__plot")).toHaveCount(0);

  // Switching to a target that has data replaces the message with the chart.
  await page.getByRole("button", { name: "R Draconis" }).click();
  await expect(panel.locator(".flux-chart__plot")).toBeVisible();
  await expect(panel.getByText("R Draconis ·")).toBeVisible();
});

test("sky map shows a Gaia layer the viewer can switch", async ({ page }) => {
  await page.goto("/");
  const sky = page.getByRole("region", { name: "Sky map" });
  await expect(sky.locator(".skymap__map")).toBeVisible();

  const layer = sky.getByLabel("Gaia layer");
  await expect(layer.locator("option")).toHaveText([
    "Gaia DR3 (VizieR)",
    "Synthetic stars (offline)",
    "Off",
  ]);

  // Synthetic stars need no network, so the status line is deterministic.
  await layer.selectOption("mock");
  await expect(sky.getByRole("status")).toContainText(
    "synthetic Gaia-like stars",
  );
});

test("the page does not scroll sideways at 390px wide (QA-16)", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openRDraconis(page);
  await expect(page.locator(".flux-chart__plot")).toBeVisible();
  await expect(page.locator(".skymap__map")).toBeVisible();

  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("each of the five presets loads frames and a photometry answer", async ({
  page,
}) => {
  await page.goto("/");
  const panel = page.getByRole("region", { name: "Photometry" });
  const presets = [
    "Barnard's Star",
    "WISE 0855-0714",
    "Epsilon Indi B",
    "RW Aurigae",
    "R Draconis",
  ];
  for (const name of presets) {
    await page.getByRole("button", { name }).click();
    await expect(page.getByTestId("frame-summary")).toContainText(name);
    await expect(page.getByTestId("frame-summary")).toContainText("3 frames");
    // Either a chart (R Draconis) or the empty-state message, never an error.
    await expect(panel.getByRole("alert")).toHaveCount(0);
    await expect(
      panel.locator(".flux-chart__plot, p.muted:has-text('No photometry')"),
    ).toBeVisible();
  }
});
