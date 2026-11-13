import { expect, test, type Page } from "@playwright/test";

const controls = (page: Page) => page.locator("form.controls");
const framesRequest = (page: Page) =>
  page.waitForRequest((r) => r.url().includes("/api/frames?"));

test("FOV and detector change the request and the URL (FR-02, FR-03)", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByTestId("frame-summary")).toContainText("detector D6");

  const fov = framesRequest(page);
  await controls(page).getByLabel("Field of view").selectOption("5");
  expect(new URL((await fov).url()).searchParams.get("size")).toBe("0.0833");

  const detector = framesRequest(page);
  await controls(page).getByLabel("Detector").selectOption("3");
  const request = new URL((await detector).url());
  expect(request.searchParams.get("detector")).toBe("3");
  expect(request.searchParams.get("size")).toBe("0.0833");
  await expect(page.getByTestId("frame-summary")).toContainText("detector D3");

  const url = new URL(page.url());
  expect(url.searchParams.get("q")).toBe("Barnard's Star");
  expect(url.searchParams.get("fov")).toBe("5");
  expect(url.searchParams.get("det")).toBe("D3");
});

test("reloading the page reopens the same view (QA-03)", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "R Draconis" }).click();
  await controls(page).getByLabel("Field of view").selectOption("10");
  await controls(page).getByLabel("Detector").selectOption("2");
  await expect(page.getByTestId("frame-summary")).toContainText("detector D2");

  await page.reload();

  await expect(page.getByTestId("frame-summary")).toContainText("R Draconis");
  await expect(page.getByTestId("frame-summary")).toContainText("detector D2");
  await expect(
    controls(page).getByLabel("Target", { exact: true }),
  ).toHaveValue("R Draconis");
  await expect(controls(page).getByLabel("Field of view")).toHaveValue("10");
  await expect(controls(page).getByLabel("Detector")).toHaveValue("2");
});

test("a link with coordinates opens that position, size and detector", async ({
  page,
}) => {
  const request = framesRequest(page);
  await page.goto("/?q=133.7951%20-7.2451&fov=2&det=D4");

  const sent = new URL((await request).url());
  expect(sent.searchParams.get("ra")).toBe("133.7951");
  expect(sent.searchParams.get("dec")).toBe("-7.2451");
  expect(sent.searchParams.get("size")).toBe("0.0333");
  expect(sent.searchParams.get("detector")).toBe("4");
  await expect(page.getByTestId("frame-summary")).toContainText(
    "custom position",
  );
  await expect(page.getByTestId("frame-summary")).toContainText("detector D4");
});

test("a link with a name the page cannot find says so and opens Barnard", async ({
  page,
}) => {
  await page.goto("/?q=Planet%20X");
  await expect(page.getByTestId("coord-preview")).toContainText(
    'No object named "Planet X" was found',
  );
  await expect(page.getByTestId("frame-summary")).toContainText(
    "Barnard's Star",
  );
});
