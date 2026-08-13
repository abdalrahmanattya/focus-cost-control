import { test, expect } from '@playwright/test';

test('browser product flow imports, edits, analyzes, exports, and shows DLQ state', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Focus Cost Control' })).toBeVisible();
  await expect(page.getByText('Total imported cost')).toBeVisible();

  await page.getByLabel('Import CSV').setInputFiles('../fixtures/sample.csv');
  await expect(page.getByText(/completed/).first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/inserted/).first()).toBeVisible();

  await page.getByLabel('Percent').fill('100');
  await page.getByRole('button', { name: 'Save', exact: true }).first().click();
  await expect(page.getByText('Provider allocation')).toBeVisible();
  await page.getByLabel('Orders').fill('2000');
  await page.getByRole('button', { name: 'Save', exact: true }).nth(1).click();
  await expect(page.getByText(/^\$.* per order$/)).toBeVisible();
  await expect(page.getByText('Next month forecast')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Anomalies' })).toBeVisible();

  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export costs' }).click();
  expect((await download).suggestedFilename()).toBe('focus-cost-records.csv');

  const status = await page.request.get('/api/v1/imports');
  expect(status.ok()).toBeTruthy();
  expect((await status.json()).dead_letter_count).toBeGreaterThanOrEqual(0);
});
