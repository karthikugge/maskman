import asyncio
import re
import httpx
from typing import List, Dict
from backend.scrapers.engine import ScraperEngine

class DiscoveryAgent:
    def __init__(self):
        self.engine = ScraperEngine()

    async def find_on_amazon(self, query: str) -> List[Dict]:
        """Scrapes Amazon search results for a query."""
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        try:
            # Use BrowserEngine for search pages as they are often bot-protected
            html = await self.engine.browser.get_page_content(url)
            
            # Simple regex-based link extraction from search results
            # Note: A real implementation would use a proper parser (BeautifulSoup)
            # but we'll stick to regex/string for speed and simplicity.
            
            # Find links like /dp/XXXXXXXXXX or /gp/product/XXXXXXXXXX
            products = []
            seen_dp = set()
            
            matches = re.finditer(r'href="/([^/"]+/(?:dp|gp/product)/([A-Z0-9]{10})[^"]*)"', html)
            for m in matches:
                full_path = m.group(1)
                asin = m.group(2)
                
                if asin in seen_dp: continue
                seen_dp.add(asin)
                
                # Extract title from the path if possible (amazon usually has slugs in the URL)
                title_slug = full_path.split('/')[0].replace('-', ' ')
                
                products.append({
                    "url": f"https://www.amazon.in/{full_path}",
                    "name": title_slug.title(),
                    "source": "Amazon"
                })
                
                if len(products) >= 3: break
                
            return products
        except Exception as e:
            print(f"Amazon Discovery Error: {e}")
            return []

    async def find_on_flipkart(self, query: str) -> List[Dict]:
        """Scrapes Flipkart search results for a query."""
        url = f"https://www.flipkart.com/search?q={query.replace(' ', '%20')}"
        try:
            html = await self.engine.browser.get_page_content(url)
            
            # Find product links /p/itm...
            products = []
            matches = re.finditer(r'href="/([^/"]+/p/([a-zA-Z0-9]{16})[^"]*)"', html)
            for m in matches:
                full_path = m.group(1)
                p_id = m.group(2)
                
                title_slug = full_path.split('/')[0].replace('-', ' ')
                
                products.append({
                    "url": f"https://www.flipkart.com/{full_path}",
                    "name": title_slug.title(),
                    "source": "Flipkart"
                })
                
                if len(products) >= 3: break
                
            return products
        except Exception as e:
            print(f"Flipkart Discovery Error: {e}")
            return []

    async def discover_all(self, query: str) -> List[Dict]:
        """Discovery on multiple sites in parallel."""
        tasks = [self.find_on_amazon(query), self.find_on_flipkart(query)]
        results = await asyncio.gather(*tasks)
        return [item for sublist in results for item in sublist]

discovery_agent = DiscoveryAgent()
