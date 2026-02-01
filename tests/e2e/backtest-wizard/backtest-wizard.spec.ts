/**
 * E2E Tests for Backtest Wizard
 *
 * Tests the 4-step wizard flow for running ETF arbitrage backtests
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

test.describe('Backtest Wizard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the frontend
    await page.goto(`${BASE_URL}/frontend/index.html`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display backtest tab and wizard interface', async ({ page }) => {
    // Click on backtest tab
    await page.click('text=回测');

    // Wait for wizard to be visible
    await expect(page.locator('#backtest')).toBeVisible();

    // Verify wizard progress indicator is visible
    await expect(page.locator('.wizard-progress')).toBeVisible();

    // Verify 4 steps are shown
    const steps = page.locator('.wizard-step');
    await expect(steps).toHaveCount(4);

    // Verify step labels
    await expect(page.locator('.wizard-step[data-step="1"] .step-label')).toContainText('选择时间');
    await expect(page.locator('.wizard-step[data-step="2"] .step-label')).toContainText('配置策略');
    await expect(page.locator('.wizard-step[data-step="3"] .step-label')).toContainText('预览数据');
    await expect(page.locator('.wizard-step[data-step="4"] .step-label')).toContainText('查看结果');

    // Take screenshot
    await page.screenshot({ path: 'artifacts/backtest-wizard-initial.png' });
  });

  test('should navigate through wizard steps - date selection', async ({ page }) => {
    // Click on backtest tab
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });

    // Verify step 1 is active
    await expect(page.locator('#wizard-step-1.active')).toBeVisible();
    await expect(page.locator('.wizard-step.active[data-step="1"]')).toBeVisible();

    // Test quick date preset buttons
    await page.click('.date-preset[data-months="1"]');
    await page.waitForTimeout(500); // Wait for date picker to update

    // Verify date inputs are filled
    const startDate = page.locator('#wizard-start-date');
    const endDate = page.locator('#wizard-end-date');

    await expect(startDate).toHaveValue(/20\d{2}-\d{2}-\d{2}/);
    await expect(endDate).toHaveValue(/20\d{2}-\d{2}-\d{2}/);

    // Take screenshot of date selection
    await page.screenshot({ path: 'artifacts/backtest-wizard-step1-dates.png' });
  });

  test('should navigate to strategy configuration step', async ({ page }) => {
    // Click on backtest tab and go to step 2
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });

    // Select dates first
    await page.click('.date-preset[data-months="3"]');
    await page.waitForTimeout(500);

    // Click next button
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-2.active', { timeout: 5000 });

    // Verify step 2 is active
    await expect(page.locator('#wizard-step-2.active')).toBeVisible();
    await expect(page.locator('.wizard-step.completed[data-step="1"]')).toBeVisible();
    await expect(page.locator('.wizard-step.active[data-step="2"]')).toBeVisible();

    // Verify strategy templates are loaded
    await expect(page.locator('#strategy-templates')).toBeVisible();
    await expect(page.locator('.strategy-template-card')).toHaveCount(3);

    // Verify template names
    await expect(page.locator('.strategy-template-card')).toContainText(['保守型', '平衡型', '激进型']);

    // Take screenshot of strategy selection
    await page.screenshot({ path: 'artifacts/backtest-wizard-step2-strategy.png' });
  });

  test('should select strategy template and show advanced options', async ({ page }) => {
    // Navigate to step 2
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });
    await page.click('.date-preset[data-months="3"]');
    await page.waitForTimeout(500);
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-2.active', { timeout: 5000 });

    // Select conservative template
    await page.click('.strategy-template-card[data-template-id="conservative"]');

    // Verify it's selected
    await expect(page.locator('.strategy-template-card.selected[data-template-id="conservative"]')).toBeVisible();

    // Click advanced options
    await page.click('text=高级选项');
    await page.waitForSelector('#advanced-options-body.show', { timeout: 2000 });

    // Verify advanced fields are visible
    await expect(page.locator('#wizard-min-weight')).toBeVisible();
    await expect(page.locator('#wizard-min-volume')).toBeVisible();
    await expect(page.locator('#wizard-evaluator')).toBeVisible();
    await expect(page.locator('#wizard-interpolation')).toBeVisible();

    // Verify conservative values are filled
    await expect(page.locator('#wizard-min-weight')).toHaveValue('8');
    await expect(page.locator('#wizard-min-volume')).toHaveValue('8000');

    // Take screenshot
    await page.screenshot({ path: 'artifacts/backtest-wizard-step2-advanced.png' });
  });

  test('should navigate to data preview step', async ({ page }) => {
    // Navigate to step 3
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });
    await page.click('.date-preset[data-months="3"]');
    await page.waitForTimeout(500);
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-2.active', { timeout: 5000 });

    // Select balanced template
    await page.click('.strategy-template-card[data-template-id="balanced"]');

    // Click next to go to preview
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-3.active', { timeout: 5000 });

    // Verify step 3 is active
    await expect(page.locator('#wizard-step-3.active')).toBeVisible();
    await expect(page.locator('.wizard-step.completed[data-step="1"]')).toBeVisible();
    await expect(page.locator('.wizard-step.completed[data-step="2"]')).toBeVisible();
    await expect(page.locator('.wizard-step.active[data-step="3"]')).toBeVisible();

    // Wait for preview to load
    await page.waitForTimeout(1500);

    // Verify preview content
    await expect(page.locator('#data-preview-content')).toBeVisible();
    await expect(page.locator('#data-preview-content')).toContainText(['数据预览功能', '日期范围', '策略模板']);

    // Take screenshot
    await page.screenshot({ path: 'artifacts/backtest-wizard-step3-preview.png' });
  });

  test('should show start backtest button on preview step', async ({ page }) => {
    // Navigate to step 3
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });
    await page.click('.date-preset[data-months="1"]');
    await page.waitForTimeout(500);
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-2.active', { timeout: 5000 });
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-3.active', { timeout: 5000 });
    await page.waitForTimeout(1500);

    // Verify start button is visible and next button is hidden
    await expect(page.locator('#wizard-start-btn')).toBeVisible();
    await expect(page.locator('#wizard-start-btn')).not.toHaveClass('d-none');
    await expect(page.locator('#wizard-next-btn')).toHaveClass('d-none');
  });

  test('should navigate back using previous button', async ({ page }) => {
    // Navigate to step 2
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });
    await page.click('.date-preset[data-months="3"]');
    await page.waitForTimeout(500);
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-2.active', { timeout: 5000 });

    // Click previous button
    await page.click('#wizard-prev-btn');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });

    // Verify we're back on step 1
    await expect(page.locator('#wizard-step-1.active')).toBeVisible();
    await expect(page.locator('.wizard-step[data-step="1"]')).toHaveClass('active');
    await expect(page.locator('.wizard-step[data-step="2"]')).not.toHaveClass('active');
  });

  test('should validate date selection before proceeding', async ({ page }) => {
    // Navigate to backtest
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });

    // Clear date inputs if they have values
    await page.locator('#wizard-start-date').clear();
    await page.locator('#wizard-end-date').clear();

    // Try to click next without selecting dates
    await page.click('#wizard-next-btn');
    await page.waitForTimeout(500);

    // Should still be on step 1 (validation failed)
    await expect(page.locator('#wizard-step-1.active')).toBeVisible();

    // Select dates now
    await page.click('.date-preset[data-months="1"]');
    await page.waitForTimeout(500);

    // Now next should work
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-2.active', { timeout: 5000 });
    await expect(page.locator('#wizard-step-2.active')).toBeVisible();
  });

  test('should load strategy templates from API', async ({ page }) => {
    // Navigate to backtest and wait for step 2
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });
    await page.click('.date-preset[data-months="3"]');
    await page.waitForTimeout(500);
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-2.active', { timeout: 5000 });

    // Wait for API call to complete
    await page.waitForResponse(resp =>
      resp.url().includes('/api/backtest/templates') && resp.status() === 200
    );

    // Verify all 3 templates are displayed
    const templates = page.locator('.strategy-template-card');
    await expect(templates).toHaveCount(3);

    // Verify conservative template
    const conservative = page.locator('.strategy-template-card[data-template-id="conservative"]');
    await expect(conservative).toContainText('保守型');
    await expect(conservative).toContainText('更严格的筛选');
    await expect(conservative).toContainText('8%');
    await expect(conservative).toContainText('8000万');

    // Verify balanced template
    const balanced = page.locator('.strategy-template-card[data-template-id="balanced"]');
    await expect(balanced).toContainText('平衡型');
    await expect(balanced).toContainText('推荐设置');
    await expect(balanced).toContainText('5%');
    await expect(balanced).toContainText('5000万');

    // Verify aggressive template
    const aggressive = page.locator('.strategy-template-card[data-template-id="aggressive"]');
    await expect(aggressive).toContainText('激进型');
    await expect(aggressive).toContainText('更多信号');
    await expect(aggressive).toContainText('3%');
    await expect(aggressive).toContainText('3000万');
  });

  test('should update trading days hint based on date range', async ({ page }) => {
    // Navigate to backtest
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });

    // Select 1 month
    await page.click('.date-preset[data-months="1"]');
    await page.waitForTimeout(500);

    // Check trading days hint
    const hint = page.locator('#trading-days-hint');
    await expect(hint).toContainText('预计需要处理约');
    await expect(hint).not.toContainText('- 个交易日');

    // Select 6 months for more days
    await page.click('.date-preset[data-months="6"]');
    await page.waitForTimeout(500);

    // Hint should show more days
    const hintText = await hint.textContent();
    // 6 months should show more days than 1 month
    await expect(hintText).toBeDefined();
  });

  test('should test full wizard flow end-to-end', async ({ page }) => {
    // Step 1: Select date range
    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });

    await page.click('.date-preset[data-months="1"]');
    await page.waitForTimeout(500);

    // Verify date selection
    await expect(page.locator('#wizard-start-date')).not.toBeEmpty();
    await expect(page.locator('#wizard-end-date')).not.toBeEmpty();

    // Step 2: Configure strategy
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-2.active', { timeout: 5000 });

    // Select aggressive template
    await page.click('.strategy-template-card[data-template-id="aggressive"]');
    await page.waitForTimeout(300);

    // Expand advanced options
    await page.click('text=高级选项');
    await page.waitForSelector('#advanced-options-body.show', { timeout: 2000 });

    // Verify values
    await expect(page.locator('#wizard-min-weight')).toHaveValue('3');
    await expect(page.locator('#wizard-evaluator')).toHaveValue('aggressive');

    // Step 3: Preview data
    await page.click('#wizard-next-btn');
    await page.waitForSelector('#wizard-step-3.active', { timeout: 5000 });
    await page.waitForTimeout(1500);

    // Verify preview loaded
    await expect(page.locator('#data-preview-content')).toContainText('数据预览功能');
    await expect(page.locator('#data-preview-content')).toContainText('aggressive');

    // Take final screenshot before attempting backtest
    await page.screenshot({ path: 'artifacts/backtest-wizard-full-flow.png' });

    // Verify start button is ready
    await expect(page.locator('#wizard-start-btn')).toBeVisible();
    await expect(page.locator('#wizard-start-btn')).not.toHaveClass('d-none');
  });

  test('should have responsive design on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.click('text=回测');
    await page.waitForSelector('#wizard-step-1.active', { timeout: 5000 });

    // Verify wizard is visible on mobile
    await expect(page.locator('.wizard-progress')).toBeVisible();

    // Verify quick date buttons wrap or are accessible
    await expect(page.locator('.date-preset').first()).toBeVisible();

    // Take mobile screenshot
    await page.screenshot({ path: 'artifacts/backtest-wizard-mobile.png' });
  });
});
