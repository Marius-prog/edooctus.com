import { test, expect } from "@playwright/test";

test.describe("Cookie banner", () => {
  test("appears on first visit", async ({ page, context }) => {
    await context.clearCookies();
    await page.goto("/");
    await expect(page.locator("#cookie-banner")).toBeVisible();
    await expect(page.locator("#cookie-accept")).toBeVisible();
    await expect(page.locator("#cookie-reject")).toBeVisible();
  });

  test("accept hides banner and stores choice", async ({ page, context }) => {
    await context.clearCookies();
    await page.goto("/");
    await page.click("#cookie-accept");
    await expect(page.locator("#cookie-banner")).toBeHidden();
    const stored = await page.evaluate(() =>
      localStorage.getItem("educto.cookie_consent_v1"),
    );
    expect(stored).toBe("granted");
  });

  test("reject hides banner and stores choice", async ({ page, context }) => {
    await context.clearCookies();
    await page.goto("/");
    await page.click("#cookie-reject");
    await expect(page.locator("#cookie-banner")).toBeHidden();
    const stored = await page.evaluate(() =>
      localStorage.getItem("educto.cookie_consent_v1"),
    );
    expect(stored).toBe("rejected");
  });

  test("does not reappear after decision", async ({ page, context }) => {
    await context.clearCookies();
    await page.goto("/");
    await page.click("#cookie-accept");
    await page.reload();
    await expect(page.locator("#cookie-banner")).toBeHidden();
  });
});
