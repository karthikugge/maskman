import httpx
import os
from typing import Optional, Dict, Any

class FlipkartRapidAPI:
    """
    Wrapper for the real-time-flipkart-data2 RapidAPI.
    Requires an API key provided via environment variable (RAPIDAPI_KEY) or directly to methods.
    """
    
    BASE_URL = "https://real-time-flipkart-data2.p.rapidapi.com"
    HOST = "real-time-flipkart-data2.p.rapidapi.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            print("Warning: No RAPIDAPI_KEY found. API calls will fail with 401 Unauthorized.")
            
    async def get_sub_categories(self, category_id: str) -> Dict[str, Any]:
        """
        Fetch sub-categories for a given category ID (e.g., 'clo').
        """
        url = f"{self.BASE_URL}/sub-categories"
        querystring = {"categoryId": category_id}

        headers = {
            "x-rapidapi-key": self.api_key or "",
            "x-rapidapi-host": self.HOST,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            return response.json()

# Example usage:
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Replace 'YOUR_KEY_HERE' with your actual RapidAPI Key
        api = FlipkartRapidAPI(api_key="YOUR_KEY_HERE")
        try:
            print("Fetching sub-categories for 'clo'...")
            data = await api.get_sub_categories("clo")
            print("Success:", data)
        except Exception as e:
            print("Error:", e)
            
    asyncio.run(main())
