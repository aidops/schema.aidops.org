import { test, expect } from "@playwright/test";

test.describe("Homepage", () => {
  test("homepage loads with AidOps branding", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Humanitarian assessment profiles/);
    await expect(page.locator(".site-title-aid")).toBeVisible();
    await expect(page.locator("nav")).toContainText("Concepts");
    await expect(page.locator("nav")).toContainText("Properties");
    await expect(page.locator("nav")).toContainText("Vocabularies");
  });

  test("homepage has hero section with profile links", async ({ page }) => {
    await page.goto("/");
    const hero = page.locator(".h3-hero");
    await expect(hero).toBeVisible();
    await expect(page.locator("#index")).toBeVisible();
  });
});

test.describe("Concepts", () => {
  test("concepts index loads", async ({ page }) => {
    await page.goto("/concepts/");
    await expect(page).toHaveTitle(/Concepts/);
    await expect(page.locator("table.data-table")).toBeVisible();
  });

  test("FoodSecurityProfile concept page exists and has properties", async ({
    page,
  }) => {
    await page.goto("/FoodSecurityProfile/");
    await expect(page).toHaveTitle(/FoodSecurityProfile/);
    await expect(page.locator("#properties")).toBeVisible();
    // Should show maturity badge
    await expect(page.locator(".meta-line .badge")).toBeVisible();
  });

  test("FunctioningProfile concept page exists", async ({ page }) => {
    await page.goto("/FunctioningProfile/");
    await expect(page).toHaveTitle(/FunctioningProfile/);
  });

  test("AnthropometricProfile concept page exists", async ({ page }) => {
    await page.goto("/AnthropometricProfile/");
    await expect(page).toHaveTitle(/AnthropometricProfile/);
  });
});

test.describe("Properties", () => {
  test("properties index loads", async ({ page }) => {
    await page.goto("/properties/");
    await expect(page).toHaveTitle(/Properties/);
    await expect(page.locator("table.data-table")).toBeVisible();
  });
});

test.describe("Vocabularies", () => {
  test("vocabularies index loads", async ({ page }) => {
    await page.goto("/vocabularies/");
    await expect(page).toHaveTitle(/Vocabularies/);
    await expect(page.locator("table.data-table")).toBeVisible();
  });
});

test.describe("About", () => {
  test("about page loads", async ({ page }) => {
    await page.goto("/about/");
    await expect(page).toHaveTitle(/About AidOps/);
    await expect(page.locator("h1")).toContainText("About AidOps");
  });
});

test.describe("i18n", () => {
  test("French concepts index loads", async ({ page }) => {
    await page.goto("/fr/concepts/");
    await expect(page.locator("html")).toHaveAttribute("lang", "fr");
    await expect(page.locator("table.data-table")).toBeVisible();
  });

  test("Spanish homepage loads", async ({ page }) => {
    await page.goto("/es/");
    await expect(page.locator("html")).toHaveAttribute("lang", "es");
  });
});
