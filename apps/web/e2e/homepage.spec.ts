import { test, expect } from '@playwright/test'

test.describe('Homepage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('has correct title and branding', async ({ page }) => {
    await expect(page).toHaveTitle(/Jarvis PM/)
    await expect(page.getByText('Jarvis PM').first()).toBeVisible()
    await expect(page.getByText('AI 驱动的产品管理').first()).toBeVisible()
  })

  test('displays hero section with CTA buttons', async ({ page }) => {
    await expect(page.getByText('用对话方式 10 分钟完成原本需要 2 天的 PRD 撰写和评审准备')).toBeVisible()
    await expect(page.getByRole('link', { name: '免费开始使用' })).toBeVisible()
    await expect(page.getByRole('link', { name: '浏览模板' })).toBeVisible()
  })

  test('displays feature cards', async ({ page }) => {
    await expect(page.getByText('AI PRD 生成')).toBeVisible()
    await expect(page.getByText('评审助手')).toBeVisible()
    await expect(page.getByText('效率提升')).toBeVisible()
  })

  test('displays efficiency comparison section', async ({ page }) => {
    await expect(page.getByText('效率对比').first()).toBeVisible()
    await expect(page.getByText('传统方式')).toBeVisible()
    await expect(page.getByText('Jarvis PM').nth(1)).toBeVisible()
  })

  test('navigation links have correct hrefs', async ({ page }) => {
    const startButton = page.getByRole('link', { name: '开始使用', exact: true })
    await expect(startButton).toBeVisible()
    await expect(startButton).toHaveAttribute('href', '/dashboard')

    const templateLink = page.getByRole('link', { name: '浏览模板' })
    await expect(templateLink).toHaveAttribute('href', '/templates')
  })

  test('footer is visible', async ({ page }) => {
    await expect(page.getByText('© 2026 Jarvis PM. All rights reserved.')).toBeVisible()
  })
})
