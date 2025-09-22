import { expect, test } from '@playwright/test';

test.describe('Admin user management', () => {
  test('shows an error when creating a user without the API', async ({ page }) => {
    await page.goto('/admin/users');

    await expect(page.getByRole('heading', { name: 'User management' })).toBeVisible();

    await page.getByLabel('Username').fill('playwright-user');
    await page.getByLabel('Email').fill('playwright@example.com');
    await page.getByLabel('Temporary password').fill('supersecure123');
    await page.getByRole('button', { name: 'Create user' }).click();

    await expect(
      page.getByText('The admin API did not respond. Please verify the Nest/Prisma service is running and try again.')
    ).toBeVisible();

    await expect(page.getByRole('row', { name: /playwright-user/i })).toHaveCount(0);
  });
});
