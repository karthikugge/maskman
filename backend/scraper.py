import asyncio
from typing import Dict
from .scrapers.engine import ScraperEngine

# Global engine instance for reuse
_engine = ScraperEngine()

async def scrape_product_data(url: str) -> dict:
    """
    Main entry point for scraping.
    Now uses the powerful modular ScraperEngine with Playwright fallback.
    """
    try:
        result = await _engine.scrape(url)
        return result
    except Exception as e:
        print(f"Global Scraper Entry Error: {e}")
        return {
            "title": "Unknown Product",
            "price": 0.0,
            "image_url": "",
            "description": f"Error: {str(e)}"
        }
