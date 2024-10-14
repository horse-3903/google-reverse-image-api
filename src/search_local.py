import subprocess

import asyncio
from tqdm import tqdm

from local_util import *

from playwright.async_api import async_playwright

class GoogleReverseSearch:
    def __init__(self, debug: bool = False, trace_file: bool = None):
        self.debug = debug
        
        if debug and trace_file:
            self.trace_file = trace_file
        elif debug and not trace_file:
            self.trace_file = "trace.zip"
        
        self.active = False
        self.url = "https://www.google.com/imghp?hl=en"

    async def __start__(self):
        self.active = True
        
        with SendMessage("Opening Playwright Instances..."):
            self.playwright = await async_playwright().start()
            self.chromium = self.playwright.chromium
            self.browser = await self.chromium.launch(headless=(not self.debug))
            self.context = await self.browser.new_context()
            
            if self.debug:
                await self.context.tracing.start(screenshots=True, snapshots=True)
            
            self.page = await self.context.new_page()
        
            await self.page.goto(self.url)

    async def __end__(self):
        assert self.active
        
        self.active = False

        await self.context.tracing.stop(path=self.trace_file)
        await self.page.close()
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

        subprocess.run(["playwright", "show-trace", self.trace_file])

    async def search_query(self, query: str, num: int = None):
        await self.__start__()

        with SendMessage(f"Searching '{query}'..."):
            search_bar = self.page.locator("textarea").first
            await search_bar.fill(query)

            search_button = self.page.locator("button[type=submit]")
            await search_button.click()

            await self.page.wait_for_load_state("load")

        search_results = self.page.locator(f"div[data-q='{query}'] > div > div")
        search_results = await search_results.all()

        filtered_search_results = []

        for div in search_results:
            if "Related searches" not in (await div.inner_text()):
                filtered_search_results.append(div)

        search_results = filtered_search_results

        while len(search_results) < num:
            with SendMessage("Scrolling..."):
                await self.page.keyboard.press("End")
                await asyncio.sleep(3)

                search_results = self.page.locator(f"div[data-q='{query}'] > div > div")
                search_results = await search_results.all()

                # async filter where 😭
                filtered_search_results = []

                for div in search_results:
                    if "Related searches" not in (await div.inner_text()):
                        filtered_search_results.append(div)

                search_results = filtered_search_results

        links = []

        search_results = [*search_results][:num]
        
        for idx, div in enumerate(tqdm(search_results, leave=False, unit="image")):
            if idx + 1 >= num:
                break

            try:
                await div.click()
                await self.page.wait_for_selector(f"div[role=dialog][data-query='{query}']")

                image = self.page.locator(f"div[role=dialog][data-query='{query}']").locator("a > img[aria-hidden=false]")
                links.append(await image.get_attribute("src", timeout=500))
            except:
                continue

        await self.__end__()

        return links

async def main():   
    g = GoogleReverseSearch(debug=True)

    print(await g.search_query(query="among us", num=10))

asyncio.run(main())