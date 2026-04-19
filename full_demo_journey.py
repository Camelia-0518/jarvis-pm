# -*- coding: utf-8 -*-
"""
Jarvis PM Full Journey Demo - Stable Version
Showcases all features using existing data
"""
import os, sys, asyncio, time
os.environ['PYTHONIOENCODING'] = 'utf-8'

from playwright.async_api import async_playwright

SCREEN_DIR = r"C:\Users\13400\jarvis_pm_demo_screenshots"
os.makedirs(SCREEN_DIR, exist_ok=True)
BASE = "http://localhost:3000"

JOURNAL = []

def out(text):
    sys.stdout.buffer.write((text + "\n").encode('utf-8'))
    sys.stdout.buffer.flush()

def log(step, detail):
    line = f"[{time.strftime('%H:%M:%S')}] {step}: {detail}"
    JOURNAL.append(line)
    out(line)

async def shot(page, name, full=False):
    path = os.path.join(SCREEN_DIR, f"journey_{name}.png")
    await page.screenshot(path=path, full_page=full)
    log("SHOT", name)

async def safe_click(page, selector, desc, timeout=10000):
    """Safely click an element with fallback"""
    try:
        loc = page.locator(selector).first
        await loc.click(timeout=timeout)
        log("CLICK", desc)
        return True
    except Exception as e:
        log("SKIP", f"{desc} - {str(e)[:60]}")
        return False

async def journey():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # ===== STEP 1: Dashboard =====
        log("STEP1", "Open Dashboard")
        await page.goto(f"{BASE}/dashboard")
        await page.wait_for_timeout(3000)
        await shot(page, "01_dashboard", full=True)
        title = await page.title()
        log("INFO", f"Page title: {title}")

        # Count projects
        proj_cards = page.locator('a[href*="/workspace?id="]')
        proj_count = await proj_cards.count()
        log("INFO", f"Projects found: {proj_count}")

        # ===== STEP 2: Open Skills Panel inline =====
        log("STEP2", "Open inline Skills Panel")
        await safe_click(page, 'button:has-text("技能面板")', "Skills panel button")
        await page.wait_for_timeout(1500)
        await shot(page, "02_skills_panel")

        # Close panel
        await safe_click(page, 'button:has-text("✕")', "Close button")
        await page.wait_for_timeout(500)

        # ===== STEP 3: Navigate to Skills Page (FIXED) =====
        log("STEP3", "Navigate to /skills page (NEW fixed route)")
        await page.goto(f"{BASE}/skills")
        await page.wait_for_timeout(3000)
        await shot(page, "03_skills_page", full=True)

        # Count skill cards
        cards = page.locator('div.cursor-pointer')
        count = await cards.count()
        log("INFO", f"Skill cards: {count}")

        # Click category filters
        for cat in ["医疗", "分析", "设计"]:
            clicked = await safe_click(page, f'button:has-text("{cat}")', f"Filter {cat}")
            if clicked:
                await page.wait_for_timeout(1000)
                await shot(page, f"04_skills_{cat}")
                # Click back to All
                await safe_click(page, 'button:has-text("全部")', "All filter")
                await page.wait_for_timeout(500)
                break  # Just demo one filter

        # Click first skill to see detail
        if count > 0:
            await cards.first.click()
            await page.wait_for_timeout(1000)
            await shot(page, "05_skill_detail")

        # ===== STEP 4: Templates Page =====
        log("STEP4", "Navigate to Templates")
        await page.goto(f"{BASE}/templates")
        await page.wait_for_timeout(2500)
        await shot(page, "06_templates", full=True)

        tmpl_btns = page.locator('button:has-text("使用此模板")')
        tmpl_count = await tmpl_btns.count()
        log("INFO", f"Templates: {tmpl_count}")

        # ===== STEP 5: Workflow Page =====
        log("STEP5", "Navigate to Workflow")
        await page.goto(f"{BASE}/workflow")
        await page.wait_for_timeout(2500)
        await shot(page, "07_workflow", full=True)

        # ===== STEP 6: Battle Page =====
        log("STEP6", "Navigate to Battle/Sprint mode")
        await page.goto(f"{BASE}/battle")
        await page.wait_for_timeout(2500)
        await shot(page, "08_battle", full=True)

        # ===== STEP 7: Enter existing project Workspace =====
        log("STEP7", "Go to Dashboard and enter existing project")
        await page.goto(f"{BASE}/dashboard")
        await page.wait_for_timeout(2500)

        proj_links = page.locator('a[href*="/workspace?id="]')
        if await proj_links.count() > 0:
            await proj_links.first.click()
            await page.wait_for_timeout(3500)
            await shot(page, "09_workspace", full=True)

            # Check PRD list
            prd_links = page.locator('a[href*="/prd/"]')
            prd_count = await prd_links.count()
            log("INFO", f"PRDs in project: {prd_count}")

            # ===== STEP 8: Open existing PRD Editor =====
            if prd_count > 0:
                log("STEP8", "Open existing PRD for editing")
                await prd_links.first.click()
                await page.wait_for_timeout(3000)
                await shot(page, "10_prd_editor", full=True)

                # Check content
                editor = page.locator('textarea').first
                if await editor.is_visible():
                    content = await editor.input_value()
                    log("INFO", f"PRD content: {len(content)} chars")

                # Quick actions
                for action_text in ["生成评审议程", "检查风险点", "合规检查"]:
                    btn = page.locator(f'button:has-text("{action_text}")')
                    if await btn.count() > 0:
                        log("ACTION", f"Click quick action: {action_text}")
                        await btn.first.click()
                        await page.wait_for_timeout(18000)
                        await shot(page, f"11_prd_{action_text[:4]}", full=True)
                        break  # Just do one

                # Save
                save = page.locator('button:has-text("保存")').first
                if await save.count() > 0:
                    await save.click()
                    await page.wait_for_timeout(1500)
                    log("RESULT", "PRD saved")

        # ===== STEP 9: API Docs =====
        log("STEP9", "Check API docs")
        await page.goto(f"{BASE}/api/docs" if False else "http://127.0.0.1:8000/docs")
        await page.wait_for_timeout(2500)
        await shot(page, "12_api_docs", full=True)

        # ===== STEP 10: Final Dashboard =====
        log("STEP10", "Final Dashboard view")
        await page.goto(f"{BASE}/dashboard")
        await page.wait_for_timeout(2500)
        await shot(page, "13_final_dashboard", full=True)

        log("COMPLETE", "Demo finished successfully")
        await browser.close()

async def main():
    out("")
    out("=" * 70)
    out("Jarvis PM Full Feature Demo")
    out("=" * 70)
    out("")
    out("Demonstrating: Dashboard, Skills, Templates, Workflow,")
    out("                Battle, Workspace, PRD Editor, API Docs")
    out("")

    try:
        await journey()
    except Exception as e:
        log("ERROR", str(e))
        import traceback
        traceback.print_exc()

    out("")
    out("=" * 70)
    out("Operation Log")
    out("=" * 70)
    for line in JOURNAL:
        out(line)
    out("")
    out(f"Screenshots: {SCREEN_DIR}")
    out("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
