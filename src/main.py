import asyncio
import time
from playwright.async_api import async_playwright, Playwright

async def run(playwright: Playwright):
    global page 

    # navigate to imghp page
    chromium = playwright.chromium
    browser = await chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto("https://www.google.com/imghp?hl=en")

    # search url
    await search_url("https://static.wikia.nocookie.net/amogus/images/c/cb/Susremaster.png/revision/latest?cb=20210806124552")

async def search_url(url: str):
    # search with link
    await page.get_by_role("button", name="Search by image").click()
    url_input = page.get_by_placeholder("Paste image link")
    await url_input.hover()
    await url_input.type(url)
    
    await page.get_by_role("button", name="Search", exact=True).first.click()
    await page.get_by_text("Find image source").locator("../..").click()

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

asyncio.run(main())