import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # We catch console errors
        page.on("console", lambda msg: print(f"Console: {msg.text}") if msg.type == 'error' else None)
        page.on("pageerror", lambda err: print(f"Error: {err.message}"))
        
        with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
            js = f.read()
            
        print("Evaluating calendar.js...")
        try:
            await page.evaluate(js)
            print("Successfully evaluated without syntax errors.")
        except Exception as e:
            print(f"Exception during evaluation:\n{e}")
            
        await browser.close()

asyncio.run(main())
