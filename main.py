from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
from uuid import uuid4
import uvicorn

# --- IMPORTS ---
# Import the browser engine singleton
from browser_engine import engine

# Import our logic handlers
from handlers.generic import GenericHandler
from handlers.chatgpt import ChatGPTHandler

# --- 1. LIFESPAN MANAGER (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- 🚀 Starting up Browser Engine ---")
    await engine.start()
    yield
    print("--- 🛑 Shutting down Browser Engine ---")
    await engine.close()

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

# --- 2. DATA MODELS ---
class CreateSessionRequest(BaseModel):
    url: str

class ActionRequest(BaseModel):
    action_id: str
    params: dict = {}

# --- 3. HELPER: Select Handler based on URL ---
def get_handler(url: str):
    """
    Decides which 'Brain' to use for the current website.
    """
    if "chatgpt.com" in url or "openai.com" in url:
        return ChatGPTHandler()
    # You can add more specific handlers here (e.g. Claude, Twitter)
    return GenericHandler()

# --- 4. API ENDPOINTS ---

@app.post("/session")
async def start_session(req: CreateSessionRequest):
    """
    Spins up a new browser tab (headless) and navigates to the URL.
    Returns a session_id to control this specific tab.
    """
    session_id = str(uuid4())
    
    try:
        # Ask engine to create a page
        page = await engine.create_session(session_id, req.url)
        
        # Detect which handler handles this URL
        handler = get_handler(req.url)
        
        return {
            "session_id": session_id,
            "status": "created",
            "handler_type": handler.__class__.__name__,
            "current_url": page.url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}/actions")
async def get_page_actions(session_id: str):
    """
    Scrapes the current page and tells the frontend what buttons/inputs to show.
    """
    # 1. Retrieve the browser page from memory
    page = engine.get_session(session_id)
    if not page:
        raise HTTPException(status_code=404, detail="Session not found. It may have expired.")

    # 2. Get the right handler logic based on where the browser IS currently
    handler = get_handler(page.url)

    # 3. Analyze the page
    try:
        actions = await handler.get_actions(page)
        return actions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing page: {str(e)}")

@app.post("/session/{session_id}/execute")
async def execute_action(session_id: str, req: ActionRequest):
    """
    Remote controls the browser: clicks buttons, types text, extracts data.
    """
    # 1. Retrieve the browser page
    page = engine.get_session(session_id)
    if not page:
        raise HTTPException(status_code=404, detail="Session not found.")

    # 2. Get the right handler logic
    handler = get_handler(page.url)

    # 3. Execute the action
    try:
        result = await handler.execute(page, req.action_id, req.params)
        return {
            "success": True,
            "result": result,
            "current_url": page.url
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.delete("/session/{session_id}")
async def close_session(session_id: str):
    """
    Manually close a specific tab/session to free up RAM.
    """
    await engine.close_session(session_id)
    return {"status": "closed", "session_id": session_id}

if __name__ == "__main__":
    # Running on 0.0.0.0 allows external access if needed
    # Port 8080 avoids common conflicts
    uvicorn.run(app, host="0.0.0.0", port=8080)