import asyncio
import random
from typing import Dict, Optional
from playwright.async_api import async_playwright

class BrowserEngine:
    def __init__(self):
        self.browser = None
        self.context = None

    async def get_page_content(self, url: str) -> Optional[str]:
        """
        Use Playwright to load a page, wait for rendering, and return HTML.
        Includes basic bot-detection avoidance.
        """
        async with async_playwright() as p:
            # Slow mo to look more human if needed
            browser = await p.chromium.launch(headless=True)
            
            # Use a mobile-like or high-end desktop viewport
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Random wait before navigation
            await asyncio.sleep(random.uniform(1, 2))
            
            try:
                # 30s timeout for heavy pages
                await page.goto(url, wait_until="load", timeout=30000)
                
                # Human-like scroll and wait
                await page.mouse.wheel(0, 800)
                await asyncio.sleep(2)
                await page.mouse.wheel(0, -400)
                await asyncio.sleep(1)
                
                content = await page.content()
                return content
            except Exception as e:
                print(f"BrowserEngine error for {url}: {e}")
                return None
            finally:
                await browser.close()
