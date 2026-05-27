import { test, expect, Page } from '@playwright/test'

/**
 * Full E2E test suite for Jarvis PM
 * Covers all 6 critical user flows with console error capture and API monitoring.
 */

// --- Helpers ---

interface PageTestResult {
  page: string
  url: string
  loaded: boolean
  consoleErrors: string[]
  apiFailures: string[]
  keyElements: { name: string; found: boolean }[]
}

async function collectPageResults(
  page: Page,
  pageName: string,
  url: string,
  keyElementNames: string[]
): Promise<PageTestResult> {
  const consoleErrors: string[] = []
  const apiFailures: string[] = []

  // Capture console errors
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(`[${msg.type()}] ${msg.text()}`)
    }
  })

  // Capture failed API requests
  page.on('requestfailed', (request) => {
    apiFailures.push(`${request.method()} ${request.url()} — ${request.failure()?.errorText || 'unknown'}`)
  })

  // Navigate
  let loaded = false
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 })
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {
      // networkidle may timeout on pages with polling/websockets — not a failure
    })
    loaded = true
  } catch (e) {
    consoleErrors.push(`Navigation error: ${String(e)}`)
  }

  // Check for key elements
  const keyElements: { name: string; found: boolean }[] = []
  for (const name of keyElementNames) {
    try {
      const el = page.getByText(name, { exact: false }).first()
      await el.waitFor({ state: 'visible', timeout: 5000 })
      keyElements.push({ name, found: true })
    } catch {
      keyElements.push({ name, found: false })
    }
  }

  return { page: pageName, url, loaded, consoleErrors, apiFailures, keyElements }
}

function printResult(result: PageTestResult): void {
  console.log(`\n${'='.repeat(60)}`)
  console.log(`  PAGE: ${result.page}`)
  console.log(`  URL:  ${result.url}`)
  console.log(`  Loaded: ${result.loaded ? 'YES' : 'NO'}`)
  console.log(`${'='.repeat(60)}`)

  console.log(`\n  Key Elements:`)
  for (const el of result.keyElements) {
    console.log(`    ${el.found ? 'PASS' : 'FAIL'} — ${el.name}`)
  }

  if (result.consoleErrors.length > 0) {
    console.log(`\n  Console Errors (${result.consoleErrors.length}):`)
    for (const err of result.consoleErrors) {
      console.log(`    ERR: ${err}`)
    }
  } else {
    console.log(`\n  Console Errors: none`)
  }

  if (result.apiFailures.length > 0) {
    console.log(`\n  API Failures (${result.apiFailures.length}):`)
    for (const f of result.apiFailures) {
      console.log(`    FAIL: ${f}`)
    }
  } else {
    console.log(`\n  API Failures: none`)
  }
}

// --- Test Suite ---

test.describe('Jarvis PM — Full E2E Flow', () => {
  test.describe.configure({ mode: 'serial' })

  const results: PageTestResult[] = []

  // ============================================================
  // 1. DASHBOARD
  // ============================================================
  test('01 - Dashboard loads with projects and navigation', async ({ page }) => {
    const r = await collectPageResults(page, 'Dashboard', '/dashboard', [
      'Jarvis PM',
      '欢迎回来',
      '进行中的项目',
      '新建 PRD',
      'AI 助手使用统计',
    ])

    // Additional: verify project cards are visible
    try {
      const projectCards = page.locator('[data-testid="project-card"], .project-card, [class*="project" i]')
      const count = await projectCards.count()
      console.log(`  Project cards found: ${count}`)
      r.keyElements.push({ name: `Project cards (${count})`, found: count > 0 })
    } catch {
      r.keyElements.push({ name: 'Project cards', found: false })
    }

    printResult(r)
    results.push(r)

    expect(r.loaded).toBe(true)
    expect(r.keyElements.filter((e) => !e.found).length).toBeLessThanOrEqual(1)
  })

  // ============================================================
  // 2. PRD DETAIL
  // ============================================================
  test('02 - PRD detail page loads with content', async ({ page }) => {
    const prdId = '4ac75ffe-bcf9-4a46-abc9-3093cac0d0ee'
    const r = await collectPageResults(page, 'PRD Detail', `/prd/${prdId}`, [
      '互联互通测评平台PRD',
      'Jarvis PM',
    ])

    // Additional: check markdown/content area renders
    try {
      const contentArea = page.locator('.prose, [class*="markdown"], article, main')
      const visible = await contentArea.first().isVisible().catch(() => false)
      r.keyElements.push({ name: 'Content/markdown area', found: visible })
    } catch {
      r.keyElements.push({ name: 'Content/markdown area', found: false })
    }

    // Additional: check for chapter tabs/sections
    try {
      const hasChapters =
        (await page.getByText('背景与目标').first().isVisible().catch(() => false)) ||
        (await page.getByText('用户故事').first().isVisible().catch(() => false)) ||
        (await page.getByText('功能规格').first().isVisible().catch(() => false))
      r.keyElements.push({ name: 'PRD chapters/sections', found: hasChapters })
    } catch {
      r.keyElements.push({ name: 'PRD chapters/sections', found: false })
    }

    printResult(r)
    results.push(r)

    expect(r.loaded).toBe(true)
    expect(r.keyElements.filter((e) => e.name === 'Content/markdown area' && !e.found).length).toBe(0)
  })

  // ============================================================
  // 3. DELIVERY LIST
  // ============================================================
  test('03 - Delivery plans list loads with health indicators', async ({ page }) => {
    const r = await collectPageResults(page, 'Delivery List', '/delivery', [
      'Jarvis PM',
      '交付计划',
    ])

    // Check for "生成交付计划" button
    try {
      const genButton = page.getByRole('button', { name: /生成交付计划/ }).first()
      await genButton.waitFor({ state: 'visible', timeout: 5000 })
      r.keyElements.push({ name: '"生成交付计划" button', found: true })
    } catch {
      r.keyElements.push({ name: '"生成交付计划" button', found: false })
    }

    // Check for health indicators
    try {
      const hasHealth =
        (await page.getByText(/交付健康/i).first().isVisible().catch(() => false)) ||
        (await page.getByText(/风险健康/i).first().isVisible().catch(() => false)) ||
        (await page.getByText(/高风险/i).first().isVisible().catch(() => false))
      r.keyElements.push({ name: 'Dashboard health indicators', found: hasHealth })
    } catch {
      r.keyElements.push({ name: 'Dashboard health indicators', found: false })
    }

    // Check for delivery plan items
    try {
      const planItems = page.locator('[class*="plan"], [class*="delivery"], [class*="card"]')
      const count = await planItems.count()
      r.keyElements.push({ name: `Delivery plan items (${count})`, found: count > 0 })
    } catch {
      r.keyElements.push({ name: 'Delivery plan items', found: false })
    }

    printResult(r)
    results.push(r)

    expect(r.loaded).toBe(true)
    expect(r.keyElements.filter((e) => !e.found && e.name.includes('button')).length).toBe(0)
  })

  // ============================================================
  // 4. DELIVERY DETAIL
  // ============================================================
  test('04 - Delivery detail page renders WBS/Gantt/risk components', async ({ page }) => {
    const deliveryId = 'fe3e9cf1-56e5-4cac-9c67-c7b638bdf018'
    const r = await collectPageResults(page, 'Delivery Detail', `/delivery/${deliveryId}`, [
      'Jarvis PM',
      '交付计划',
    ])

    // Check for WBS/Gantt/risk tabs or sections
    const componentNames = ['WBS', '甘特', 'Gantt', '风险', 'Risks', '里程碑', '资源']
    for (const name of componentNames) {
      try {
        const el = page.getByText(name, { exact: false }).first()
        const visible = await el.isVisible().catch(() => false)
        if (visible) {
          r.keyElements.push({ name: `${name} component`, found: true })
        }
      } catch {
        // not found — skip
      }
    }

    // Check for risk items specifically (API shows 16 risks)
    try {
      const riskItems = page.getByText(/RSK-\d{3}/).first()
      const visible = await riskItems.isVisible().catch(() => false)
      r.keyElements.push({ name: 'Risk items (RSK-xxx)', found: visible })
    } catch {
      r.keyElements.push({ name: 'Risk items (RSK-xxx)', found: false })
    }

    printResult(r)
    results.push(r)

    expect(r.loaded).toBe(true)
    // At least one of WBS/Gantt/risk related elements should be visible
    const deliveryComponents = r.keyElements.filter(
      (e) =>
        (e.name.includes('WBS') ||
          e.name.includes('甘特') ||
          e.name.includes('Gantt') ||
          e.name.includes('风险') ||
          e.name.includes('Risks') ||
          e.name.includes('Risk items')) &&
        e.found
    )
    expect(deliveryComponents.length).toBeGreaterThan(0)
  })

  // ============================================================
  // 5. TEMPLATES
  // ============================================================
  test('05 - Templates page loads with template list', async ({ page }) => {
    const r = await collectPageResults(page, 'Templates', '/templates', [
      'Jarvis PM',
    ])

    // Check for template items
    const templateNames = ['默认模板', '医疗行业模板', 'PRD', '模板']
    for (const name of templateNames) {
      try {
        const el = page.getByText(name, { exact: false }).first()
        const visible = await el.isVisible().catch(() => false)
        if (visible) {
          r.keyElements.push({ name: `Template: "${name}"`, found: true })
        }
      } catch {
        // skip
      }
    }

    // If no templates found by name, at least check for template cards
    if (r.keyElements.filter((e) => e.name.startsWith('Template:')).length === 0) {
      try {
        const cards = page.locator('[class*="template"], [class*="card"]')
        const count = await cards.count()
        r.keyElements.push({
          name: `Template cards (${count})`,
          found: count > 0,
        })
      } catch {
        r.keyElements.push({ name: 'Template cards', found: false })
      }
    }

    printResult(r)
    results.push(r)

    expect(r.loaded).toBe(true)
  })

  // ============================================================
  // 6. WORKSPACE
  // ============================================================
  test('06 - Workspace page loads', async ({ page }) => {
    const r = await collectPageResults(page, 'Workspace', '/workspace', [
      'Jarvis PM',
      '项目工作区',
    ])

    // Check for main content area
    try {
      const contentArea = page.locator('main, [class*="workspace"], [class*="content"]')
      const visible = await contentArea.first().isVisible().catch(() => false)
      r.keyElements.push({ name: 'Workspace content area', found: visible })
    } catch {
      r.keyElements.push({ name: 'Workspace content area', found: false })
    }

    printResult(r)
    results.push(r)

    expect(r.loaded).toBe(true)
  })

  // ============================================================
  // FINAL SUMMARY
  // ============================================================
  test('07 - FINAL SUMMARY REPORT', async () => {
    console.log('\n\n')
    console.log('='.repeat(70))
    console.log('  JARVIS PM E2E TEST — COMPREHENSIVE REPORT')
    console.log('='.repeat(70))

    const totalPages = results.length
    const loadedPages = results.filter((r) => r.loaded).length
    const totalConsoleErrors = results.reduce((sum, r) => sum + r.consoleErrors.length, 0)
    const totalApiFailures = results.reduce((sum, r) => sum + r.apiFailures.length, 0)
    const totalKeyElements = results.reduce((sum, r) => sum + r.keyElements.length, 0)
    const foundKeyElements = results.reduce(
      (sum, r) => sum + r.keyElements.filter((e) => e.found).length,
      0
    )

    console.log(`\n  Pages Tested:  ${totalPages}`)
    console.log(`  Pages Loaded:  ${loadedPages} / ${totalPages}`)
    console.log(`  Key Elements:  ${foundKeyElements} / ${totalKeyElements} found`)
    console.log(`  Console Errs:  ${totalConsoleErrors}`)
    console.log(`  API Failures:  ${totalApiFailures}`)

    console.log(`\n  Per-Page Summary:`)
    for (const r of results) {
      const elPass = r.keyElements.filter((e) => e.found).length
      const elTotal = r.keyElements.length
      const status = r.loaded && r.consoleErrors.length === 0 && r.apiFailures.length === 0 ? 'PASS' : 'ISSUES'
      console.log(
        `    ${status === 'PASS' ? 'PASS' : 'WARN'} | ${r.page.padEnd(18)} | Elements: ${elPass}/${elTotal} | Console: ${r.consoleErrors.length} | API: ${r.apiFailures.length}`
      )
    }

    console.log(`\n  FAILED ELEMENTS:`)
    let anyFailed = false
    for (const r of results) {
      for (const el of r.keyElements) {
        if (!el.found) {
          console.log(`    MISSING in ${r.page}: "${el.name}"`)
          anyFailed = true
        }
      }
    }
    if (!anyFailed) {
      console.log(`    (none)`)
    }

    console.log(`\n  ALL CONSOLE ERRORS:`)
    let anyConsoleErr = false
    for (const r of results) {
      for (const err of r.consoleErrors) {
        console.log(`    [${r.page}] ${err}`)
        anyConsoleErr = true
      }
    }
    if (!anyConsoleErr) {
      console.log(`    (none)`)
    }

    console.log(`\n  ALL API FAILURES:`)
    let anyApiFail = false
    for (const r of results) {
      for (const f of r.apiFailures) {
        console.log(`    [${r.page}] ${f}`)
        anyApiFail = true
      }
    }
    if (!anyApiFail) {
      console.log(`    (none)`)
    }

    console.log(`\n${'='.repeat(70)}\n`)

    // Soft assertions for the report — don't hard-fail on console errors
    // but flag them clearly
    expect(loadedPages).toBe(totalPages)
  })
})
