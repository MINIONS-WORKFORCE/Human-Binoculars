// QA-16 / NFR-06: every control is at least 44px tall and Tab reaches all of them.
// The sky map (Aladin Lite) and the plot (Plotly) draw their own small buttons, so
// they are left out of the size check.
import { expect, test, type Page } from "@playwright/test";

const OWN_CONTROLS =
  "main button, main select, main input, main summary, main a[href]";
const THIRD_PARTY = ".skymap__map, .flux-chart__plot";

async function openLoaded(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "R Draconis" }).click();
  await expect(page.getByTestId("frame-summary")).toContainText("R Draconis");
  await expect(page.locator(".flux-chart__plot")).toBeVisible();
  await expect(page.getByTestId("frame-counter")).toBeVisible();
}

test("our controls are at least 44px tall", async ({ page }) => {
  await openLoaded(page);
  const small = await page.evaluate(
    ([own, third]) =>
      Array.from(document.querySelectorAll<HTMLElement>(own))
        .filter((el) => !el.closest(third))
        .map((el) => {
          // A checkbox is switched by clicking its label, so the label is the target.
          const target =
            el instanceof HTMLInputElement && el.type === "checkbox"
              ? (el.closest("label") ?? el)
              : el;
          const box = target.getBoundingClientRect();
          return {
            what: `${el.tagName.toLowerCase()} "${(el.getAttribute("aria-label") ?? el.textContent ?? el.id).trim().slice(0, 30)}"`,
            height: box.height,
            shown: box.width > 0,
          };
        })
        .filter((c) => c.shown && c.height < 43.5),
    [OWN_CONTROLS, THIRD_PARTY],
  );
  expect(small).toEqual([]);
});

test("Tab reaches every one of our controls", async ({ page }) => {
  await openLoaded(page);
  // Stop the blink so it does not move under the test.
  await page.getByRole("button", { name: "Pause" }).click();

  const count = await page.evaluate(
    ([own, third]) => {
      const controls = Array.from(
        document.querySelectorAll<HTMLElement>(own),
      ).filter(
        (el) =>
          !el.closest(third) &&
          el.getBoundingClientRect().width > 0 &&
          !(el as HTMLButtonElement).disabled,
      );
      controls.forEach((el, i) => el.setAttribute("data-tab-check", String(i)));
      return controls.length;
    },
    [OWN_CONTROLS, THIRD_PARTY],
  );
  expect(count).toBeGreaterThan(10);

  await page.evaluate(() => (document.activeElement as HTMLElement)?.blur());
  const reached = new Set<string>();
  for (let step = 0; step < 150; step++) {
    await page.keyboard.press("Tab");
    const id = await page.evaluate(() =>
      document.activeElement?.getAttribute("data-tab-check"),
    );
    if (id) reached.add(id);
    if (reached.size === count) break;
  }
  expect(reached.size).toBe(count);
});
