from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from gemini_sdk import get_chat_completion

app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def serve_home():
    html_path = Path("index.html")
    return HTMLResponse(content=html_path.read_text(), status_code=200)

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    
    if not messages:
        return {"reply": "No message provided."}

    try:
        reply = get_chat_completion(messages)
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Sorry, I couldn't process your request. Error: {str(e)}"}

