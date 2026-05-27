import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard')
  })

  test('has correct title and header', async ({ page }) => {
    await expect(page.getByText('Jarvis PM').first()).toBeVisible()
    await expect(page.getByText('工作台')).toBeVisible()
  })

  test('displays welcome message', async ({ page }) => {
    await expect(page.getByText(/欢迎回来/)).toBeVisible()
  })

  test('displays quick action buttons', async ({ page }) => {
    await expect(page.getByText('新建 PRD').first()).toBeVisible()
    await expect(page.getByText('数据分析').first()).toBeVisible()
  })

  test('displays projects section', async ({ page }) => {
    await expect(page.getByText('进行中的项目')).toBeVisible()
    // Shows either project list or empty state
    const emptyState = page.getByText('暂无项目')
    const projectCount = page.getByText(/共 \d+ 个项目/)
    await expect(emptyState.or(projectCount)).toBeVisible()
  })

  test('can open skill panel', async ({ page }) => {
    const skillButton = page.getByRole('button', { name: /技能面板/ }).first()
    await skillButton.click()

    await expect(page.getByText('技能面板').first()).toBeVisible()
    await expect(page.getByText('技能链（一键执行）')).toBeVisible()
  })

  test('can open new project modal', async ({ page }) => {
    const newProjectButton = page.getByRole('button', { name: /新建项目/ }).first()
    await newProjectButton.click()

    await expect(page.getByText('新建项目').first()).toBeVisible()
    await expect(page.getByPlaceholder('输入项目名称')).toBeVisible()
    await expect(page.getByPlaceholder('输入项目描述')).toBeVisible()
  })

  test('can open feedback modal', async ({ page }) => {
    const feedbackButton = page.getByRole('button', { name: /反馈/ }).first()
    await feedbackButton.click()

    await expect(page.getByText('意见反馈').first()).toBeVisible()
    await expect(page.getByPlaceholder('请描述你的建议或遇到的问题...')).toBeVisible()
  })

  test('displays stats section', async ({ page }) => {
    await expect(page.getByText('AI 助手使用统计')).toBeVisible()
    await expect(page.getByText('AI 技能调用')).toBeVisible()
    await expect(page.getByText('PRD 生成')).toBeVisible()
    await expect(page.getByText('评审准备')).toBeVisible()
    await expect(page.getByText('站会报告')).toBeVisible()
  })

  test('logo link is present', async ({ page }) => {
    const logoLink = page.getByRole('link').filter({ hasText: 'Jarvis PM' }).first()
    await expect(logoLink).toBeVisible()
    await expect(logoLink).toHaveAttribute('href', '/')
  })
})
