# browser_engine.py
import asyncio
from playwright.async_api import async_playwright, Browser, Page

# --- EXPANDED MANUAL STEALTH FUNCTION ---
async def apply_stealth(page: Page):
    """
    Applies multiple patches to hide browser automation.
    """
    # 1. Hides the 'webdriver' flag in the navigator.
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    # 2. Fakes a real Chrome browser's properties.
    await page.add_init_script("""
        window.navigator.chrome = {
            runtime: {},
            // add other properties you need to fake here
        };
    """)

    # 3. Fakes common browser plugins.
    await page.add_init_script("""
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
            ],
        });
    """)

    # 4. Fakes standard browser languages.
    await page.add_init_script("""
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
    """)
    
    # 5. Fakes WebGL vendor and renderer to look like a real GPU.
    await page.add_init_script("""
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                return 'Intel Open Source Technology Center';
            }
            if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                return 'Mesa DRI Intel(R) Ivybridge Mobile';
            }
            return getParameter(parameter);
        };
    """)
    
    # 6. Spoofs permissions to avoid bot-like "denied" or "prompt" states.
    await page.add_init_script("""
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.sessions = {} 

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        print("--- Browser Engine Started (Robust Manual Stealth) ---")

    async def create_session(self, session_id: str, url: str):
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = await context.new_page()
        
        # Apply our comprehensive stealth scripts before any navigation
        await apply_stealth(page)
        
        try:
            # wait_until="domcontentloaded" is faster and often sufficient
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Error loading {url}: {e}")

        self.sessions[session_id] = page
        return page

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    async def close_session(self, session_id: str):
        if session_id in self.sessions:
            try:
                await self.sessions[session_id].context.close()
            except Exception as e:
                print(f"Could not close session {session_id}: {e}")
            del self.sessions[session_id]

    async def close(self):
        print("--- Closing Browser Engine ---")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

engine = BrowserManager()