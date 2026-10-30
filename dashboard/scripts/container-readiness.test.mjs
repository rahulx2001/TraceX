/** Current production image, real local API/WebSocket; no model or microphone. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium, expect } from '@playwright/test';
import { runReportHandoffTest } from './report-handoff.test.mjs';

const fixture = JSON.parse(await fs.readFile(process.argv[2], 'utf8'));
const base = fixture.base;
assert.equal(new URL(base).hostname, '127.0.0.1', 'This test is restricted to its disposable local container');
const browser = await chromium.launch(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {});
try {
  const context = await browser.newContext();
  await context.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
  const page = await context.newPage();
  await page.goto(`${base}/ui/`);
  await expect(page.getByTestId('signin-page')).toBeVisible();
  await page.getByRole('button', { name: /Have an operator API key/ }).click();
  await page.getByLabel('Operator API key', { exact: true }).fill('invalid-container-test-key');
  await page.getByRole('button', { name: 'Verify & Continue', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('not accepted');
  await page.getByLabel('Operator API key', { exact: true }).fill(fixture.api_key);
  await page.getByRole('button', { name: 'Verify & Continue', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'From an owner report to a reviewable investigation' })).toBeVisible();
  await page.goto(`${base}/ui/#signin?next=demo`);
  await page.getByRole('button', { name: /Have a supervisor session/ }).click();
  await page.getByLabel('Supervisor session', { exact: true }).fill(fixture.supervisor_token);
  await page.getByRole('button', { name: 'Use session', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'From an owner report to a reviewable investigation' })).toBeVisible();
  assert.equal((await context.cookies()).find(c => c.name.endsWith('frontline_session'))?.httpOnly, true);
  await runReportHandoffTest({ page, context, base, fixture });
  console.log('PASS: clean Docker image serves rendered credential entry and the complete text report/correction/revision/review/export workflow. Fixtures only; no real audio or human study.');
  await context.close();
} finally {
  await browser.close();
}
