import { expect, test, type Page } from "@playwright/test";

const controls = (page: Page) => page.locator("form.controls");
const framesRequest = (page: Page) =>
  page.waitForRequest((r) => r.url().includes("/api/frames?"));

/** Frames are always fetched for the widest field (10′); FOV only zooms. */
const FETCH_SIZE = "0.1667";

test("FOV zooms without a request; detector refetches; both go in the URL (FR-02, FR-03)", async ({
  page,
}) => {
  const first = framesRequest(page);
  await page.goto("/");
  expect(new URL((await first).url()).searchParams.get("size")).toBe(
    FETCH_SIZE,
  );
  await expect(page.getByTestId("frame-summary")).toContainText("detector D6");

  const calls: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/frames?")) calls.push(r.url());
  });
  await controls(page).getByLabel("Field of view").selectOption("2");
  await expect(page.getByTestId("zoom-readout")).toContainText("×");
  expect(calls).toEqual([]);

  const detector = framesRequest(page);
  await controls(page).getByLabel("Detector").selectOption("3");
  const request = new URL((await detector).url());
  expect(request.searchParams.get("detector")).toBe("3");
  expect(request.searchParams.get("size")).toBe(FETCH_SIZE);
  await expect(page.getByTestId("frame-summary")).toContainText("detector D3");

  const url = new URL(page.url());
  expect(url.searchParams.get("q")).toBe("Barnard's Star");
  expect(url.searchParams.get("fov")).toBe("2");
  expect(url.searchParams.get("det")).toBe("D3");
});

test("reloading the page reopens the same view (QA-03)", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "R Draconis" }).click();
  await controls(page).getByLabel("Field of view").selectOption("2");
  await controls(page).getByLabel("Detector").selectOption("2");
  await expect(page.getByTestId("frame-summary")).toContainText("detector D2");

  await page.reload();

  await expect(page.getByTestId("frame-summary")).toContainText("R Draconis");
  await expect(page.getByTestId("frame-summary")).toContainText("detector D2");
  await expect(
    controls(page).getByLabel("Target", { exact: true }),
  ).toHaveValue("R Draconis");
  await expect(controls(page).getByLabel("Field of view")).toHaveValue("2");
  await expect(controls(page).getByLabel("Detector")).toHaveValue("2");
});

test("a link with coordinates opens that position, zoom and detector", async ({
  page,
}) => {
  const request = framesRequest(page);
  await page.goto("/?q=133.7951%20-7.2451&fov=2&det=D4");

  const sent = new URL((await request).url());
  expect(sent.searchParams.get("ra")).toBe("133.7951");
  expect(sent.searchParams.get("dec")).toBe("-7.2451");
  expect(sent.searchParams.get("size")).toBe(FETCH_SIZE);
  expect(sent.searchParams.get("detector")).toBe("4");
  await expect(page.getByTestId("frame-summary")).toContainText(
    "custom position",
  );
  await expect(page.getByTestId("frame-summary")).toContainText("detector D4");
  await expect(controls(page).getByLabel("Field of view")).toHaveValue("2");
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
