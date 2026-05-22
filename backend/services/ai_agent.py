"""
ai_agent.py — Professional Visual-Language Product Search Engine (LLM Upgraded)

Features:
- Primary Semantic Parsing via local LLM (qwen3.5 via Ollama)
- Fallback to robust dictionary-based NLP decoding
- Clean decoupled Search Strategies for Multi-Channel discovery
"""

import requests
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from backend.supabase_lib import supabase

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3.5:latest"

# ═══════════════════════════════════════════════════════════════
#  QUERY CONTEXT AND PARSING
# ═══════════════════════════════════════════════════════════════

class ParsedQuery:
    """Structured representation of extracted search intent."""
    def __init__(self, **kwargs):
        self.category: Optional[str] = kwargs.get("category")
        self.category_keyword: str = kwargs.get("category_keyword", "")
        self.brand: Optional[str] = kwargs.get("brand")
        self.price_min: Optional[int] = kwargs.get("price_min")
        self.price_max: Optional[int] = kwargs.get("price_max")
        self.colors: List[str] = kwargs.get("colors", [])
        self.materials: List[str] = kwargs.get("materials", [])
        self.styles: List[str] = kwargs.get("styles", [])
        self.moods: List[str] = kwargs.get("moods", [])
        self.raw_keywords: str = kwargs.get("raw_keywords", "")
        self.search_phrases: List[str] = kwargs.get("search_phrases", [])
        self.decoded_summary: str = kwargs.get("decoded_summary", "Searching products")

class ConversationContext:
    """Persistent session state for accumulating filters."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.category: Optional[str] = None
        self.brand: Optional[str] = None
        self.price_min: Optional[int] = None
        self.price_max: Optional[int] = None
        self.colors: List[str] = []
        self.materials: List[str] = []
        self.styles: List[str] = []
        self.moods: List[str] = []
        self.raw_keywords: str = ""
        self.search_phrases: List[str] = []
        self.decoded_summary: str = ""

    def merge(self, pq: ParsedQuery):
        """Merge a new incoming query into the persistent context."""
        if pq.category and pq.category != self.category:
            self.reset()
            self.category = pq.category
        elif pq.category:
            self.category = pq.category

        if pq.brand: self.brand = pq.brand
        if pq.price_min is not None: self.price_min = pq.price_min
        if pq.price_max is not None: self.price_max = pq.price_max
        if pq.colors: self.colors = pq.colors
        if pq.materials: self.materials = pq.materials
        if pq.styles: self.styles = pq.styles
        if pq.moods: self.moods = pq.moods
        if pq.raw_keywords: self.raw_keywords = pq.raw_keywords
        if pq.decoded_summary: self.decoded_summary = pq.decoded_summary
        if pq.search_phrases: self.search_phrases = pq.search_phrases


# ═══════════════════════════════════════════════════════════════
#  LLM INTENT DECODER
# ═══════════════════════════════════════════════════════════════

class IntentDecoder:
    """Decodes user input using Ollama LLM with fallback to basic regex."""
    
    @staticmethod
    def parse_with_llm(message: str) -> Optional[ParsedQuery]:
        prompt = f"""
        You are an API that extracts product search intent into JSON.
        User query: "{message}"
        
        Extract the values exactly into this JSON format:
        {{
            "category": "category name (e.g. electronics, fashion) or null",
            "brand": "brand name or null",
            "price_min": integer minimum price or null,
            "price_max": integer maximum price or null,
            "colors": ["list of exact colors mentioned"],
            "materials": ["list of materials mentioned"],
            "styles": ["aesthetic or style keywords"],
            "moods": ["vibe or mood keywords"],
            "raw_keywords": "string with core product keywords removing filler words",
            "search_phrases": ["list of 3 natural google search queries based on this intent"],
            "decoded_summary": "A friendly 1-sentence summary of the search (e.g. 'Searching for a comfy sofa under 20000')"
        }}
        Return ONLY valid JSON and nothing else.
        """
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "format": "json",
                "stream": False
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = json.loads(data["response"])
                return ParsedQuery(**result)
        except Exception as e:
            print(f"[LLM DECODER] Failed or timed out: {e}")
            return None
            
    @staticmethod
    def parse_with_regex(message: str) -> ParsedQuery:
        """Primitive fallback if LLM is down."""
        msg = message.lower().strip()
        pq_dict = {"colors": [], "materials": [], "styles": [], "moods": [], "search_phrases": []}
        
        def text_to_int(val: str) -> int:
            val = val.replace(",", "").replace("₹", "").replace("rs", "").replace(".", "").strip()
            if 'k' in val: return int(float(val.replace('k', '')) * 1000)
            return int(val)

        under = re.search(r'(under|below)\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?k?)', msg)
        if under: pq_dict["price_max"] = text_to_int(under.group(2))
        
        pq_dict["raw_keywords"] = msg.split(" under ")[0].replace("find me", "").replace("i want", "").strip()
        pq_dict["decoded_summary"] = f"Searching for: {pq_dict['raw_keywords'][:40]}"
        pq_dict["search_phrases"] = [pq_dict["raw_keywords"], msg]
        
        return ParsedQuery(**pq_dict)

    @classmethod
    def parse_query(cls, message: str) -> ParsedQuery:
        result = cls.parse_with_llm(message)
        if result:
            return result
        return cls.parse_with_regex(message)

# ═══════════════════════════════════════════════════════════════
#  SEARCH ENGINE
# ═══════════════════════════════════════════════════════════════

class SearchEngine:
    @staticmethod
    def _format_products(data: List[Dict]) -> List[Dict[str, Any]]:
        return [{
            "title": p.get("name", "Unknown"),
            "price": f"₹{p.get('discounted_price'):,.0f}" if p.get('discounted_price') else "N/A",
            "discount": f"{round(p.get('discount_pct', 0))}% OFF",
            "link": f"/product.html?id={p.get('id')}",
            "deal_url": f"/product.html?id={p.get('id')}",
            "image_src": p.get("image_url", ""),
            "source": (p.get("pages") or {}).get("name", "Our Store"),
            "raw_price": p.get("discounted_price", 0),
        } for p in data]

    @staticmethod
    def channel_a_db_strict(ctx: ConversationContext) -> List[Dict]:
        try:
            q = supabase.table("products").select("*, pages(name)")
            if ctx.brand: q = q.ilike("name", f"%{ctx.brand}%")
            if ctx.raw_keywords:
                main_kw = ctx.raw_keywords.split()[0]
                if len(main_kw) > 1: q = q.ilike("name", f"%{main_kw}%")
            if ctx.price_max: q = q.lte("discounted_price", ctx.price_max)
            if ctx.price_min: q = q.gte("discounted_price", ctx.price_min)
            res = q.order("discount_pct", desc=True).limit(6).execute()
            return SearchEngine._format_products(res.data) if res.data else []
        except Exception as e:
            return []

    @staticmethod
    def channel_b_db_relaxed(ctx: ConversationContext) -> Tuple[List[Dict], str]:
        # Stage 1: Drop price
        try:
            q = supabase.table("products").select("*, pages(name)")
            if ctx.raw_keywords:
                main_kw = ctx.raw_keywords.split()[0]
                q = q.ilike("name", f"%{main_kw}%")
            res = q.order("discount_pct", desc=True).limit(6).execute()
            if res.data:
                return SearchEngine._format_products(res.data), "price_relaxed"
        except Exception: pass
        return [], "none"

    @staticmethod
    def channel_c_web(ctx: ConversationContext) -> List[Dict[str, str]]:
        all_results = []
        seen = set()
        headers = {"User-Agent": "Mozilla/5.0"}
        phrases = ctx.search_phrases[:2] if ctx.search_phrases else [ctx.raw_keywords]
        
        for phrase in phrases:
            if not phrase.strip(): continue
            try:
                full = f"{phrase} India best deals"
                if ctx.price_max: full += f" under {ctx.price_max}"
                url = f"https://duckduckgo.com/html/?q={requests.utils.quote(full)}"
                r = requests.get(url, headers=headers, timeout=5)
                links = re.findall(r'result__a" href="([^"]+)">([^<]+)</a>', r.text)
                for link_url, title in links[:3]:
                    clean = requests.utils.unquote(link_url.split("?uddg=")[-1].split("&")[0])
                    if clean not in seen:
                        seen.add(clean)
                        all_results.append({"title": title.strip(), "link": clean})
            except Exception: pass
        return all_results[:5]


# ═══════════════════════════════════════════════════════════════
#  MAIN AGENT
# ═══════════════════════════════════════════════════════════════

class ChatbotAgent:
    def __init__(self):
        self.context = ConversationContext()

    def respond(self, message: str) -> Dict[str, Any]:
        try:
            pq = IntentDecoder.parse_query(message)
            self.context.merge(pq)
            ctx = self.context

            print(f"[LLM Agent] Processed: {ctx.decoded_summary}")

            db_products = SearchEngine.channel_a_db_strict(ctx)
            mode = "strict" if db_products else "none"

            if not db_products:
                db_products, mode = SearchEngine.channel_b_db_relaxed(ctx)

            web_results = []
            if not db_products:
                web_results = SearchEngine.channel_c_web(ctx)

            text = ctx.decoded_summary
            if db_products and mode == "strict":
                text += f"\n\nFound {len(db_products)} exact matches with great discounts."
            elif db_products:
                text += f"\n\nWe couldn't find an exact match, but here are related top deals."
            elif web_results:
                text += f"\n\nNo local matches in our catalog, but I found these {len(web_results)} links online."
            else:
                text += "\n\nI couldn't find anything for that request."

            # Smart Follow-up Chips
            chips = ["Trending Deals"]
            if ctx.price_max: chips.append(f"Under ₹{ctx.price_max*2:,}")
            if not ctx.price_max: chips.append("Under ₹5,000")

            return {
                "text": text,
                "products": db_products,
                "sources": [r["link"] for r in web_results],
                "suggestions": chips[:3]
            }
        except Exception as e:
            print(f"[Agent Crash] {e}")
            return {"text": "My LLM parser ran into an issue finding things for you.", "products": [], "sources": [], "suggestions": ["Try again"]}

chatbot_agent = ChatbotAgent()
