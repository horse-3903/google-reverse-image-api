import argparse
import asyncio
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
UNICODE_ESC = re.compile(r"\\+u([0-9a-fA-F]{4})")


def extract(text: str):
    results = {}
    for tbnid, _, _, _, url, height, width in RESULT_RE.findall(text):
        url = UNICODE_ESC.sub(lambda m: chr(int(m.group(1), 16)), url)
        results.setdefault(tbnid, {"url": url, "width": int(width), "height": int(height)})
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

    async def search_query(self, query: str, num: int = 0):
        """Returns up to num results as {url, width, height}; num=0 scrolls until Google has no more."""
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
            reuse = self.endpoint == "launch" and bool(blank)
            page = blank[0] if reuse else await context.new_page()
            page.on("response", lambda r: asyncio.ensure_future(grab(r)))

            try:
                await page.goto(SEARCH_URL)
                search_bar = page.locator("textarea").first
                await search_bar.fill(query)
                await search_bar.press("Enter")
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
            finally:
                if not reuse:
                    await page.close()

        results = list(results.values())
        return results[:num] if num else results


@celery.task
def google_reverse_search_task(query: str, num: int):
    return asyncio.run(GoogleReverseSearch().search_query(query=query, num=num))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--num", type=int, default=10, help="0 for every result Google will show")
    ap.add_argument("--out", help="write results to this JSON file")
    args = ap.parse_args()

    found = asyncio.run(GoogleReverseSearch().search_query(args.query, args.num))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(found, f, indent=2)
    print(f"{len(found)} results")
    for r in found[:5]:
        print(f"  {r['width']}x{r['height']}  {r['url']}")
