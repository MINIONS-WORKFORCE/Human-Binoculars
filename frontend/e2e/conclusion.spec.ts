import { expect, test } from "@playwright/test";

test("displays scientific conclusion for Barnard's Star and updates on target switch", async ({
  page,
}) => {
  await page.goto("/");

  // Verify Barnard's Star conclusion card is rendered
  const card = page.getByTestId("target-conclusion");
  await expect(card).toBeVisible();
  await expect(card).toContainText("About this target");
  await expect(card).toContainText("Barnard's Star");
  await expect(card).toContainText(
    "Barnard's Star has the largest proper motion of any star, about 10.4″ a year",
  );

  // Switch to Difference mode and check difference hint
  await page.getByRole("button", { name: "Difference" }).click();
  await expect(page.getByTestId("blink-hint")).toContainText(
    "bright–dark dipole pair",
  );

  // Switch target preset to WISE 0855
  await page.getByRole("button", { name: "WISE 0855-0714" }).click();
  await expect(card).toContainText("WISE 0855-0714");
  await expect(card).toContainText(
    "WISE 0855 is an ultra-cold sub-stellar brown dwarf",
  );
});
