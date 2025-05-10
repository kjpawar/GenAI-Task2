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

SMTP_SERVER = os.getenv("SMTP_SERVER")    
SMTP_PORT = os.getenv("SMTP_PORT")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  
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

# cur.execute(f"""
#     SELECT column_name, data_type 
#     FROM information_schema.columns 
#     WHERE table_name = '{table_name}'
# """)

            cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name = %s
            """, (table_name,))
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

