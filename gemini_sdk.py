import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

TABLE_STRUCTURE = """
You must assume the following PostgreSQL database schema:

Tables:

1. employee
- id (integer, primary key)
- name (text)
- age (integer)
- department_id (integer, foreign key references department(id))
- salary (numeric)
- join_date (date)

2. department
- id (integer, primary key)
- name (text)
- location (text)

3. project
- id (integer, primary key)
- name (text)
- department_id (integer, foreign key references department(id))
- start_date (date)
- end_date (date)

Relationships:
- employee.department_id is a foreign key to department.id
- project.department_id is a foreign key to department.id

Rules:
- Always generate queries based on these tables and their relationships.
- Use proper JOINs where necessary based on foreign keys.
- Use ILIKE instead of = for any text comparison to make it case-insensitive.
- Do not hallucinate columns that are not in these tables.
- Output only pure PostgreSQL SQL code, without markdown formatting (no ```sql).
"""

model = genai.GenerativeModel('gemini-1.5-pro')

def get_chat_completion(messages):
    try:
        user_message = messages[-1]["content"]
        print("Sending to Gemini:", user_message)

        final_prompt = TABLE_STRUCTURE + "\n\nUser Request: " + user_message

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


