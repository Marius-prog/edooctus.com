import { test, expect } from "@playwright/test";

/**
 * Smoke test for the AI sandbox HTMX flow.
 * Requires:
 *   - a test user `e2e_user / e2e_pass!`
 *   - a registered AITool with slug `echo` and provider `local`
 * Seed both via the `seed_e2e` management command before running CI.
 */
const USER = process.env.E2E_USERNAME || "e2e_user";
const PASS = process.env.E2E_PASSWORD || "e2e_pass!";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/accounts/login/");
  await page.fill("input[name='username']", USER);
  await page.fill("input[name='password']", PASS);
  await page.click("button[type='submit']");
}

test("sandbox runs an echo prompt and shows result", async ({ page }) => {
  await login(page);
  await page.goto("/ai/sandbox/echo/");
  await page.fill("textarea[name='prompt']", "hello world");
  await page.click("button[type='submit']");
  // HTMX swaps a partial into #sandbox-result
  const result = page.locator("#sandbox-result");
  await expect(result).toContainText("fake:echo", { timeout: 10_000 });
  await expect(result).toContainText("hello world");
});
