import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('AI 驱动的产品管理').first()).toBeVisible()
  })

  test('dashboard loads', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.getByText(/欢迎回来/)).toBeVisible()
  })

  test('templates page loads', async ({ page }) => {
    await page.goto('/templates')
    await expect(page.getByText('Jarvis PM').first()).toBeVisible()
  })

  test('workspace page loads', async ({ page }) => {
    await page.goto('/workspace')
    await expect(page.getByText('项目工作区')).toBeVisible()
  })

  test('skills page loads', async ({ page }) => {
    await page.goto('/skills')
    await expect(page.getByText('技能面板')).toBeVisible()
  })

  test('workflow page loads', async ({ page }) => {
    await page.goto('/workflow')
    await expect(page.getByText('Jarvis PM').first()).toBeVisible()
  })

  test('battle page loads', async ({ page }) => {
    await page.goto('/battle')
    await expect(page.getByText('Jarvis PM').first()).toBeVisible()
  })
})
