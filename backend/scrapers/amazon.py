import re
from typing import Dict
from .base import BaseParser

class AmazonParser(BaseParser):
    def can_handle(self, url: str) -> bool:
        u = url.lower()
        return "amazon.in" in u or "amazon.com" in u or "amzn.in" in u or "amzn.to" in u

    def parse(self, html: str) -> dict:
        result = {
            "title": "Unknown Amazon Product",
            "price": 0.0,             # Original/MRP
            "discounted_price": 0.0,  # Current Sale Price
            "image_url": "",
            "image_gallery": [],
            "description": "",
            "currency": "INR",
            "source": "Amazon"
        }
        
        # 1. TITLE
        og_t = re.search(r'property="og:title" content="(.*?)"', html)
        if og_t:
            result["title"] = og_t.group(1).strip()
        else:
            title_match = re.search(r'<span id="productTitle".*?>(.*?)</span>', html, re.DOTALL)
            if title_match: result["title"] = title_match.group(1).strip()

        # 2. IMAGE & GALLERY
        # Primary Image
        og_i = re.search(r'property="og:image" content="(.*?)"', html)
        if og_i: 
            result["image_url"] = og_i.group(1).strip()
        
        # Gallery (Amazon specific JSON block)
        # Search for all high-res image patterns in the HTML
        all_imgs = re.findall(r'"hiRes":"(https://m\.media-amazon\.com/images/I/.*?\.jpg)"', html)
        if not all_imgs:
            all_imgs = re.findall(r'"large":"(https://m\.media-amazon\.com/images/I/.*?\.jpg)"', html)
            
        if all_imgs:
            # Clean and unique
            result["image_gallery"] = list(dict.fromkeys(all_imgs))[:6]
            if not result["image_url"]: result["image_url"] = result["image_gallery"][0]
        
        if not result["image_url"]:
            og_i = re.search(r'property="og:image" content="(.*?)"', html)
            if og_i: result["image_url"] = og_i.group(1).strip()

        # 3. PRICE
        # Discounted Price (Current)
        for regex in [
            r'<span class="a-price-whole">([0-9,]+(?:\.[0-9]{2})?)</span>',
            r'<span class="a-offscreen">(?:₹|Rs\.?|x20B9|&#8377;)\s*([0-9,]+(?:\.[0-9]{2})?)</span>',
            r'apexPriceToPay.*?>(?:₹|x20B9|&#8377;)\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'(?:₹|x20B9|&#8377;)\s*([0-9,]+(?:\.[0-9]{2})?)'
        ]:
            amz_p = re.search(regex, html)
            if amz_p:
                try:
                    result["discounted_price"] = float(amz_p.group(1).replace(",", ""))
                    break
                except: pass

        # Original Price (MRP)
        for regex in [
            r'basisPrice.*?([0-9,]+(?:\.[0-9]{2})?)',
            r'M\.R\.P\.:.*?([0-9,]+(?:\.[0-9]{2})?)',
            r'<span class="a-price a-text-price".*?><span class="a-offscreen">.*?([0-9,]+(?:\.[0-9]{2})?)</span>',
            r'<span class="a-text-strike">.*?([0-9,]+(?:\.[0-9]{2})?)</span>',
            r'data-a-strike="true".*?([0-9,]+(?:\.[0-9]{2})?)'
        ]:
            amz_orig = re.search(regex, html)
            if amz_orig:
                try:
                    val = float(amz_orig.group(1).replace(",", ""))
                    # Sanity check: MRP should be higher than sale price
                    if val > result["discounted_price"]:
                        result["price"] = val
                        break
                except: pass
        
        if result["price"] == 0.0:
            result["price"] = result["discounted_price"]

        # 4. DESCRIPTION
        og_d = re.search(r'property="og:description" content="(.*?)"', html, re.I)
        if og_d: result["description"] = og_d.group(1).strip()
        else:
            meta_d = re.search(r'name="description" content="(.*?)"', html, re.I)
            if meta_d: result["description"] = meta_d.group(1).strip()
            
        return result
