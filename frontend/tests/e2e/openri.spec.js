import { expect, test } from "@playwright/test";
import { AxeBuilder } from "@axe-core/playwright";

test("runs sample manuscript and exposes findings", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Run Text/ }).click();
  await expect(page.getByRole("button", { name: /Statistical consistency/ })).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/AI Reviewer Protocol/)).toBeVisible();
});

test("shows structured API error for invalid upload", async ({ page }) => {
  await page.goto("/");
  await page.setInputFiles('input[type="file"]', {
    name: "paper.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("not a manuscript"),
  });
  await page.getByRole("button", { name: /Run PDF\/File/ }).click();
  await expect(page.getByText(/invalid_pdf_magic|Upload API returned 422/)).toBeVisible({ timeout: 15000 });
});

test("basic accessibility smoke", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).disableRules(["color-contrast"]).analyze();
  expect(results.violations).toEqual([]);
});
