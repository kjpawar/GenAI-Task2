import os
import json
import hashlib
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import psycopg2
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Constants
MODEL_NAME = 'gemini-1.5-pro'
EXAMPLES_DIR = 'training_examples'
os.makedirs(EXAMPLES_DIR, exist_ok=True)

model = genai.GenerativeModel(MODEL_NAME)

SMTP_SERVER = os.getenv("SMTP_SERVER")    # Change if you use Outlook, Yahoo, etc.
SMTP_PORT = os.getenv("SMTP_PORT")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # App Password if Gmail + 2FA
EMAIL_TO = os.getenv("EMAIL_TO")


def fetch_table_structure():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
        )
        cur = conn.cursor()

        table_structure = "You must assume the following PostgreSQL database schema:\n\nTables:\n"

        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' AND table_type='BASE TABLE'
        """)
        tables = cur.fetchall()

        for table in tables:
            table_name = table[0]
            table_structure += f"\n{table_name}\n"

            cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
            """)
            columns = cur.fetchall()

            for column in columns:
                table_structure += f"- {column[0]} ({column[1]})\n"

        
        # Example: Calculate total revenue
        cur.execute("""
        SELECT SUM(quantity_sold * unit_price) AS total_revenue
        FROM sales_table;
        """)
        result = cur.fetchone()
        total_revenue = result[0] if result[0] is not None else 0

        print(f"Total Revenue: {total_revenue}")
        
        # Check if revenue is less than 20,000
        if total_revenue < 20000:
        # Prepare HTML email
           subject = "⚠️ Revenue Alert: Low Revenue Detected!"
           html_content = f"""
           <html>
           <body>
            <h2 style="color: red;">Revenue Alert 🚨</h2>
            <p>Dear Team,</p>
            <p>The total revenue has dropped below the threshold.</p>
            <p><strong>Current Revenue:</strong> ${total_revenue:,.2f}</p>
            <p>Please take immediate action.</p>
            <hr>
            <p style="font-size:12px;color:gray;">This is an automated message from the Financial Monitoring System.</p>
           </body>
           </html>
           """

           # Set up email message
           message = MIMEMultipart('alternative')
           message['From'] = EMAIL_USER
           message['To'] = EMAIL_TO
           message['Subject'] = subject

           message.attach(MIMEText(html_content, 'html'))

           # Send the email
           with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
              server.starttls()  # Secure the connection
              server.login(EMAIL_USER, EMAIL_PASSWORD)
              server.sendmail(EMAIL_USER, EMAIL_TO, message.as_string())

           print("✅ Alert Email sent successfully.")

        else:
           print("✅ Revenue is healthy, no email sent.")


        cur.close()
        conn.close()


        


        return table_structure

    except Exception as e:
        print(f"Error fetching table structure: {e}")
        return ""
def load_training_examples():
    """Load saved examples with error handling"""
    examples_file = os.path.join(EXAMPLES_DIR, 'examples.json')
    try:
        if os.path.exists(examples_file):
            with open(examples_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading examples: {e}")
    return {"natural_language": [], "sql": []}

def save_training_examples(examples):
    """Save examples with atomic write"""
    temp_file = os.path.join(EXAMPLES_DIR, 'temp_examples.json')
    examples_file = os.path.join(EXAMPLES_DIR, 'examples.json')
    
    try:
        with open(temp_file, 'w') as f:
            json.dump(examples, f, indent=2)
        os.replace(temp_file, examples_file)  # Atomic operation
    except Exception as e:
        print(f"Error saving examples: {e}")

def add_training_examples(new_nl, new_sql):
    """Add new examples with content-based deduplication"""
    examples = load_training_examples()
    existing_hashes = {hashlib.md5(nl.encode()).hexdigest(): i 
                      for i, nl in enumerate(examples["natural_language"])}
    
    added = 0
    for nl, sql in zip(new_nl, new_sql):
        nl_hash = hashlib.md5(nl.encode()).hexdigest()
        if nl_hash not in existing_hashes:
            examples["natural_language"].append(nl)
            examples["sql"].append(sql)
            existing_hashes[nl_hash] = len(examples["natural_language"]) - 1
            added += 1
    
    if added > 0:
        save_training_examples(examples)
    return added

def get_chat_completion(messages, chart_mode=False):
    try:
        user_message = messages[-1]["content"]
        examples = load_training_examples()
        
        prompt = f"""Database Expert Instructions:
{fetch_table_structure()}

Recent Examples:
"""
        # Add most relevant examples
        for nl, sql in zip(examples["natural_language"][-3:], examples["sql"][-3:]):
            prompt += f"\nQ: {nl}\nA: {sql}\n"
        
        prompt += f"""
Rules:
- Generate precise PostgreSQL queries
- Use only the schema shown
- Never invent columns

{"CHART REQUEST: Return exactly 2 columns with clear aliases" if chart_mode else ""}

New Query:
Q: {user_message}
A: """
        
        response = model.generate_content(prompt)
        sql = response.text.strip().removeprefix('```sql').removesuffix('```').strip()
        return sql
    except Exception as e:
        print(f"Generation error: {e}")
        raise












# import os
# import json
# import hashlib
# from datetime import datetime
# import google.generativeai as genai
# from dotenv import load_dotenv
# import psycopg2

# load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# # Constants
# MODEL_NAME = 'gemini-1.5-pro'
# EXAMPLES_DIR = 'training_examples'
# os.makedirs(EXAMPLES_DIR, exist_ok=True)

# model = genai.GenerativeModel(MODEL_NAME)

# def fetch_table_structure():
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"),
#             database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASSWORD"),
#             port=os.getenv("DB_PORT"),
#         )
#         cur = conn.cursor()

#         table_structure = "You must assume the following PostgreSQL database schema:\n\nTables:\n"

#         cur.execute("""
#             SELECT table_name 
#             FROM information_schema.tables 
#             WHERE table_schema='public' AND table_type='BASE TABLE'
#         """)
#         tables = cur.fetchall()

#         for table in tables:
#             table_name = table[0]
#             table_structure += f"\n{table_name}\n"

#             cur.execute(f"""
#                 SELECT column_name, data_type 
#                 FROM information_schema.columns 
#                 WHERE table_name = '{table_name}'
#             """)
#             columns = cur.fetchall()

#             for column in columns:
#                 table_structure += f"- {column[0]} ({column[1]})\n"

#         cur.close()
#         conn.close()

#         return table_structure

#     except Exception as e:
#         print(f"Error fetching table structure: {e}")
#         return ""
# def load_training_examples():
#     """Load saved examples with error handling"""
#     examples_file = os.path.join(EXAMPLES_DIR, 'examples.json')
#     try:
#         if os.path.exists(examples_file):
#             with open(examples_file, 'r') as f:
#                 return json.load(f)
#     except Exception as e:
#         print(f"Error loading examples: {e}")
#     return {"natural_language": [], "sql": []}

# def save_training_examples(examples):
#     """Save examples with atomic write"""
#     temp_file = os.path.join(EXAMPLES_DIR, 'temp_examples.json')
#     examples_file = os.path.join(EXAMPLES_DIR, 'examples.json')
    
#     try:
#         with open(temp_file, 'w') as f:
#             json.dump(examples, f, indent=2)
#         os.replace(temp_file, examples_file)  # Atomic operation
#     except Exception as e:
#         print(f"Error saving examples: {e}")

# def add_training_examples(new_nl, new_sql):
#     """Add new examples with content-based deduplication"""
#     examples = load_training_examples()
#     existing_hashes = {hashlib.md5(nl.encode()).hexdigest(): i 
#                       for i, nl in enumerate(examples["natural_language"])}
    
#     added = 0
#     for nl, sql in zip(new_nl, new_sql):
#         nl_hash = hashlib.md5(nl.encode()).hexdigest()
#         if nl_hash not in existing_hashes:
#             examples["natural_language"].append(nl)
#             examples["sql"].append(sql)
#             existing_hashes[nl_hash] = len(examples["natural_language"]) - 1
#             added += 1
    
#     if added > 0:
#         save_training_examples(examples)
#     return added

# def get_chat_completion(messages, chart_mode=False):
#     try:
#         user_message = messages[-1]["content"]
#         examples = load_training_examples()
        
#         prompt = f"""Database Expert Instructions:
# {fetch_table_structure()}

# Recent Examples:
# """
#         # Add most relevant examples
#         for nl, sql in zip(examples["natural_language"][-3:], examples["sql"][-3:]):
#             prompt += f"\nQ: {nl}\nA: {sql}\n"
        
#         prompt += f"""
# Rules:
# - Generate precise PostgreSQL queries
# - Use only the schema shown
# - Never invent columns

# {"CHART REQUEST: Return exactly 2 columns with clear aliases" if chart_mode else ""}

# New Query:
# Q: {user_message}
# A: """
        
#         response = model.generate_content(prompt)
#         sql = response.text.strip().removeprefix('```sql').removesuffix('```').strip()
#         return sql
#     except Exception as e:
#         print(f"Generation error: {e}")
#         raise









# def load_training_examples():
#     """Load saved training examples from file"""
#     examples_file = os.path.join(EXAMPLES_DIR, 'examples.json')
#     if os.path.exists(examples_file):
#         with open(examples_file, 'r') as f:
#             return json.load(f)
#     return {"natural_language": [], "sql": []}

# def save_training_examples(examples):
#     """Save training examples to file"""
#     examples_file = os.path.join(EXAMPLES_DIR, 'examples.json')
#     with open(examples_file, 'w') as f:
#         json.dump(examples, f)

# def add_training_examples(natural_language, sql):
#     """Add new training examples"""
#     examples = load_training_examples()
#     examples["natural_language"].extend(natural_language)
#     examples["sql"].extend(sql)
#     save_training_examples(examples)

# def get_chat_completion(messages, chart_mode=False):
#     try:
#         user_message = messages[-1]["content"]
#         print("Sending to Gemini:", user_message)

#         table_structure = fetch_table_structure()
#         examples = load_training_examples()

#         # Build the prompt with examples
#         prompt = f"""You are a PostgreSQL expert. Convert natural language to SQL.

# Database Schema:
# {table_structure}

# Examples:
# """
#         # Add up to 5 most relevant examples
#         for nl, sql in zip(examples["natural_language"][-5:], examples["sql"][-5:]):
#             prompt += f"\nQ: {nl}\nA: {sql}\n"

#         prompt += f"""
# Rules:
# - Use only the tables and columns shown
# - Use proper JOINs where needed
# - Use ILIKE for text comparisons
# - Never invent columns that don't exist
# - Output only SQL code

# {"Important for Chart: Select exactly 2 columns with meaningful aliases" if chart_mode else ""}

# Now convert this:
# Q: {user_message}
# A: 
# """

#         response = model.generate_content(prompt)
#         sql_query = response.text.strip()
#         sql_query = sql_query.replace('```sql', '').replace('```', '').strip()

#         return sql_query

#     except Exception as e:
#         print(f"Error during Gemini call: {e}")
#         raise e



# import os
# import google.generativeai as genai
# from dotenv import load_dotenv
# import psycopg2
# import json
# from datetime import datetime

# load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# # Model configuration
# MODEL_NAME = 'gemini-1.5-pro'
# TUNED_MODELS_DIR = 'tuned_models'
# os.makedirs(TUNED_MODELS_DIR, exist_ok=True)

# # Load base model or fine-tuned model
# def get_model():
#     # Check if we have a fine-tuned model to use
#     tuned_models = [f for f in os.listdir(TUNED_MODELS_DIR) if f.endswith('.json')]
#     if tuned_models:
#         # Use the most recently tuned model
#         latest_model = max(tuned_models, key=lambda x: os.path.getmtime(os.path.join(TUNED_MODELS_DIR, x)))
#         with open(os.path.join(TUNED_MODELS_DIR, latest_model), 'r') as f:
#             tuning_data = json.load(f)
#             return genai.GenerativeModel(tuning_data['model_name'], 
#                                        system_instruction=tuning_data['system_instruction'])
    
#     # Fall back to base model
#     return genai.GenerativeModel(MODEL_NAME)

# model = get_model()

# def fetch_table_structure():
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"),
#             database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASSWORD"),
#             port=os.getenv("DB_PORT"),
#         )
#         cur = conn.cursor()

#         table_structure = "You must assume the following PostgreSQL database schema:\n\nTables:\n"

#         cur.execute("""
#             SELECT table_name 
#             FROM information_schema.tables 
#             WHERE table_schema='public' AND table_type='BASE TABLE'
#         """)
#         tables = cur.fetchall()

#         for table in tables:
#             table_name = table[0]
#             table_structure += f"\n{table_name}\n"

#             cur.execute(f"""
#                 SELECT column_name, data_type 
#                 FROM information_schema.columns 
#                 WHERE table_name = '{table_name}'
#             """)
#             columns = cur.fetchall()

#             for column in columns:
#                 table_structure += f"- {column[0]} ({column[1]})\n"

#         cur.close()
#         conn.close()

#         return table_structure

#     except Exception as e:
#         print(f"Error fetching table structure: {e}")
#         return ""

# def prepare_fine_tuning_data(natural_language_queries, sql_queries):
#     """Prepare data for fine-tuning in the required format."""
#     training_data = []
#     for nlq, sql in zip(natural_language_queries, sql_queries):
#         training_data.append({
#             "input": nlq,
#             "output": sql
#         })
#     return training_data

# def fine_tune_model(dataset_path):
#     """Fine-tune the model with the provided dataset."""
#     try:
#         with open(dataset_path, 'r') as f:
#             data = json.load(f)
        
#         # Prepare system instruction with table structure
#         table_structure = fetch_table_structure()
#         system_instruction = f"""
#         {table_structure}

#         Rules:
#         - Always generate queries based on these tables and their relationships.
#         - Use proper JOINs where necessary.
#         - Use ILIKE for any text comparison to make it case-insensitive.
#         - Do not hallucinate columns.
#         - Output only pure PostgreSQL SQL code.
#         - For chart requests, select exactly 2 columns with meaningful aliases.
#         """
        
#         # Create tuning data
#         training_data = prepare_fine_tuning_data(data['natural_language'], data['sql'])
        
#         # Fine-tune the model (this is a simplified version - actual API may differ)
#         tuned_model = model.finetune(
#             training_data=training_data,
#             system_instruction=system_instruction
#         )
        
#         # Save tuning information
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         tuning_info = {
#             "model_name": f"{MODEL_NAME}-tuned-{timestamp}",
#             "system_instruction": system_instruction,
#             "training_data_size": len(training_data),
#             "tuned_at": timestamp
#         }
        
#         tuning_file = os.path.join(TUNED_MODELS_DIR, f"tuning_{timestamp}.json")
#         with open(tuning_file, 'w') as f:
#             json.dump(tuning_info, f)
        
#         return True, f"Model fine-tuned successfully. Tuning info saved to {tuning_file}"
    
#     except Exception as e:
#         return False, f"Fine-tuning failed: {str(e)}"

# def get_chat_completion(messages, chart_mode=False):
#     try:
#         user_message = messages[-1]["content"]
#         print("Sending to Gemini:", user_message)

#         # Get the current model (might be fine-tuned)
#         current_model = get_model()
        
#         # Generate prompt
#         prompt = "User Request: " + user_message
        
#         if chart_mode:
#             prompt += "\n\nImportant: This is a chart request. Select exactly 2 columns with meaningful aliases."
        
#         response = current_model.generate_content(prompt)
        
#         print("Gemini SQL response:", response.text)
        
#         sql_query = response.text.strip()
#         sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        
#         return sql_query
    
#     except Exception as e:
#         print(f"Error during Gemini call: {e}")
#         raise e

# import os
# import google.generativeai as genai
# from dotenv import load_dotenv
# import psycopg2

# load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# def fetch_table_structure():
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"),
#             database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASSWORD"),
#             port=os.getenv("DB_PORT"),
#         )
#         cur = conn.cursor()

#         table_structure = "You must assume the following PostgreSQL database schema:\n\nTables:\n"

#         cur.execute("""
#             SELECT table_name 
#             FROM information_schema.tables 
#             WHERE table_schema='public' AND table_type='BASE TABLE'
#         """)
#         tables = cur.fetchall()

#         for table in tables:
#             table_name = table[0]
#             table_structure += f"\n{table_name}\n"

#             cur.execute(f"""
#                 SELECT column_name, data_type 
#                 FROM information_schema.columns 
#                 WHERE table_name = '{table_name}'
#             """)
#             columns = cur.fetchall()

#             for column in columns:
#                 table_structure += f"- {column[0]} ({column[1]})\n"

#         cur.close()
#         conn.close()

#         return table_structure

#     except Exception as e:
#         print(f"Error fetching table structure: {e}")
#         return ""

# model = genai.GenerativeModel('gemini-1.5-pro')

# def get_chat_completion(messages, chart_mode=False):
#     try:
#         user_message = messages[-1]["content"]
#         print("Sending to Gemini:", user_message)

#         table_structure = fetch_table_structure()

#         final_prompt = table_structure + """

# Rules:
# - Always generate queries based on these tables and their relationships.
# - Use proper JOINs where necessary.
# - Use ILIKE for any text comparison to make it case-insensitive.
# - Do not hallucinate columns.
# - Output only pure PostgreSQL SQL code.
# """

#         if chart_mode:
#           final_prompt += """

# Important:
# - User wants a chart.
# - Generate SQL that selects exactly 2 columns: one for x-axis (labels), one for y-axis (values).
# - Always alias the first column meaningfully (e.g., 'Year', 'Department Name', 'Employee Name', etc.).
# - Always alias the second column meaningfully (e.g., 'Sales Count', 'Project Count', etc.).
# - Do not use generic aliases like x or y.
# - Limit results if needed.
# """

#         final_prompt += "\n\nUser Request: " + user_message

#         response = model.generate_content(final_prompt)

#         print("Gemini SQL response:", response.text)

#         sql_query = response.text.strip()
#         sql_query = sql_query.replace('```sql', '').replace('```', '').strip()

#         return sql_query

#     except Exception as e:
#         print(f"Error during Gemini call: {e}")
#         raise e

