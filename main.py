from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import psycopg2
import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from gemini_sdk import get_chat_completion, model, add_training_examples, load_training_examples

load_dotenv()
app = FastAPI()

# Setup directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("training_examples", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )

def run_sql_query(sql_query):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql_query)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return {"columns": columns, "rows": rows}
    except Exception as e:
        print(f"Database error: {e}")
        raise e

def convert_to_human_readable(user_prompt, db_result):
    try:
        if not db_result["rows"]:
            return "No results found."

        rows_text = ""
        for row in db_result["rows"]:
            rows_text += ", ".join(str(item) for item in row) + "\n"

        second_prompt = f"""
User asked: "{user_prompt}"

Here is the SQL query result:
{rows_text}

Based on the user's request and the SQL result, generate a human-readable answer.
Do not show raw data.
"""

        response = model.generate_content(second_prompt)
        return response.text.strip()

    except Exception as e:
        print(f"Error in human-readable conversion: {e}")
        return "Couldn't generate human readable answer."




@app.get("/", response_class=HTMLResponse)
async def serve_home():
    try:
        # Explicit UTF-8 encoding with error handling
        content = Path("index.html").read_text(encoding="utf-8", errors="strict")
        return HTMLResponse(content=content)
    except UnicodeDecodeError as e:
        # Fallback to binary read if needed
        with open("index.html", "rb") as f:
            return HTMLResponse(content=f.read().decode("utf-8"))
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Page not found</h1>", status_code=404)



def cleanup_old_uploads(days=1):
    """Remove uploads older than specified days"""
    cutoff = time.time() - (days * 86400)
    for filename in os.listdir("uploads"):
        filepath = os.path.join("uploads", filename)
        if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
            os.remove(filepath)

@app.on_event("startup")
async def startup():
    cleanup_old_uploads()

@app.post("/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    try:
        content = await file.read()
        
        # Normalize JSON to prevent formatting differences
        try:
            data = json.loads(content)
            normalized = json.dumps(data, sort_keys=True, indent=2).encode()
            content_hash = hashlib.md5(normalized).hexdigest()
        except json.JSONDecodeError as e:
            raise HTTPException(400, "Invalid JSON format") from e

        # Check for existing identical content
        for existing in os.listdir("uploads"):
            with open(os.path.join("uploads", existing), "rb") as f:
                if hashlib.md5(f.read()).hexdigest() == content_hash:
                    return JSONResponse(
                        {"status": "exists", "file": existing},
                        status_code=200
                    )

        # Save new file
        filename = f"dataset_{content_hash[:8]}.json"
        filepath = os.path.join("uploads", filename)
        with open(filepath, "wb") as f:
            f.write(normalized)

        # Add to training examples
        added = add_training_examples(data["natural_language"], data["sql"])
        
        return JSONResponse({
            "status": "success",
            "added": added,
            "total_examples": len(load_training_examples()["natural_language"]),
            "file": filename
        })
    
    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}") from e

@app.get("/training-status")
async def training_status():
    examples = load_training_examples()
    return {
        "example_count": len(examples["natural_language"]),
        "last_updated": os.path.getmtime(os.path.join("training_examples", "examples.json")) 
                       if os.path.exists(os.path.join("training_examples", "examples.json")) 
                       else None
    }

# ... (keep your existing chat endpoint and other routes) ...

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    
    if not messages:
        return {"reply": "No message provided."}

    user_prompt = messages[-1]["content"]

    try:
        chart_mode = "chart" in user_prompt.lower()

        sql_query = get_chat_completion(messages, chart_mode=chart_mode)
        db_result = run_sql_query(sql_query)
        
        if chart_mode:
            chart_data = {"x": [], "y": []}
            for row in db_result["rows"]:
                chart_data["x"].append(row[0])
                chart_data["y"].append(row[1])

            x_label = db_result["columns"][0] if db_result["columns"] else "X Axis"
            y_label = db_result["columns"][1] if len(db_result["columns"]) > 1 else "Y Axis"

  
            return {
                "sql_query": sql_query,
                "chart_data": {
                    "x": chart_data["x"],
                    "y": chart_data["y"],
                    "x_label": x_label,
                    "y_label": y_label
                },
                "error": False
            }
        else:
            human_answer = convert_to_human_readable(user_prompt, db_result)

            return {
                "sql_query": sql_query,
                "db_result": db_result,
                "human_answer": human_answer,
                "error": False
            }

    except Exception as e:
        return {
            "sql_query": "",
            "db_result": {"columns": [], "rows": []},
            "chart_data": None,
            "human_answer": f"Sorry, an error occurred: {str(e)}",
            "error": True
        }
@app.get("/list-uploads")
async def list_uploads():
    return {"files": os.listdir("uploads")}

