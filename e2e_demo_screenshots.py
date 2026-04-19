# -*- coding: utf-8 -*-
"""
Jarvis PM E2E Fix Demo - Browser Screenshots
"""
import os, sys, asyncio
os.environ['PYTHONIOENCODING'] = 'utf-8'

from playwright.async_api import async_playwright

SCREEN_DIR = r"C:\Users\13400\jarvis_pm_demo_screenshots"
os.makedirs(SCREEN_DIR, exist_ok=True)
BASE = "http://localhost:3000"
API = "http://127.0.0.1:8002"

async def shot(page, name, full=False):
    path = os.path.join(SCREEN_DIR, f"{name}.png")
    await page.screenshot(path=path, full_page=full)
    sys.stdout.buffer.write(f"  [OK] Saved: {name}.png\n".encode('utf-8'))

async def run_demo():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # 1. Dashboard
        sys.stdout.buffer.write(b"\n[1/7] Dashboard\n")
        await page.goto(f"{BASE}/dashboard")
        await page.wait_for_timeout(3000)
        await shot(page, "01_dashboard", full=True)

        # 1b. Skills panel
        btn = await page.query_selector('text=技能面板')
        if btn:
            await btn.click()
            await page.wait_for_timeout(1500)
            await shot(page, "01b_dashboard_skills_panel")

        # 2. Skills page (NEW - fixed)
        sys.stdout.buffer.write(b"\n[2/7] Skills Page (NEW fixed page)\n")
        await page.goto(f"{BASE}/skills")
        await page.wait_for_timeout(3000)
        await shot(page, "02_skills_page", full=True)

        # Filter by category
        cat = await page.query_selector('button:has-text("医疗")')
        if cat:
            await cat.click()
            await page.wait_for_timeout(1500)
            await shot(page, "02b_skills_filtered")

        # Search
        inp = await page.query_selector('input[placeholder="搜索技能..."]')
        if inp:
            await inp.fill("PRD")
            await page.wait_for_timeout(1500)
            await shot(page, "02c_skills_search")

        # Click skill card
        card = await page.query_selector('div.cursor-pointer')
        if card:
            await card.click()
            await page.wait_for_timeout(1500)
            await shot(page, "02d_skill_detail")

        # 3. Workspace - create project then show PRD list (FIXED)
        sys.stdout.buffer.write(b"\n[3/7] Workspace - Create Project + PRD List (FIXED)\n")
        await page.goto(f"{BASE}/dashboard")
        await page.wait_for_timeout(2000)

        new_proj = await page.query_selector('text=新建项目')
        if new_proj:
            await new_proj.click()
            await page.wait_for_timeout(1000)
            name_inp = await page.query_selector('input[placeholder="输入项目名称"]')
            if name_inp:
                await name_inp.fill("E2E Demo Project")
            desc_inp = await page.query_selector('textarea[placeholder="输入项目描述"]')
            if desc_inp:
                await desc_inp.fill("Demo project for E2E testing")
            submit = await page.query_selector('form button[type="submit"]')
            if submit:
                await submit.click()
                await page.wait_for_timeout(3000)
                await shot(page, "03_workspace_created", full=True)

        # 4. Create PRD
        sys.stdout.buffer.write(b"\n[4/7] PRD Editor - Create + Load (FIXED)\n")
        new_prd = await page.query_selector('text=新建 PRD')
        if new_prd:
            await new_prd.click()
            await page.wait_for_timeout(1000)
            title_inp = await page.query_selector('input[placeholder="输入 PRD 标题"]')
            if title_inp:
                await title_inp.fill("Slide Lending Platform PRD")
            prd_submit = await page.query_selector('form button[type="submit"]')
            if prd_submit:
                await prd_submit.click()
                await page.wait_for_timeout(8000)  # AI generation
                await shot(page, "04_prd_editor_loaded", full=True)

        # 5. Quick actions
        sys.stdout.buffer.write(b"\n[5/7] PRD Editor - Quick Actions\n")
        qa = await page.query_selector('text=生成评审议程')
        if qa:
            await qa.click()
            await page.wait_for_timeout(5000)
            await shot(page, "05_prd_quick_action", full=True)

        # 6. Templates
        sys.stdout.buffer.write(b"\n[6/7] Templates Page\n")
        await page.goto(f"{BASE}/templates")
        await page.wait_for_timeout(2000)
        await shot(page, "06_templates", full=True)

        # 7. Workflow
        sys.stdout.buffer.write(b"\n[7/7] Workflow Page\n")
        await page.goto(f"{BASE}/workflow")
        await page.wait_for_timeout(2000)
        await shot(page, "07_workflow", full=True)

        await browser.close()

    # Summary
    sys.stdout.buffer.write(b"\n========================================\n")
    sys.stdout.buffer.write(f"Demo complete! Screenshots in:\n  {SCREEN_DIR}\n".encode('utf-8'))
    sys.stdout.buffer.write(b"========================================\n")
    for f in sorted(os.listdir(SCREEN_DIR)):
        if f.endswith('.png'):
            sz = os.path.getsize(os.path.join(SCREEN_DIR, f)) / 1024
            sys.stdout.buffer.write(f"  {f} ({sz:.0f} KB)\n".encode('utf-8'))

if __name__ == "__main__":
    asyncio.run(run_demo())
