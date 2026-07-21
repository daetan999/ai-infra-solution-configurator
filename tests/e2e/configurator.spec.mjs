import { expect, test } from "@playwright/test";

test("completes the synthetic discovery-to-export journey", async ({ page }) => {
  const consoleErrors = [];
  const pageErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/");
  await expect(page.locator("#engine-status-label")).toHaveText("Rules engine online");
  await expect(page.locator("#scenario-rail .scenario-item")).toHaveCount(3);

  await page.locator("#solution-tab").click();
  await expect(page.locator("#recommendation-traces .trace-item")).toHaveCount(13);
  await expect(page.locator("#confidence-score")).toContainText("%");
  await page.locator("#assumptions-tab").click();
  await expect(page.locator("#solution-assumptions li")).toHaveCount(5);
  await expect(page.locator("#solution-assumptions")).not.toContainText(
    "No explicit assumptions were returned.",
  );

  await page.locator("#new-scenario").click();
  await page.locator('input[name="name"]').fill("Fictional CI Governed Feature Platform");
  await page.locator('textarea[name="description"]').fill(
    "A fictional governed feature service used to verify the complete browser workflow.",
  );
  for (const stage of [2, 3, 4, 5]) {
    await page.locator("#next-stage").click();
    await expect(page.locator(`[data-stage-panel="${stage}"]`)).toBeVisible();
  }
  await page.locator("#hypothesis-confirmation").check();
  await page.locator("#generate-solution").click();
  await expect(page.getByText("Fictional CI Governed Feature Platform", { exact: true }).first()).toBeVisible();
  await expect(page.locator("#scenario-rail .scenario-item")).toHaveCount(4);

  for (const [label, extension] of [["JSON", ".json"], ["Markdown", ".md"], ["SVG", ".svg"]]) {
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: label, exact: true }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename().endsWith(extension)).toBe(true);
  }
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test("retains accessible mobile layout boundaries", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    skipLink: Boolean(document.querySelector('.skip-link[href="#workspace"]')),
    namedStages: [...document.querySelectorAll(".stage-tab")].every((tab) =>
      /^Stage [1-5]: /.test(tab.getAttribute("aria-label") || ""),
    ),
  }));

  expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewport + 1);
  expect(layout.skipLink).toBe(true);
  expect(layout.namedStages).toBe(true);
});
