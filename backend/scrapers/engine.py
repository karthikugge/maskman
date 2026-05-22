import httpx
import asyncio
from typing import Dict, Optional
from .base import BaseParser
from .flipkart import FlipkartParser
from .amazon import AmazonParser
from .myntra import MyntraParser
from .nykaa import NykaaParser
from .browser import BrowserEngine

class ScraperEngine:
    def __init__(self):
        self.parsers = {
            "flipkart.com": FlipkartParser(),
            "amazon.in": AmazonParser(),
            "amazon.com": AmazonParser(),
            "myntra.com": MyntraParser(),
            "nykaa.com": NykaaParser()
        }
        self.browser = BrowserEngine()

    async def scrape(self, url: str) -> Dict:
        """
        Main entry point for scraping. 
        Tries fast HTTP first, then Playwright fallback.
        """
        parser = self._get_parser(url)
        
        # 1. FAST HTTP TRY
        headers = parser.get_headers() if parser else {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    html = resp.text
                    
                    # Resolve parser from final URL if it wasn't resolved before
                    final_url = str(resp.url)
                    if not parser or not parser.can_handle(final_url):
                        parser = self._get_parser(final_url)
                        
                    if parser:
                        result = parser.parse(html)
                        if result.get("price", 0) > 0 or result.get("discounted_price", 0) > 0:
                            return result
            except Exception as e:
                print(f"Fast HTTP failed for {url}: {e}")

        # 2. HEAVY BROWSER FALLBACK
        print(f"Triggering BrowserEngine for {url}")
        html_heavy = await self.browser.get_page_content(url)
        if html_heavy:
            # Re-resolve parser in case redirect changed the domain significantly
            # Note: browser.get_page_content returns just HTML, 
            # ideally it should return the final URL too.
            # But we can try the original parser first.
            if not parser:
                # We don't have the final URL easily from BrowserEngine without modification,
                # so we just try to resolve again from the original URL if we somehow missed it.
                parser = self._get_parser(url)
                
            if parser and html_heavy:
                try:
                    return parser.parse(html_heavy)
                except Exception as e:
                    print(f"Parser failed for heavy HTML: {e}")
        
        # 3. GENERIC FALLBACK
        return {
            "title": "Unknown Product",
            "price": 0.0,
            "image_url": "",
            "description": "Scrape failed or bot detected.",
            "source": "Unknown"
        }

    def _get_parser(self, url: str) -> Optional[BaseParser]:
        for p in self.parsers.values():
            if p.can_handle(url):
                return p
        return None
