import re
from typing import Dict
from .base import BaseParser

class FlipkartParser(BaseParser):
    def can_handle(self, url: str) -> bool:
        return "flipkart.com" in url.lower()

    def parse(self, html: str) -> dict:
        result = {
            "title": "Unknown Flipkart Product",
            "price": 0.0,             # Original/MRP
            "discounted_price": 0.0,  # Current Sale Price
            "image_url": "",
            "image_gallery": [],
            "description": "",
            "currency": "INR",
            "source": "Flipkart"
        }
        
        # 1. TITLE
        fk_t = re.search(r'<span class="B_NuCI">(.*?)</span>', html)
        if fk_t:
            result["title"] = fk_t.group(1).strip()
        else:
            og_t = re.search(r'property="og:title" content="(.*?)"', html)
            if og_t: result["title"] = og_t.group(1).strip()

        # 2. IMAGE & GALLERY
        # Primary
        fk_i = re.search(r'<img.*?(?:class="_396cs4"|class="_2r_T1I").*?src="(.*?)"', html)
        if fk_i:
            result["image_url"] = fk_i.group(1).strip()
            
        # Gallery (Flipkart thumbnails)
        # We look for high-res patterns and common image tags
        all_imgs = re.findall(r'src="(https://[^"]*?\.flixcart\.com/image/[^"]+)"', html)
        if all_imgs:
            # Upgrade to higher res if it contains /128/128/ or similar
            cleaned = []
            for img in all_imgs:
                # Replace low-res components with higher ones if found
                img = re.sub(r'/[0-9]+/[0-9]+/', '/832/832/', img)
                if img not in cleaned: cleaned.append(img)
            result["image_gallery"] = cleaned[:6]
            if not result["image_url"] and cleaned: result["image_url"] = cleaned[0]

        if not result["image_url"]:
            og_i = re.search(r'property="og:image" content="(.*?)"', html)
            if og_i: result["image_url"] = og_i.group(1).strip()

        # 3. PRICE (Strict -> Relaxed)
        # Discounted Price (Current)
        for regex in [
            r'<div class="_30jeq3 _16Jk6d">(?:₹|Rs\.?|x20B9)\s*([0-9,]+(?:\.[0-9]{2})?)</div>',
            r'<div class="(?:Nx9bqj CxhGGd|hl05eU)">(?:₹|Rs\.?|x20B9|&#8377;)\s*([0-9,]+(?:\.[0-9]{2})?)</div>',
            r'class="[^"]*?price[^"]*?".*?>(?:₹|x20B9|&#8377;)\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'(?:₹|x20B9|&#8377;)\s*([0-9,]+(?:\.[0-9]{2})?)'
        ]:
            fk_p = re.search(regex, html)
            if fk_p:
                try:
                    result["discounted_price"] = float(fk_p.group(1).replace(",", ""))
                    break
                except: pass
        
        # Original Price (MRP)
        for regex in [
            r'<div class="_3I9_1Q _1V3w9E">.*?([0-9,]+(?:\.[0-9]{2})?)</div>',
            r'<div class="y9Y9kE">.*?([0-9,]+(?:\.[0-9]{2})?)</div>',
            r'class="[^"]*?original-price[^"]*?".*?([0-9,]+(?:\.[0-9]{2})?)',
            r'MRP:[^0-9]*([0-9,]+(?:\.[0-9]{2})?)'
        ]:
            fk_orig = re.search(regex, html)
            if fk_orig:
                try:
                    val = float(fk_orig.group(1).replace(",", ""))
                    if val > result["discounted_price"]:
                        result["price"] = val
                        break
                except: pass
        
        # If no MRP found, set it to the discounted price (no discount)
        if result["price"] == 0.0:
            result["price"] = result["discounted_price"]
        
        # 4. DESCRIPTION
        og_d = re.search(r'property="og:description" content="(.*?)"', html, re.I)
        if og_d: result["description"] = og_d.group(1).strip()
        else:
            meta_d = re.search(r'name="description" content="(.*?)"', html, re.I)
            if meta_d: result["description"] = meta_d.group(1).strip()
            
        return result
