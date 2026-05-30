import { test, expect } from "@playwright/test";

/** Smoke: anonymous home page loads. */
test("anonymous home page returns 200 and renders title", async ({ page }) => {
  const response = await page.goto("/");
  expect(response?.status()).toBeLessThan(400);
  await expect(page).toHaveTitle(/educto|course|home/i);
});

test("login page is reachable", async ({ page }) => {
  const response = await page.goto("/accounts/login/");
  expect(response?.status()).toBeLessThan(400);
  await expect(page.locator("input[name='username']")).toBeVisible();
  await expect(page.locator("input[name='password']")).toBeVisible();
});

test("registration page is reachable", async ({ page }) => {
  const response = await page.goto("/students/register/");
  expect(response?.status()).toBeLessThan(400);
});

test("404 page works", async ({ page }) => {
  const response = await page.goto("/this-does-not-exist/");
  expect(response?.status()).toBe(404);
});
