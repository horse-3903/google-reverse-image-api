import asyncio
import aiofiles
from datetime import datetime
from playwright.async_api import async_playwright, Playwright

async def run():
    global playwright, chromium, browser, context, page
    playwright: Playwright = async_playwright()

    # navigate to imghp page
    chromium = playwright.chromium
    browser = await chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto("https://www.google.com/imghp?hl=en")

async def close():
    await page.close()
    await context.close()
    await browser.close()
    await playwright.stop()

async def search_url(url: str, num: int):
    # search with link
    await page.get_by_role("button", name="Search by image").click()
    url_input = page.get_by_placeholder("Paste image link")
    await url_input.hover()
    await url_input.type(url)
    
    await page.get_by_role("button", name="Search", exact=True).first.click()
    await page.get_by_text("Find image source").locator("../..").click()

    await page.wait_for_load_state("networkidle")

    while len(await page.locator(".anSuc").all()) < num:
        await page.locator(".dg5SXe").locator("button").click()

    content = await page.locator(".pFjtkf").inner_html()

    async with aiofiles.open(f"./content/content-{datetime.now().strftime('%d%m%Y-%H%M%S')}.html", "w+", encoding="utf-8") as f:
        await f.write(content)
    
    await close()

asyncio.run(run())