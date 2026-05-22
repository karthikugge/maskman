import re
from .base import BaseParser

class NykaaParser(BaseParser):
    """
    Dedicated parser for Nykaa.
    Handles specialized beauty and fashion product data.
    """
    def can_handle(self, url: str) -> bool:
        return "nykaa.com" in url

    def parse(self, html: str) -> dict:
        result = {
            "title": "Unknown Nykaa Product",
            "price": 0.0,
            "discounted_price": 0.0,
            "image_url": "",
            "image_gallery": [],
            "description": "",
            "currency": "INR",
            "source": "Nykaa"
        }

        # 1. TITLE
        og_t = re.search(r'property="og:title" content="(.*?)"', html, re.I)
        if og_t: result["title"] = og_t.group(1).replace(" - Buy Online at Best Price in India | Nykaa", "").strip()

        # 2. IMAGE
        og_i = re.search(r'property="og:image" content="(.*?)"', html, re.I)
        if og_i: result["image_url"] = og_i.group(1).strip()
        
        # Try finding high-res image gallery
        gallery_matches = re.findall(r'"media":\[\{"url":"(https://.*?\.jpg)"', html)
        if not gallery_matches:
            gallery_matches = re.findall(r'(https://images-static.nykaa.com/.*?\.jpg)', html)
        if gallery_matches:
            cleaned = []
            for img in gallery_matches:
                if img not in cleaned: cleaned.append(img)
            result["image_gallery"] = cleaned[:6]

        # 3. PRICE
        # Sale Price (Discounted)
        price_meta = re.search(r'property="og:price:amount" content="(.*?)"', html, re.I)
        if price_meta:
            try: result["discounted_price"] = float(price_meta.group(1).replace(",", ""))
            except: pass
        
        if result["discounted_price"] == 0.0:
            for regex in [
                r'"offerPrice":\s*([0-9.]+)',
                r'class="css-1jcz6ot">.*?([0-9,.]+)',
                r'"price":\s*([0-9.]+)'
            ]:
                match = re.search(regex, html)
                if match:
                    try:
                        result["discounted_price"] = float(match.group(1).replace(",", ""))
                        break
                    except: pass
                    
        # Original Price (MRP)
        for regex in [
            r'"mrp":\s*([0-9.]+)',
            r'class="css-17x46n5"[^>]*>.*?([0-9,]+(?:\.[0-9]{2})?)'
        ]:
            mrp_match = re.search(regex, html)
            if mrp_match:
                try:
                    val = float(mrp_match.group(1).replace(",", ""))
                    if val > result["discounted_price"]:
                        result["price"] = val
                        break
                except: pass
                
        if result["price"] == 0.0:
            result["price"] = result["discounted_price"]

        # 4. DESCRIPTION
        og_d = re.search(r'property="og:description" content="(.*?)"', html, re.I)
        if og_d: result["description"] = og_d.group(1).strip()

        return result
