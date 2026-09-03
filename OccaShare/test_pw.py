import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        # Instead of chromium, maybe we can use msedge since we are on Windows?
        # playwright uses its own browsers, which might not be installed.
        # Let's try to use the system edge.
        browser = await p.chromium.launch(channel="msedge")
        page = await browser.new_page()
        
        page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Page Error: {err.message}"))
        
        url = f"file:///{os.path.abspath('test.html').replace(chr(92), '/')}"
        print(f"Navigating to {url}")
        await page.goto(url)
        await asyncio.sleep(2)
        
        await browser.close()

asyncio.run(main())
