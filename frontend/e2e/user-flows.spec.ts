import { expect, test, type Page } from "@playwright/test";
import { createClient } from "@supabase/supabase-js";
import { config } from "dotenv";

config({ path: ".env.local" });

const email = process.env.E2E_TEST_EMAIL;
const password = process.env.E2E_TEST_PASSWORD;

async function logIn(page: Page) {
    await page.goto("/login");

    await page.getByPlaceholder("Email").fill(email!);
    await page.getByPlaceholder("Password").fill(password!);
    await page.getByRole("button", { name: "Log In" }).click();

    await expect(page).toHaveURL(/\/$/);
}

test("redirects unauthenticated users away from protected pages", async ({
    page,
}) => {
    await page.goto("/portfolio");
    await expect(page).toHaveURL(/\/login$/);

    await page.goto("/profile");
    await expect(page).toHaveURL(/\/login$/);
});

test.describe("authenticated Supabase flows", () => {
    test.skip(
        !email || !password,
        "Add E2E_TEST_EMAIL and E2E_TEST_PASSWORD to .env.e2e first."
    );

    test("adds and removes a portfolio holding", async ({ page }) => { 
        await logIn(page);
        await page.goto("/portfolio");

        await expect(
            page.getByRole("heading", { name: "Portfolio Tracker" }),        
        ).toBeVisible();

        await page.getByPlaceholder("Ticker, e.g. AAPL").fill("AAPL");
        await page.getByPlaceholder("Shares").fill("0.000001");
        await page.getByPlaceholder("Purchase Price").fill("1");
        await page.locator('input[type="date"]').fill("2000-01-01");

        await page.getByRole("button", { name: "Add holding" }).click();

        await expect(
            page.getByText("AAPL added to your portfolio."),
        ).toBeVisible();

        const holdingRow = page
            .getByText("2000-01-01", { exact: true })
            .locator("xpath=../..");

        await holdingRow.getByRole("button", { name: "Remove" }).click();

        await expect(
            page.getByText("Holding removed from your portfolio."),
        ).toBeVisible();
    });

    test("creates a watchlist, adds a ticker, and deletes the watchlist", async ({
        page,
    }) => { 
        await logIn(page);
        await page.goto("/");

        const watchlistName = `E2E Test Watchlist ${Date.now()}`;

        await page.getByPlaceholder("e.g. Long-Term").fill(watchlistName);
        await page.getByRole("button", { name: "New" }).click();

        await expect(
            page.getByText(`${watchlistName} watchlist created.`),
        ).toBeVisible();

        await page
            .getByPlaceholder("Ticker Symbol, e.g. AAPL")
            .fill("AAPL");
        await page.getByRole("button", { name: "Add" }).click();

        await expect(
            page.getByText(`AAPL added to ${watchlistName}.`),
        ).toBeVisible();

        await page.getByRole("button", { name: "Delete Watchlist" }).click();

        await expect(
            page.getByText(`${watchlistName} deleted.`),
        ).toBeVisible();
    });

    test("saves research history after a completed request", async ({ page }) => {
        const question = `E2E research history check ${Date.now()}`;

        await page.route("**/research", async (route) => { 
            if (route.request().method() !== "POST") { 
                await route.continue();
                return;
            }

            await route.fulfill({
                contentType: "application/json",
                body: JSON.stringify({
                    ticker: "AAPL",
                    question,
                    answer: "This is an automated E2E research response [1].",
                    citations: [],
                }),
            });
        });

        await logIn(page);
        await page.goto("/research");

        await page.locator("#ticker").fill("AAPL");
        await page.locator("#question").fill(question);
        await page.getByRole("button", { name: /Research AAPL/ }).click();

        await expect(page.getByText(question, { exact: true })).toHaveCount(2);

        const supabase = createClient(
            process.env.NEXT_PUBLIC_SUPABASE_URL!,
            process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
        );

        const { error: loginError } = await supabase.auth.signInWithPassword({
            email: email!,
            password: password!,
        });

        expect(loginError).toBeNull();

        const { error: deleteError } = await supabase
            .from("research_history")
            .delete()
            .eq("question", question);

        await supabase.auth.signOut();

        expect(deleteError).toBeNull();
    });
});
