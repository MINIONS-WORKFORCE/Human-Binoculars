import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("frame-summary")).toContainText(
    "Barnard's Star",
  );
});

test("decimal degrees also show as hours / degrees, and load frames", async ({
  page,
}) => {
  const target = page.getByLabel("Target", { exact: true });
  await target.fill("133.795129 -7.245147");

  const decimal = page.getByTestId("coord-decimal");
  const sexagesimal = page.getByTestId("coord-sexagesimal");
  await expect(decimal).toContainText("typed");
  await expect(decimal).toContainText("RA 133.7951° · Dec −7.2451°");
  await expect(sexagesimal).toContainText("RA 08h55m10.83s · Dec −07°14′42.5″");
  await expect(page.getByTestId("coord-name")).toHaveCount(0);

  await target.press("Enter");
  await expect(page.getByTestId("frame-summary")).toContainText(
    "custom position · RA 08h55m10.83s Dec −07°14′42.5″",
  );
});

test("hours / degrees also show as decimal degrees", async ({ page }) => {
  await page
    .getByLabel("Target", { exact: true })
    .fill("17h57m48.5s +04d41m36s");
  await expect(page.getByTestId("coord-sexagesimal")).toContainText("typed");
  await expect(page.getByTestId("coord-decimal")).toContainText(
    "RA 269.4521° · Dec +4.6933°",
  );
});

test("a name shows the name and both notations", async ({ page }) => {
  await page.getByLabel("Target", { exact: true }).fill("r dra");
  await expect(page.getByTestId("coord-name")).toContainText("R Draconis");
  await expect(page.getByTestId("coord-decimal")).toContainText(
    "RA 248.1676° · Dec +66.7550°",
  );
  await expect(page.getByTestId("coord-sexagesimal")).toContainText(
    "RA 16h32m40.23s · Dec +66°45′17.9″",
  );

  await page.getByRole("button", { name: "Load frames" }).click();
  await expect(page.getByTestId("frame-summary")).toContainText("R Draconis");
});

test("explains bad input and unknown names", async ({ page }) => {
  const target = page.getByLabel("Target", { exact: true });
  await target.fill("400 10");
  await expect(page.getByTestId("coord-preview")).toContainText(
    "RA in degrees must be from 0",
  );
  await expect(target).toHaveAttribute("aria-invalid", "true");

  await target.fill("Planet X");
  await target.press("Enter");
  await expect(page.getByTestId("coord-preview")).toContainText(
    'No object named "Planet X" was found',
  );
});
