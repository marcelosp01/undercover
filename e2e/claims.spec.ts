import { expect, test } from "@playwright/test";

test("the queue lists the 25 claims", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(25);
});

test("a claim page shows the story and documents", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page.getByText("My flight home from Rome")).toBeVisible();
  await expect(page.getByText("Hotel receipt")).toBeVisible();
  await expect(page.getByText("No decision yet.")).toBeVisible();
});

test("the agent decides and pays a claim under the limit", async ({ page }) => {
  await page.goto("/#/claims/CLM-1001");
  await page.getByRole("button", { name: "Run agent" }).click();
  await expect(page.getByText("Paid $420.00.")).toBeVisible();
  await expect(page.locator(".badge")).toHaveText("Decided");
  await expect(page.getByText("Tried to pay $420.00")).toBeVisible();
});

test("a payout over the limit waits for a handler", async ({ page }) => {
  await page.goto("/#/claims/CLM-1002");
  await page.getByRole("button", { name: "Run agent" }).click();
  await expect(page.locator(".badge")).toHaveText("Waiting for sign-off");
  await expect(page.getByText(/The system refused: Error 409/)).toBeVisible();
  await page.getByRole("button", { name: "Sign off and pay" }).click();
  await expect(page.locator(".badge")).toHaveText("Decided");
  await expect(page.getByText("Signed off by Dana Whitfield.")).toBeVisible();
  await expect(page.getByText("Paid $1,150.00.")).toBeVisible();
});

test("the instructions are read only", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Agent instructions" }).click();
  await expect(page.getByText("You are the UnderCover Agent")).toBeVisible();
  await expect(page.locator("input, textarea")).toHaveCount(0);
});
