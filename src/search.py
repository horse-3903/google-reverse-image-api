from tqdm import tqdm

import asyncio

from playwright.async_api import async_playwright

url = "https://www.google.com/imghp?hl=en"

async def search_query(query: str, num: int = None):
    async with async_playwright() as playwright:
        chromium = playwright.chromium
        browser = await chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(url)

        search_bar = page.locator("textarea").first
        await search_bar.fill(query)

        search_button = page.locator("button[type=submit]")
        await search_button.click()

        await page.wait_for_load_state("load")

        search_results = page.locator(f"div[data-q='{query}'] > div > div")
        search_results = await search_results.all()

        links = []
        
        for idx, div in enumerate(tqdm(search_results, leave=False, unit="images")):
            if idx + 1 >= num:
                break

            if "Related searches" in (await div.inner_text()):
                continue

            await div.click()
            await page.wait_for_selector("div[role=dialog][data-query='among us']")

            image = page.locator("div[role=dialog][data-query='among us']").locator("a > img[aria-hidden=false]")

            try:
                links.append(await image.get_attribute("src", timeout=500))
            except:
                continue

        await browser.close()

        return links

async def main():   
    print(await search_query(query="among us", num=5))

asyncio.run(main())