import asyncio
import aiofiles

from datetime import datetime

from pathlib import Path
import json

import tempfile

from tqdm import tqdm

from playwright.async_api import async_playwright, Playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

playwright: Playwright

async def run():
    global playwright, chromium, browser, context, page

    ## add print info thing
    playwright = await async_playwright().start()

    # navigate to imghp page
    chromium = playwright.chromium
    browser = await chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto("https://www.google.com/imghp?hl=en")

async def close():
    ## add print info thing
    await page.close()
    await context.close()
    await browser.close()
    await playwright.stop()

async def search_url(url: str, num: int):
    await run()

    # search with link
    ## add print info thing
    await page.get_by_role("button", name="Search by image").click()
    url_input = page.get_by_placeholder("Paste image link")
    await url_input.hover()
    await url_input.type(url)
    
    await page.get_by_role("button", name="Search", exact=True).first.click()
    await page.get_by_text("Find image source").locator("../..").click()

    await page.wait_for_load_state("networkidle")

    ## add print info thing
    while len(await page.locator(".anSuc").all()) < num:
        await page.locator(".dg5SXe").locator("button").click()

    content = await page.locator(".pFjtkf").inner_html()

    ## add print info thing
    path = Path(f"./content/content-{datetime.now().strftime('%d%m%Y-%H%M%S')}.html")
    
    async with aiofiles.open(path, "w+", encoding="utf-8") as f:
        await f.write(content)
    
    await close()

    return path

async def search_query(q: str, num: int):
    await run()

    # search with link
    ## add print info thing
    query_input = page.get_by_role("combobox", name="Search")
    await query_input.hover()
    await query_input.type(q)
    await query_input.press("Enter")

    await page.wait_for_load_state("networkidle")
    
    main_image_div = list(await page.locator(".islrc > div").all())
    extra_image_div = []
    
    # load images
    ## add print info thing
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

    if len(image_div) > num:
        image_div = image_div[:num]
    
    content = []

    ## add print info thing
    # collect high-res
    for div in tqdm(image_div, desc="Photos Scraped", unit="images"):
        if "Related searches" not in (await div.inner_text()):
            await div.click()
            await asyncio.sleep(0.3)
            # not extracting img
            content.append(await page.locator("#Sva75c").inner_html())
    
    ## add print info thing
    path = Path(f"./data/test-data-{datetime.now().strftime('%d%m%Y-%H%M%S')}.json")
    # path = Path(f"./content/test-data-{datetime.now().strftime('%d%m%Y-%H%M%S')}.html")
    
    async with aiofiles.open(path, "w+", encoding="utf-8") as f:
        await f.write(json.dumps(content, indent=4))
        # await f.write(content[0])

    await close()

# asyncio.run(search_url("https://static.wikia.nocookie.net/amogus/images/c/cb/Susremaster.png/revision/latest?cb=20210806124552", 10))
asyncio.run(search_query("dogs", 500))