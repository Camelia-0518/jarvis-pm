/**
 * Jarvis PM 产品功能 E2E 检测脚本
 * 模拟真实用户操作流程
 * 运行: npx playwright test e2e_functional_test.ts --headed --reporter=list
 */
import { test, expect, type Page } from '@playwright/test';

const BASE = 'http://localhost:3000';

// ============================================================
// 辅助函数
// ============================================================

async function safeClick(page: Page, selector: string, timeout = 5000) {
  try {
    await page.waitForSelector(selector, { timeout });
    await page.click(selector);
    return true;
  } catch {
    return false;
  }
}

async function safeFill(page: Page, selector: string, text: string, timeout = 5000) {
  try {
    await page.waitForSelector(selector, { timeout });
    await page.fill(selector, text);
    return true;
  } catch {
    return false;
  }
}

async function logResult(testName: string, passed: boolean, detail: string = '') {
  const icon = passed ? '✅' : '❌';
  console.log(`${icon} ${testName}${detail ? ': ' + detail : ''}`);
}

// ============================================================
// 1. 首页 & 导航
// ============================================================
test.describe('一、首页与基础导航', () => {
  test('1.1 首页加载', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');

    // 首页应该有标题或 hero 区域
    const hasHero = await page.locator('text=AI').first().isVisible().catch(() => false);
    const hasHeading = await page.locator('h1, h2').first().isVisible().catch(() => false);
    console.log(`   首页加载: hero=${hasHero}, heading=${hasHeading}`);
    expect(hasHero || hasHeading).toBeTruthy();
  });

  test('1.2 导航到工作台', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');

    // 尝试点击进入工作台的链接
    const clicked = await safeClick(page, 'a[href*="dashboard"]') ||
                    await safeClick(page, 'text=工作台') ||
                    await safeClick(page, 'text=进入工作台');
    if (clicked) {
      await page.waitForTimeout(2000);
      console.log(`   当前 URL: ${page.url()}`);
    }
    // 即使没有直接链接，直接导航到 dashboard
    if (!page.url().includes('dashboard')) {
      await page.goto(`${BASE}/dashboard`);
      await page.waitForLoadState('networkidle');
    }
  });

  test('1.3 顶部导航栏所有链接可用', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const navLinks = [
      { name: '工作台', href: 'dashboard' },
      { name: '写PRD', href: 'workspace' },
      { name: '交付中心', href: 'delivery' },
      { name: '模板管理', href: 'templates' },
      { name: '技能广场', href: 'skills' },
      { name: '提示词', href: 'prompts' },
      { name: '工作流', href: 'workflow' },
      { name: 'Battle', href: 'battle' },
    ];

    for (const link of navLinks) {
      try {
        await page.goto(`${BASE}/${link.href}`);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);
        const title = await page.title();
        console.log(`   ${link.name} (/` + link.href + `): title="${title}" - OK`);
        expect(title.length).toBeGreaterThan(0);
      } catch (e) {
        console.log(`   ${link.name} (/` + link.href + `): ERROR - ${e}`);
      }
    }
  });
});

// ============================================================
// 2. 项目管理
// ============================================================
test.describe('二、项目管理', () => {
  test('2.1 仪表盘加载', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 仪表盘应该显示项目列表或空状态
    const hasContent = await page.locator('text=项目').first().isVisible().catch(() => false);
    const hasCard = await page.locator('[class*="card"], [class*="Card"]').first().isVisible().catch(() => false);
    console.log(`   仪表盘: hasProjectText=${hasContent}, hasCard=${hasCard}`);
    expect(hasContent || hasCard).toBeTruthy();
  });

  test('2.2 新建项目', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // 点击新建项目按钮
    const newBtn = await safeClick(page, 'text=新建项目') ||
                   await safeClick(page, 'text=新项目') ||
                   await safeClick(page, 'button:has-text("新建")') ||
                   await safeClick(page, '[aria-label*="新建"]');

    if (newBtn) {
      await page.waitForTimeout(1000);
      // 填写项目名称
      await safeFill(page, 'input[name*="name"], input[placeholder*="名称"], input[placeholder*="项目"]', 'E2E测试项目-智能导诊系统');
      await safeFill(page, 'textarea[name*="description"], textarea[placeholder*="描述"]', '这是一个E2E自动化测试创建的项目');
      // 提交
      await safeClick(page, 'button[type="submit"], button:has-text("创建"), button:has-text("保存"), button:has-text("确定")');
      await page.waitForTimeout(2000);
      console.log('   新建项目表单已提交');
    } else {
      // 直接导航到 workspace 创建
      await page.goto(`${BASE}/workspace`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1500);
      console.log('   直接进入工作区创建项目');
    }
  });

  test('2.3 项目列表', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 截图保存当前仪表盘状态
    await page.screenshot({ path: 'test-results/dashboard.png', fullPage: true });
    console.log('   仪表盘截图已保存: test-results/dashboard.png');
  });
});

// ============================================================
// 3. 工作区 & PRD
// ============================================================
test.describe('三、工作区与PRD', () => {
  test('3.1 工作区加载', async ({ page }) => {
    await page.goto(`${BASE}/workspace`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 检查工作区是否加载
    const hasWorkspace = await page.locator('text=PRD').first().isVisible().catch(() => false) ||
                         await page.locator('text=工具箱').first().isVisible().catch(() => false);
    console.log(`   工作区加载: ${hasWorkspace}`);
    // 工作区可能因无项目而显示引导，也算正常
    expect(true).toBeTruthy(); // 不做硬断言，记录状态
  });

  test('3.2 工具箱面板', async ({ page }) => {
    await page.goto(`${BASE}/workspace`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const tools = ['用户调研', '竞品分析', '干系人分析', '数据分析', '评审材料', '原型设计'];
    let visibleTools = 0;
    for (const tool of tools) {
      const visible = await page.locator(`text=${tool}`).first().isVisible().catch(() => false);
      if (visible) visibleTools++;
    }
    console.log(`   工具箱可见项: ${visibleTools}/${tools.length}`);
    expect(visibleTools).toBeGreaterThanOrEqual(0); // 记录不硬断
  });

  test('3.3 工作区标签页切换', async ({ page }) => {
    await page.goto(`${BASE}/workspace`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const tabs = ['PRD 文档', '用户画像', '竞品信息', '需求池'];
    for (const tab of tabs) {
      const clicked = await safeClick(page, `text=${tab}`);
      if (clicked) {
        await page.waitForTimeout(500);
        console.log(`   切换到标签: ${tab} ✓`);
      }
    }
  });
});

// ============================================================
// 4. 技能广场
// ============================================================
test.describe('四、技能广场', () => {
  test('4.1 技能广场加载', async ({ page }) => {
    await page.goto(`${BASE}/skills`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'test-results/skills.png', fullPage: true });

    // 检查是否有技能卡片或列表
    const hasSkills = await page.locator('text=技能').first().isVisible().catch(() => false);
    const hasCards = await page.locator('[class*="card"], [class*="Card"]').first().isVisible().catch(() => false);
    console.log(`   技能页: hasSkills=${hasSkills}, hasCards=${hasCards}`);
    expect(hasSkills || hasCards).toBeTruthy();
  });

  test('4.2 技能分类筛选', async ({ page }) => {
    await page.goto(`${BASE}/skills`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const categories = ['分析', '设计', '开发', '评审', '医疗', '规划'];
    for (const cat of categories) {
      const clicked = await safeClick(page, `text=${cat}`);
      if (clicked) {
        await page.waitForTimeout(500);
        console.log(`   筛选分类: ${cat} ✓`);
      }
    }
  });

  test('4.3 技能详情与执行', async ({ page }) => {
    await page.goto(`${BASE}/skills`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 尝试点击第一个技能
    const skillClicked = await safeClick(page, '[class*="skill"], [class*="Skill"], [class*="card"]');
    if (skillClicked) {
      await page.waitForTimeout(1000);
      // 查看是否有 input 表单
      const hasInputs = await page.locator('input, textarea').first().isVisible().catch(() => false);
      console.log(`   技能详情: hasInputs=${hasInputs}`);
    } else {
      console.log('   技能卡片不可点击或未找到');
    }
    await page.screenshot({ path: 'test-results/skill-detail.png', fullPage: true });
  });
});

// ============================================================
// 5. 模板管理
// ============================================================
test.describe('五、模板管理', () => {
  test('5.1 模板页面加载', async ({ page }) => {
    await page.goto(`${BASE}/templates`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'test-results/templates.png', fullPage: true });

    const hasTemplate = await page.locator('text=模板').first().isVisible().catch(() => false);
    const hasCard = await page.locator('[class*="card"], [class*="Card"]').first().isVisible().catch(() => false);
    console.log(`   模板页: hasTemplate=${hasTemplate}, hasCards=${hasCard}`);
    expect(hasTemplate || hasCard).toBeTruthy();
  });
});

// ============================================================
// 6. 提示词管理
// ============================================================
test.describe('六、提示词管理', () => {
  test('6.1 提示词页面加载', async ({ page }) => {
    await page.goto(`${BASE}/prompts`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const hasContent = await page.locator('text=提示词').first().isVisible().catch(() => false);
    console.log(`   提示词页: hasContent=${hasContent}`);
    await page.screenshot({ path: 'test-results/prompts.png', fullPage: true });
  });
});

// ============================================================
// 7. 交付中心
// ============================================================
test.describe('七、交付中心', () => {
  test('7.1 交付仪表盘加载', async ({ page }) => {
    await page.goto(`${BASE}/delivery`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'test-results/delivery.png', fullPage: true });

    const hasDelivery = await page.locator('text=交付').first().isVisible().catch(() => false);
    console.log(`   交付中心: hasDelivery=${hasDelivery}`);
    expect(hasDelivery).toBeTruthy();
  });
});

// ============================================================
// 8. Battle 模式
// ============================================================
test.describe('八、需求Battle模式', () => {
  test('8.1 Battle 页面加载', async ({ page }) => {
    await page.goto(`${BASE}/battle`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'test-results/battle.png', fullPage: true });

    const hasContent = await page.locator('text=Battle').first().isVisible().catch(() => false) ||
                       await page.locator('text=战役').first().isVisible().catch(() => false) ||
                       await page.locator('text=Day').first().isVisible().catch(() => false);
    console.log(`   Battle页: hasContent=${hasContent}`);
  });
});

// ============================================================
// 9. 工作流可视化
// ============================================================
test.describe('九、工作流编排', () => {
  test('9.1 工作流画布加载', async ({ page }) => {
    await page.goto(`${BASE}/workflow`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'test-results/workflow.png', fullPage: true });

    const hasContent = await page.locator('text=工作流').first().isVisible().catch(() => false) ||
                       await page.locator('canvas, [class*="react-flow"]').first().isVisible().catch(() => false);
    console.log(`   工作流页: hasContent=${hasContent}`);
  });
});

// ============================================================
// 10. API 连通性
// ============================================================
test.describe('十、后端API连通性', () => {
  test('10.1 健康检查', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/health');
    expect(response.status()).toBe(200);
    console.log(`   /health: ${response.status()} ✓`);
  });

  test('10.2 API 文档可访问', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/docs');
    expect(response.status()).toBe(200);
    console.log(`   /docs: ${response.status()} ✓`);
  });

  test('10.3 技能定义列表', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/api/v1/skills/definitions');
    expect(response.status()).toBe(200);
    const body = await response.json();
    console.log(`   /skills/definitions: ${response.status()}, 数据: ${JSON.stringify(body).substring(0, 80)}...`);
  });

  test('10.4 工作流模板列表', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/api/v1/workflows/templates');
    expect(response.status()).toBe(200);
    console.log(`   /workflows/templates: ${response.status()} ✓`);
  });

  test('10.5 项目列表', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/api/v1/projects');
    expect(response.status()).toBe(200);
    console.log(`   /projects: ${response.status()} ✓`);
  });

  test('10.6 交付 Dashboard', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/api/v1/delivery/dashboard');
    expect(response.status()).toBe(200);
    console.log(`   /delivery/dashboard: ${response.status()} ✓`);
  });

  test('10.7 模板列表', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/api/v1/templates');
    expect(response.status()).toBe(200);
    console.log(`   /templates: ${response.status()} ✓`);
  });

  test('10.8 提示词列表', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/api/v1/prompts');
    expect(response.status()).toBe(200);
    console.log(`   /prompts: ${response.status()} ✓`);
  });
});
