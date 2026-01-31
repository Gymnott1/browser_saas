from .base import BaseHandler
from bs4 import BeautifulSoup

class GenericHandler(BaseHandler):
    async def get_actions(self, page):
        # Get current HTML
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        actions = []
        
        # 1. Detect Search Bars (Inputs OR Textareas)
        # We look for common search attributes like name='q' (Google/Bing) or type='search'
        search_candidates = soup.find_all(['input', 'textarea'])
        has_search = False
        for el in search_candidates:
            # Check if it looks like a search bar
            if (el.get('name') == 'q' or 
                el.get('type') == 'search' or 
                'search' in str(el.get('class', [])).lower() or
                'search' in str(el.get('placeholder', [])).lower()):
                has_search = True
                break
        
        if has_search:
            actions.append({
                "id": "search",
                "type": "input",
                "label": "Search this site",
                "param_name": "query"
            })

        # 2. Detect Readable Content (Headlines)
        # Limit to top 5 to keep JSON small
        headlines = soup.find_all(['h1', 'h2', 'h3'], limit=5)
        for idx, h in enumerate(headlines):
            text = h.get_text().strip()
            if text:
                actions.append({
                    "id": f"read_section_{idx}",
                    "type": "extract",
                    "label": f"Read: {text[:40]}...",
                    "selector": self._get_unique_selector(h) # In a real app, generate CSS path
                })
            
        return {
            "site_type": "generic",
            "url": page.url,
            "title": await page.title(),
            "available_actions": actions
        }

    async def execute(self, page, action_id, params):
        if action_id == "search":
            query = params.get("query")
            
            # --- IMPROVED SEARCH STRATEGY ---
            # Try these selectors in order. The first one that is visible gets used.
            selectors = [
                "textarea[name='q']",       # Google, Modern sites
                "input[name='q']",          # Old Google, Bing, DuckDuckGo
                "input[type='search']",     # Standard HTML5
                "input[placeholder*='Search']", # Generic placeholder
                "input[aria-label='Search']",   # Accessibility label
                "input[type='text']"        # Fallback
            ]
            
            for selector in selectors:
                try:
                    # check if visible (timeout 200ms to be fast)
                    if await page.locator(selector).first.is_visible(timeout=200):
                        print(f"Found search bar using: {selector}")
                        await page.fill(selector, query)
                        await page.press(selector, "Enter")
                        
                        # Wait for navigation or results to load
                        try:
                            await page.wait_for_load_state("networkidle", timeout=5000)
                        except:
                            pass # Continue even if network is still busy
                            
                        return {
                            "status": "success", 
                            "action": "search", 
                            "selector_used": selector,
                            "new_title": await page.title()
                        }
                except Exception:
                    continue # Try next selector

            return {"success": False, "error": "Could not find a search bar on this page."}
            
        return {"success": False, "error": "Unknown Action"}

    def _get_unique_selector(self, tag):
        # Helper to generate a simple selector (simplified for MVP)
        if tag.get('id'):
            return f"#{tag['id']}"
        return tag.name