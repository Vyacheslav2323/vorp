import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


def log_path() -> Path:
    return Path(__file__).with_name("scrape_log.jsonl")


def out_dir() -> Path:
    return Path(__file__).with_name("ridi_images")


async def wait(ms: int) -> None:
    await asyncio.sleep(ms / 1000)


def image_path(i: int) -> Path:
    directory = out_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"page_{i:04d}.png"


def write_log(entry: dict) -> None:
    entry["ts"] = datetime.utcnow().isoformat() + "Z"
    with log_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def select_imgs(page) -> list:
    selector = "div.simplebar-content img[data-index]"
    return await page.query_selector_all(selector)


async def scroll_to_bottom(page) -> None:
    last_height = 0
    stable = 0
    while True:
        await page.mouse.wheel(0, 2000)
        await wait(300)
        h = await page.evaluate("document.scrollingElement.scrollHeight")
        if h == last_height:
            stable += 1
        else:
            stable = 0
            last_height = h
        if stable >= 5:
            break


async def ensure_in_view(handle) -> None:
    await handle.scroll_into_view_if_needed()


async def screenshot_element(item: tuple) -> str:
    handle, idx = item
    path = image_path(idx)
    await handle.screenshot(type="png", path=str(path))
    return str(path)


def headless_flag() -> bool:
    v = os.environ.get("HEADFUL", "0").strip()
    return not (v == "1" or v.lower() == "true")


async def run(url: str) -> int:
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless_flag())
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await wait(800)
            try:
                await page.click("button:has-text('로그인')", timeout=2000)
            except Exception:
                pass
            await scroll_to_bottom(page)
            write_log({"event": "strategy", "type": "element_screenshot"})
            imgs = await select_imgs(page)
            saved = 0
            for idx, h in enumerate(imgs):
                try:
                    await ensure_in_view(h)
                    path = await screenshot_element((h, idx))
                    write_log({"event": "saved_screenshot", "index": idx, "path": path})
                    saved += 1
                except Exception as e:
                    write_log({"event": "error_screenshot", "index": idx, "error": str(e)})
            await browser.close()
            write_log({"event": "done", "count": saved})
            return saved
    except Exception as e:
        write_log({"event": "fatal", "error": str(e)})
        return 0


def main() -> None:
    url = None
    if len(sys.argv) == 2:
        url = sys.argv[1]
    if not url:
        url = "https://ridibooks.com/books/4745000427/view"
    count = asyncio.run(run(url))
    print(count)


if __name__ == "__main__":
    main()


