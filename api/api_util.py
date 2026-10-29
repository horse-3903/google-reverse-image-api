import argparse
import asyncio
import contextlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request

from celery import Celery
from playwright.async_api import async_playwright

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
celery = Celery("api_util", broker=REDIS_URL, backend=REDIS_URL)

CDP_ENDPOINT = os.environ.get("CDP_ENDPOINT", "launch")
CDP_PORT = int(os.environ.get("CDP_PORT", "9333"))
CHROME_PROFILE = os.environ.get("CHROME_PROFILE", os.path.join(os.path.expanduser("~"), ".google-reverse-image-profile"))
CHROME_PATH = os.environ.get("CHROME_PATH")

SEARCH_URL = "https://www.google.com/imghp?hl=en"

# Each result is embedded as [0,"<id>",["<thumb>",h,w],["<full>",h,w],...]; scroll responses escape the quotes.
RESULT_RE = re.compile(
    r'\[\d+,\\?"([\w-]+)\\?",\[\\?"(https://encrypted-tbn\d\.gstatic\.com.+?)\\?",(\d+),(\d+)\],'
    r'\[\\?"(https?://.+?)\\?",(\d+),(\d+)\]'
)
SOURCE_RE = re.compile(r'"2003":\[null,\\?"[\w-]+\\?",\\?"(https?://.+?)\\?",\\?"(.*?)\\?",')
UNICODE_ESC = re.compile(r"\\+u([0-9a-fA-F]{4})")


def unescape(s: str):
    return UNICODE_ESC.sub(lambda m: chr(int(m.group(1), 16)), s)


def extract(text: str):
    results = {}
    for m in RESULT_RE.finditer(text):
        tbnid, _, _, _, url, height, width = m.groups()
        if tbnid in results:
            continue
        result = {"url": unescape(url), "width": int(width), "height": int(height)}
        source = SOURCE_RE.search(text, m.end(), m.end() + 400)
        if source:
            result["page_url"] = unescape(source.group(1))
            result["title"] = unescape(source.group(2))
        results[tbnid] = result
    return list(results.values())


def find_chrome():
    candidates = [
        CHROME_PATH,
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"),
        shutil.which("chrome"),
    ]
    exe = next((c for c in candidates if c and os.path.exists(c)), None)
    if not exe:
        raise RuntimeError("Chrome not found, set CHROME_PATH")
    return exe


def cdp_ready(base: str):
    try:
        urllib.request.urlopen(f"{base}/json/version", timeout=1)
        return True
    except OSError:
        return False


def launch_chrome():
    base = f"http://127.0.0.1:{CDP_PORT}"
    if cdp_ready(base):
        return base

    subprocess.Popen(
        [
            find_chrome(),
            f"--remote-debugging-port={CDP_PORT}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={CHROME_PROFILE}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if cdp_ready(base):
            return base
        time.sleep(1)
    raise RuntimeError("Chrome did not expose the remote debugging port")


def ws_from_active_port():
    dirs = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"),
        os.path.expanduser("~/Library/Application Support/Google/Chrome"),
        os.path.expanduser("~/.config/google-chrome"),
    ]
    for d in dirs:
        path = os.path.join(d, "DevToolsActivePort")
        if os.path.exists(path):
            port, ws_path = open(path).read().split()[:2]
            return f"ws://127.0.0.1:{port}{ws_path}"
    raise RuntimeError("DevToolsActivePort not found, enable chrome://inspect/#remote-debugging")


class GoogleReverseSearch:
    """
    Drives a real Chrome over CDP and reads the full-size image URLs straight from Google's result data.

    endpoint: "launch" starts a dedicated Chrome profile, "auto" attaches to the main Chrome
    (chrome://inspect/#remote-debugging), or pass any http:// or ws:// CDP endpoint.
    """

    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint or CDP_ENDPOINT

    async def resolve_endpoint(self):
        if self.endpoint == "launch":
            return await asyncio.to_thread(launch_chrome)
        if self.endpoint == "auto":
            return ws_from_active_port()
        return self.endpoint

    @contextlib.asynccontextmanager
    async def session(self):
        """Yields (page, results); results fills with every result Google sends to the page."""
        endpoint = await self.resolve_endpoint()
        results = {}

        async def grab(resp):
            if "google.com/" not in resp.url or not any(k in resp.url for k in ("/search?", "/async/")):
                return
            try:
                text = await resp.text()
            except Exception:
                return
            for r in extract(text):
                results.setdefault(r["url"], r)

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(endpoint)
            context = browser.contexts[0]
            blank = [pg for pg in context.pages if pg.url == "about:blank"]
            page = blank[0] if self.endpoint == "launch" and blank else await context.new_page()
            page.on("response", lambda r: asyncio.ensure_future(grab(r)))

            try:
                yield page, results
            finally:
                others = [pg for pg in context.pages if pg != page]
                if self.endpoint == "launch" and not others:
                    with contextlib.suppress(Exception):
                        await (await browser.new_browser_cdp_session()).send("Browser.close")
                else:
                    await page.close()

    async def collect(self, page, results: dict, num: int):
        await page.wait_for_load_state("load")
        await asyncio.sleep(1)

        if "/sorry/" in page.url:
            raise RuntimeError("Google served a bot check, solve it in the Chrome window and retry")

        stalled = 0
        while (not num or len(results) < num) and stalled < 3:
            previous = len(results)
            await page.keyboard.press("End")
            for _ in range(10):
                await asyncio.sleep(0.5)
                if len(results) > previous:
                    break
            stalled = stalled + 1 if len(results) == previous else 0

        for r in extract(await page.content()):
            results.setdefault(r["url"], r)

        results = list(results.values())
        return results[:num] if num else results

    async def search_query(self, query: str, num: int = 0):
        """Text search. Returns up to num results as {url, width, height, page_url, title}; num=0 means all."""
        async with self.session() as (page, results):
            await page.goto(SEARCH_URL)
            search_bar = page.locator("textarea").first
            await search_bar.fill(query)
            await search_bar.press("Enter")
            return await self.collect(page, results, num)

    async def search_image(self, image_path: str, num: int = 0):
        """Reverse image search through Google Lens. Same result shape as search_query."""
        async with self.session() as (page, results):
            await page.goto(SEARCH_URL)
            await page.locator("[aria-label='Search by image']").first.click()
            await page.locator("input[name=encoded_image]").set_input_files(image_path)
            await page.wait_for_url(re.compile(r"google\.com/search\?.*vsrid="))
            return await self.collect(page, results, num)


@celery.task
def google_reverse_search_task(query: str, num: int):
    return asyncio.run(GoogleReverseSearch().search_query(query=query, num=num))


@celery.task
def google_reverse_image_task(image_path: str, num: int):
    try:
        return asyncio.run(GoogleReverseSearch().search_image(image_path=image_path, num=num))
    finally:
        os.remove(image_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", help="text query")
    ap.add_argument("--image", help="reverse image search with this image file instead of a text query")
    ap.add_argument("--num", type=int, default=10, help="0 for every result Google will show")
    ap.add_argument("--out", help="write results to this JSON file")
    args = ap.parse_args()
    if bool(args.query) == bool(args.image):
        ap.error("give either a query or --image")

    g = GoogleReverseSearch()
    found = asyncio.run(g.search_image(args.image, args.num) if args.image else g.search_query(args.query, args.num))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(found, f, indent=2)
    print(f"{len(found)} results")
    for r in found[:5]:
        print(f"  {r['width']}x{r['height']}  {r['url']}")
