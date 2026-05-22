"""
seed_demo_products.py — Seeds 25 demo products across multiple categories
for the visual search engine to actually have data to work with.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.supabase_lib import supabase

# First, get existing page IDs
pages_r = supabase.table("pages").select("id,name").execute()
pages = {p["name"].lower(): p["id"] for p in pages_r.data}
print(f"Existing pages: {list(pages.keys())}")

# Create pages if they don't exist
REQUIRED_PAGES = ["Mobiles", "Laptops", "Shoes", "Watches", "Home Decor", "Beauty"]
for page_name in REQUIRED_PAGES:
    if page_name.lower() not in pages:
        try:
            r = supabase.table("pages").insert({"name": page_name}).execute()
            pages[page_name.lower()] = r.data[0]["id"]
            print(f"  Created page: {page_name}")
        except Exception as e:
            print(f"  Page '{page_name}' create error: {e}")

# Refresh pages
pages_r = supabase.table("pages").select("id,name").execute()
pages = {p["name"].lower(): p["id"] for p in pages_r.data}
print(f"Pages after setup: {list(pages.keys())}")

def get_page_id(name):
    for k, v in pages.items():
        if name.lower() in k:
            return v
    return list(pages.values())[0] if pages else None

PRODUCTS = [
    # ── Electronics: Phones ──
    {"name": "Samsung Galaxy A15 5G Smartphone 128GB", "mrp": 16999, "discounted_price": 12999, "discount_pct": 24, "page": "mobiles",
     "image_url": "https://m.media-amazon.com/images/I/81NGxLv4GIL._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Apple iPhone 16 128GB Black", "mrp": 79900, "discounted_price": 74900, "discount_pct": 6, "page": "mobiles",
     "image_url": "https://m.media-amazon.com/images/I/61bK6PMWL3L._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Redmi Note 14 Pro 5G 256GB Phantom Purple", "mrp": 24999, "discounted_price": 21999, "discount_pct": 12, "page": "mobiles",
     "image_url": "https://m.media-amazon.com/images/I/71GLMJ8GDLL._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "OnePlus 13R 5G 256GB Astral Trail", "mrp": 42999, "discounted_price": 39999, "discount_pct": 7, "page": "mobiles",
     "image_url": "https://m.media-amazon.com/images/I/71s5HXKUA2L._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Realme GT 7 Pro 5G 512GB Mars Orange", "mrp": 59999, "discounted_price": 52999, "discount_pct": 12, "page": "mobiles",
     "image_url": "https://m.media-amazon.com/images/I/71DBCzRRV4L._SX679_.jpg", "url": "https://amazon.in"},

    # ── Electronics: Laptops ──
    {"name": "HP Pavilion 15 Laptop AMD Ryzen 5 16GB RAM Silver", "mrp": 64999, "discounted_price": 54990, "discount_pct": 15, "page": "laptops",
     "image_url": "https://m.media-amazon.com/images/I/71iiQcRfmVL._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Lenovo IdeaPad Slim 3 15.6 inch Intel i5 Laptop Arctic Grey", "mrp": 57990, "discounted_price": 44990, "discount_pct": 22, "page": "laptops",
     "image_url": "https://m.media-amazon.com/images/I/71jG+e7roXL._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Apple MacBook Air M3 15 inch 256GB Midnight", "mrp": 149900, "discounted_price": 134900, "discount_pct": 10, "page": "laptops",
     "image_url": "https://m.media-amazon.com/images/I/71Bwge7FELL._SX679_.jpg", "url": "https://amazon.in"},

    # ── Fashion: Shoes ──
    {"name": "Nike Air Max SC Men's Running Shoes Black White", "mrp": 7495, "discounted_price": 4497, "discount_pct": 40, "page": "shoes",
     "image_url": "https://m.media-amazon.com/images/I/71Gu+PjhYtL._UL1500_.jpg", "url": "https://amazon.in"},
    {"name": "Adidas Runfalcon 3.0 Men's Running Shoes Core Black", "mrp": 4999, "discounted_price": 2799, "discount_pct": 44, "page": "shoes",
     "image_url": "https://m.media-amazon.com/images/I/71t+E2C-a9L._UL1500_.jpg", "url": "https://amazon.in"},
    {"name": "Puma Rebound V6 Low Sneakers White Black", "mrp": 3999, "discounted_price": 2399, "discount_pct": 40, "page": "shoes",
     "image_url": "https://m.media-amazon.com/images/I/71pJPUzWFDL._UL1500_.jpg", "url": "https://amazon.in"},
    {"name": "Campus OXYFIT Men's Mesh Running Shoes Grey Orange", "mrp": 1799, "discounted_price": 899, "discount_pct": 50, "page": "shoes",
     "image_url": "https://m.media-amazon.com/images/I/71aR0VRhMjL._UL1500_.jpg", "url": "https://amazon.in"},
    {"name": "Sparx Men's Sports Shoes Black Red Lightweight", "mrp": 1299, "discounted_price": 749, "discount_pct": 42, "page": "shoes",
     "image_url": "https://m.media-amazon.com/images/I/71A9HLzDNTL._UL1500_.jpg", "url": "https://amazon.in"},
    {"name": "Asian Men's Wonder Mesh Running Shoes Navy Blue", "mrp": 999, "discounted_price": 499, "discount_pct": 50, "page": "shoes",
     "image_url": "https://m.media-amazon.com/images/I/71BI2GWtjCL._UL1500_.jpg", "url": "https://amazon.in"},

    # ── Accessories: Watches ──
    {"name": "Titan Karishma Analog Black Dial Men's Watch", "mrp": 3495, "discounted_price": 2796, "discount_pct": 20, "page": "watches",
     "image_url": "https://m.media-amazon.com/images/I/71c0n90NPAL._UL1500_.jpg", "url": "https://amazon.in"},
    {"name": "Casio Vintage A168WA-1YES Silver Digital Watch", "mrp": 3595, "discounted_price": 2876, "discount_pct": 20, "page": "watches",
     "image_url": "https://m.media-amazon.com/images/I/71UWiJNVMCL._UL1500_.jpg", "url": "https://amazon.in"},
    {"name": "Fossil Minimalist Black Leather Strap Watch Matte", "mrp": 9995, "discounted_price": 6997, "discount_pct": 30, "page": "watches",
     "image_url": "https://m.media-amazon.com/images/I/71j9rtXFPPL._UL1500_.jpg", "url": "https://amazon.in"},
    {"name": "boAt Wave Sigma Smartwatch AMOLED Matte Black", "mrp": 5999, "discounted_price": 1999, "discount_pct": 67, "page": "watches",
     "image_url": "https://m.media-amazon.com/images/I/61qLmqbYb2L._SX679_.jpg", "url": "https://amazon.in"},

    # ── Home Decor ──
    {"name": "Handmade Terracotta Ceramic Vase Matte Earthy Brown", "mrp": 1499, "discounted_price": 899, "discount_pct": 40, "page": "home decor",
     "image_url": "https://m.media-amazon.com/images/I/61gBlalVxKL._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Scandinavian Oak Wood Minimalist Desk Lamp Natural", "mrp": 3999, "discounted_price": 2499, "discount_pct": 38, "page": "home decor",
     "image_url": "https://m.media-amazon.com/images/I/61tIQHwAoVL._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Bohemian Macrame Wall Hanging Cotton Cream Boho Decor", "mrp": 999, "discounted_price": 599, "discount_pct": 40, "page": "home decor",
     "image_url": "https://m.media-amazon.com/images/I/71KMqYdclyL._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Industrial Metal Shelf Unit Black Iron Rustic Wood", "mrp": 8999, "discounted_price": 5999, "discount_pct": 33, "page": "home decor",
     "image_url": "https://m.media-amazon.com/images/I/61y4HuNwVNL._SX679_.jpg", "url": "https://amazon.in"},

    # ── Beauty ──
    {"name": "The Ordinary Niacinamide 10% + Zinc 1% Serum 30ml", "mrp": 690, "discounted_price": 590, "discount_pct": 14, "page": "beauty",
     "image_url": "https://m.media-amazon.com/images/I/61MmEJE-stL._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Cetaphil Gentle Skin Cleanser Face Wash 250ml", "mrp": 575, "discounted_price": 449, "discount_pct": 22, "page": "beauty",
     "image_url": "https://m.media-amazon.com/images/I/51hTpKSBx6L._SX679_.jpg", "url": "https://amazon.in"},
    {"name": "Neutrogena Hydro Boost Water Gel Moisturizer 50g", "mrp": 999, "discounted_price": 749, "discount_pct": 25, "page": "beauty",
     "image_url": "https://m.media-amazon.com/images/I/51sCxqJ-xkL._SX679_.jpg", "url": "https://amazon.in"},
]

# Insert products
success = 0
for p in PRODUCTS:
    page_id = get_page_id(p["page"])
    row = {
        "name": p["name"],
        "mrp": p["mrp"],
        "discounted_price": p["discounted_price"],
        "discount_pct": p["discount_pct"],
        "image_url": p["image_url"],
        "url": p["url"],
        "page_id": page_id,
    }
    try:
        supabase.table("products").insert(row).execute()
        success += 1
        print(f"  ✓ {p['name'][:50]}")
    except Exception as e:
        print(f"  ✗ {p['name'][:50]} — {e}")

print(f"\nDone: {success}/{len(PRODUCTS)} products seeded.")
