from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import psycopg2

from gemini_sdk import get_chat_completion, model  # importing model also

app = FastAPI()

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
        host="localhost",      # change if needed
        database="demodb",
        user="postgres",
        password="postgre2025",
        port="5432"
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

        # Format rows into readable text
        rows_text = ""
        for row in db_result["rows"]:
            rows_text += ", ".join(str(item) for item in row) + "\n"

        # New Gemini prompt
        second_prompt = f"""
User asked: "{user_prompt}"

Here is the SQL query result:
{rows_text}

Based on the user's request and the SQL result, please generate a clear, natural human-readable answer.
Do not show raw data, make it a nice sentence.
"""

        response = model.generate_content(second_prompt)
        return response.text.strip()

    except Exception as e:
        print(f"Error in human-readable conversion: {e}")
        return "Couldn't generate human readable answer."

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
        # Step 1: Generate SQL
        sql_query = get_chat_completion(messages)
        
        # Step 2: Run SQL
        db_result = run_sql_query(sql_query)
        
        # Step 3: Create Human Sentence
        human_answer = convert_to_human_readable(messages[-1]["content"], db_result)

        return {
            "sql_query": sql_query,
            "db_result": db_result,
            "human_answer": human_answer
        }

    except Exception as e:
        return {"reply": f"Sorry, error occurred: {str(e)}"}


# # main.py

# from fastapi import FastAPI, Request
# from fastapi.responses import HTMLResponse
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from pathlib import Path
# import psycopg2
# import os
# from dotenv import load_dotenv

# from gemini_sdk import get_chat_completion

# load_dotenv()

# app = FastAPI()

# # Allow CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Database runner
# def run_sql_query(sql_query):
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"),
#             database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASSWORD"),
#             port=os.getenv("DB_PORT"),
#         )
#         cur = conn.cursor()
#         cur.execute(sql_query)

#         rows = cur.fetchall()
#         columns = [desc[0] for desc in cur.description]

#         cur.close()
#         conn.close()

#         return {
#             "columns": columns,
#             "rows": rows
#         }
#     except Exception as e:
#         print(f"Database error: {e}")
#         raise e


# @app.get("/", response_class=HTMLResponse)
# async def serve_home():
#     html_path = Path("index.html")
#     return HTMLResponse(content=html_path.read_text(), status_code=200)

# @app.post("/chat")
# async def chat(request: Request):
#     data = await request.json()
#     messages = data.get("messages", [])
    
#     if not messages:
#         return {"reply": "No message provided."}

#     try:
#         sql_query = get_chat_completion(messages)
#         db_result = run_sql_query(sql_query)

#         return {
#             "reply": sql_query,
#             "db_result": db_result
#         }
#     except Exception as e:
#         return {"reply": f"Sorry, I couldn't process your request. Error: {str(e)}"}



# from fastapi import FastAPI, Request
# from fastapi.responses import HTMLResponse
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from pathlib import Path

# from gemini_sdk import get_chat_completion

# app = FastAPI()

# # Allow CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# @app.get("/", response_class=HTMLResponse)
# async def serve_home():
#     html_path = Path("index.html")
#     return HTMLResponse(content=html_path.read_text(), status_code=200)

# @app.post("/chat")
# async def chat(request: Request):
#     data = await request.json()
#     messages = data.get("messages", [])
    
#     if not messages:
#         return {"reply": "No message provided."}

#     try:
#         reply = get_chat_completion(messages)
#         return {"reply": reply}
#     except Exception as e:
#         return {"reply": f"Sorry, I couldn't process your request. Error: {str(e)}"}

