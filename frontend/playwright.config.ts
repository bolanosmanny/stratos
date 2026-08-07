import { defineConfig } from '@playwright/test';
import { config } from 'dotenv';

config({ path: ".env.e2e" });

export default defineConfig({
    testDir: "./e2e",
    fullyParallel: false,
    workers: 1,
    timeout: 45_000,
    reporter: "list",
    expect: {
        timeout: 15_000,
    },

    use: {
        baseURL: "http://localhost:3000",
        trace: "on-first-retry",
    },

    webServer: {
        command: "npm run dev",
        url: "http://localhost:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
    },
});