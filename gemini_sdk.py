import os
import google.generativeai as genai
from dotenv import load_dotenv
import psycopg2

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def fetch_table_structure():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="demodb",
            user="postgres",
            password="postgre2025",
            port="5432"
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

        cur.close()
        conn.close()

        return table_structure

    except Exception as e:
        print(f"Error fetching table structure: {e}")
        return ""

model = genai.GenerativeModel('gemini-1.5-pro')

def get_chat_completion(messages, chart_mode=False):
    try:
        user_message = messages[-1]["content"]
        print("Sending to Gemini:", user_message)

        table_structure = fetch_table_structure()

        final_prompt = table_structure + """

Rules:
- Always generate queries based on these tables and their relationships.
- Use proper JOINs where necessary.
- Use ILIKE for any text comparison to make it case-insensitive.
- Do not hallucinate columns.
- Output only pure PostgreSQL SQL code.
"""

        if chart_mode:
            final_prompt += """

Important:
- User wants a chart.
- Generate SQL that selects exactly 2 columns: one for x-axis (labels), one for y-axis (values).
- Alias them as 'x' and 'y'.
- Limit results if needed.
"""

        final_prompt += "\n\nUser Request: " + user_message

        response = model.generate_content(final_prompt)

        print("Gemini SQL response:", response.text)

        sql_query = response.text.strip()
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()

        return sql_query

    except Exception as e:
        print(f"Error during Gemini call: {e}")
        raise e


# import os
# import google.generativeai as genai
# from dotenv import load_dotenv
# import psycopg2

# load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# def fetch_table_structure():
#     conn = None
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"),
#             database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASSWORD"),
#             port=os.getenv("DB_PORT"),
#         )
#         cur = conn.cursor()

#         # Fetch tables
#         cur.execute("""
#             SELECT table_name
#             FROM information_schema.tables
#             WHERE table_schema = 'public'
#             ORDER BY table_name;
#         """)
#         tables = [row[0] for row in cur.fetchall()]

#         schema_info = "You must assume the following PostgreSQL database schema:\n\nTables:\n"

#         # Fetch columns for each table
#         for table in tables:
#             cur.execute(f"""
#                 SELECT column_name, data_type
#                 FROM information_schema.columns
#                 WHERE table_name = '{table}'
#                 ORDER BY ordinal_position;
#             """)
#             columns = cur.fetchall()

#             schema_info += f"\n1. {table}\n"
#             for col_name, data_type in columns:
#                 schema_info += f"- {col_name} ({data_type})\n"

#         # Fetch foreign keys
#         cur.execute("""
#             SELECT
#                 tc.table_name, kcu.column_name,
#                 ccu.table_name AS foreign_table_name,
#                 ccu.column_name AS foreign_column_name
#             FROM
#                 information_schema.table_constraints AS tc
#                 JOIN information_schema.key_column_usage AS kcu
#                   ON tc.constraint_name = kcu.constraint_name
#                 JOIN information_schema.constraint_column_usage AS ccu
#                   ON ccu.constraint_name = tc.constraint_name
#             WHERE tc.constraint_type = 'FOREIGN KEY';
#         """)
#         foreign_keys = cur.fetchall()

#         if foreign_keys:
#             schema_info += "\nRelationships:\n"
#             for table, column, foreign_table, foreign_column in foreign_keys:
#                 schema_info += f"- {table}.{column} is a foreign key to {foreign_table}.{foreign_column}\n"

#         # Rules
#         schema_info += """
# \nRules:
# - Always generate queries based on these tables and their relationships.
# - Use proper JOINs where necessary based on foreign keys.
# - Use ILIKE instead of = for any text comparison to make it case-insensitive.
# - Do not hallucinate columns that are not in these tables.
# - Output only pure PostgreSQL SQL code, without markdown formatting (no ```sql).
# """

#         cur.close()
#         return schema_info

#     except Exception as e:
#         print(f"Error fetching table structure: {e}")
#         return "Could not fetch table structure."
#     finally:
#         if conn:
#             conn.close()

# TABLE_STRUCTURE = fetch_table_structure()

# model = genai.GenerativeModel('gemini-1.5-pro')

# def get_chat_completion(messages, chart_mode=False):
#     try:
#         user_message = messages[-1]["content"]
#         print("Sending to Gemini:", user_message)

#         final_prompt = TABLE_STRUCTURE

#         if chart_mode:
#             final_prompt += """

# Important:
# - User wants a chart.
# - Generate SQL that selects exactly 2 columns: one for x-axis (labels), one for y-axis (values).
# - Alias the columns as 'x' and 'y' in the SELECT query.
# - Limit results to relevant number (e.g., 3 or 5).
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

# import os
# import google.generativeai as genai
# from dotenv import load_dotenv

# load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# TABLE_STRUCTURE = """
# You must assume the following PostgreSQL database schema:

# Tables:

# 1. employee
# - id (integer, primary key)
# - name (text)
# - age (integer)
# - department_id (integer, foreign key references department(id))
# - salary (numeric)
# - join_date (date)

# 2. department
# - id (integer, primary key)
# - name (text)
# - location (text)

# 3. project
# - id (integer, primary key)
# - name (text)
# - department_id (integer, foreign key references department(id))
# - start_date (date)
# - end_date (date)

# Relationships:
# - employee.department_id is a foreign key to department.id
# - project.department_id is a foreign key to department.id

# Rules:
# - Always generate queries based on these tables and their relationships.
# - Use proper JOINs where necessary based on foreign keys.
# - Use ILIKE instead of = for any text comparison to make it case-insensitive.
# - Do not hallucinate columns that are not in these tables.
# - Output only pure PostgreSQL SQL code, without markdown formatting (no ```sql).
# """

# model = genai.GenerativeModel('gemini-1.5-pro')

# def get_chat_completion(messages):
#     try:
#         user_message = messages[-1]["content"]
#         print("Sending to Gemini:", user_message)

#         final_prompt = TABLE_STRUCTURE + "\n\nUser Request: " + user_message

#         response = model.generate_content(final_prompt)

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

# load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# TABLE_STRUCTURE = """
# You must assume the following PostgreSQL database schema:

# Tables:

# 1. employee
# - id (integer, primary key)
# - name (text)
# - age (integer)
# - department_id (integer, foreign key references department(id))
# - salary (numeric)
# - join_date (date)

# 2. department
# - id (integer, primary key)
# - name (text)
# - location (text)

# 3. project
# - id (integer, primary key)
# - name (text)
# - department_id (integer, foreign key references department(id))
# - start_date (date)
# - end_date (date)

# Relationships:
# - employee.department_id is a foreign key to department.id
# - project.department_id is a foreign key to department.id

# Rules:
# - Always generate queries based on these tables and their relationships.
# - Use proper JOINs where necessary based on foreign keys.
# - Do not hallucinate columns that are not in these tables.
# - Output only pure PostgreSQL SQL code, without markdown formatting (no ```sql).
# """

# model = genai.GenerativeModel('gemini-1.5-pro')

# def get_chat_completion(messages):
#     try:
#         user_message = messages[-1]["content"]
#         print("Sending to Gemini:", user_message)

#         final_prompt = TABLE_STRUCTURE + "\n\nUser Request: " + user_message

#         response = model.generate_content(final_prompt)

#         print("Gemini response:", response.text)

#         sql_query = response.text.strip()
#         sql_query = sql_query.replace('```sql', '').replace('```', '').strip()

#         return sql_query

#     except Exception as e:
#         print(f"Error during Gemini call: {e}")
#         raise e


