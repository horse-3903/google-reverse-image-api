import asyncio
import aiofiles

from datetime import datetime

from pathlib import Path
import json

from playwright.async_api import async_playwright, Playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

playwright: Playwright

async def run():
    global playwright, chromium, browser, context, page
    playwright = await async_playwright().start()

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
    await run()

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

    path = Path(f"./content/content-{datetime.now().strftime('%d%m%Y-%H%M%S')}.html")
    
    async with aiofiles.open(path, "w+", encoding="utf-8") as f:
        await f.write(content)
    
    await close()

    return path

async def search_query(q: str, num: int):
    await run()

    # search with link
    query_input = page.get_by_role("combobox", name="Search")
    await query_input.hover()
    await query_input.type(q)
    await query_input.press("Enter")

    await page.wait_for_load_state("networkidle")

    main_image_div = list(await page.locator(".islrc > div").all())
    extra_image_div = []
    
    while len(main_image_div + extra_image_div) - 20 < num:
        try:
            await page.get_by_text("Show more results").click(timeout=1000)
        except PlaywrightTimeoutError:
            try:
                await page.get_by_text("See more anyway").click(timeout=1000)
            except PlaywrightTimeoutError:
                if len(await page.get_by_text("Looks like you've reached the end").all()) > 2:
                    for div in await page.get_by_text("Looks like you've reached the end").all():
                        try:
                            await div.hover(timeout=1000)
                        except:
                            pass

                    extra_image_div = list(await page.locator(".islrc > .isnpr > div").all())
                    break

        await (main_image_div + extra_image_div)[-1].hover()
        extra_image_div = list(await page.locator(".islrc > .isnpr > div").all())

    image_div = main_image_div + extra_image_div

    for div in image_div:
        await div.click()


    # path = Path(f"./data/test-data-{datetime.now().strftime('%d%m%Y-%H%M%S')}.json")
    
    # async with aiofiles.open(path, "w+", encoding="utf-8") as f:
    #     await f.write(json.dumps([await i.inner_html() for i in image_div], indent=4))

    await asyncio.sleep(1000)
    await close()

# asyncio.run(search_url("https://static.wikia.nocookie.net/amogus/images/c/cb/Susremaster.png/revision/latest?cb=20210806124552", 10))
asyncio.run(search_query("dogs", 10000))