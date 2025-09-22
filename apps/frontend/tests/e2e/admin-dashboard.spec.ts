import { expect, test } from '@playwright/test';

test.describe('Admin dashboard', () => {
  test('renders fallback metrics when the API is offline', async ({ page }) => {
    await page.goto('/admin');

    await expect(page.getByRole('heading', { name: 'Executive insights' })).toBeVisible();
    await expect(
      page.getByText(
        'The Prisma API is unavailable right now. The dashboard is showing placeholder data until the connection is restored.'
      )
    ).toBeVisible();

    await expect(page.getByText('No attendance records available for this reporting window.')).toBeVisible();
    await expect(page.getByText('No follow-up activity recorded for this timeframe.')).toBeVisible();
  });
});
