from groq import Groq
import os
import re
import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from pandas import DataFrame

# Load App/.env explicitly
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

# Default to a supported model if not configured
GROQ_MODEL = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

db_path = Path(__file__).parent / "db.sqlite"

client_sql = Groq()

sql_prompt = f"""
You are an expert SQL query generator with strong knowledge of database schemas and natural language understanding. Your responsibility is to generate accurate and valid SQLite SQL queries based only on the user's question and the provided database schema.

Guidelines:
1. Return only the SQL query.
2. Do not provide explanations or additional text.
3. Do not use markdown formatting.
4. Use only the tables and columns mentioned in the schema.
5. If the question cannot be answered from the schema, return: 'I do not know';
6. Generate SQLite-compatible SQL syntax only.
7. Use LIKE with '%' wildcards for partial text matching.
8. Never use ILIKE.
9. Brand names may appear in any letter case, so always perform case-insensitive matching using LOWER().
10. Always use LOWER(column_name) LIKE LOWER('%value%') for brand filtering.
11. Generate only a single SQL query.
12. Always return the final query inside <SQL></SQL> tags.

<schema>
Table: product
Columns:
- product_link : STRING (product hyperlink)
- title : STRING
- brand : STRING
- price : FLOAT
- discount : FLOAT (Stored as decimal, e.g., 0.3 means 30% discount, 0.5 means 50% discount)
- avg_rating : FLOAT
- total_ratings : INTEGER
</schema>

Examples:

User Question: Show Puma shoes under 3000
Response:
<SQL>SELECT * FROM product WHERE LOWER(brand) LIKE LOWER('%puma%') AND price < 3000;</SQL>

User Question: Show top-rated Nike shoes
Response:
<SQL>SELECT * FROM product WHERE LOWER(brand) LIKE LOWER('%nike%') ORDER BY avg_rating DESC LIMIT 10;</SQL>

User Question: Show product with more than 50 percent discount
Response:
<SQL>SELECT * FROM product WHERE discount >= 0.5;</SQL>
"""



def generate_sql_query(question: str) -> str:
    
    

    chat_completion= client_sql.chat.completions.create(
        messages=[
            {
                "role": "system", 
                "content": sql_prompt
            },
             {
                "role": "user", 
                "content": question
            },
        ],
                
        model=os.getenv('GROQ_MODEL_NAME', GROQ_MODEL),
        temperature=0.2, 
        max_tokens=1024,
        )

    return chat_completion.choices[0].message.content



def run_query(query):
    if query.strip().upper().startswith("SELECT"):
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(query, conn)
            return df
    else:
        raise ValueError("Only SELECT queries are allowed.")

def sql_chain(question):
    try:
        sql_query = generate_sql_query(question)
    except Exception as e:
        return f"Sorry, I couldn't generate SQL for that request ({type(e).__name__})."
    print("Generated SQL Query: ", sql_query)

    # Extract SQL from <SQL>...</SQL> if present
    pattern = r"<SQL>\s*(.*?)\s*</SQL>"
    matches = re.findall(pattern, sql_query, re.IGNORECASE | re.DOTALL)
    print("SQL Query extracted from tags: ", matches[0].strip() if matches else "No SQL tags found.")
    if matches:
        sql_query = matches[0].strip()
    else:
        sql_query = sql_query.strip()

    # Safety check
    if not sql_query.upper().startswith("SELECT"):
        raise ValueError(f"Only SELECT queries are allowed: {sql_query}")
    response = run_query(sql_query)
    if response.empty:
        return "No results found."
    
    context = response.to_dict(orient='records')
    # Try to format with the LLM; if it fails, fall back to a local formatter
    data_response = data_comprehension(question, context)
    if isinstance(data_response, str) and data_response.startswith("Sorry, I couldn't format"):
        # Local formatting: concise product list
        lines = []
        for i, row in enumerate(response.to_dict(orient='records'), start=1):
            lines.append(f"Product {i}:")
            if 'title' in row and row['title']:
                lines.append(f"- Name: {row.get('title')}")
            if 'brand' in row and row['brand']:
                lines.append(f"- Brand: {row.get('brand')}")
            if 'price' in row and row['price'] is not None:
                lines.append(f"- Price: {row.get('price')}")
            # product_link field variations
            link = row.get('product_link') or row.get('link') or row.get('url') or row.get('product_url')
            lines.append(f"- Link: {link if link else 'Not available'}")
            lines.append("")
        return "\n".join(lines)

    return data_response



comprehension_prompt = """
You are a data interpretation assistant.

You will be given:
1. A user's QUESTION
2. The SQL query result (a list of products in tabular or dictionary format) called DATA

Your task:
- Understand the user's intent from the question.
- Interpret the SQL result as a product listing.
- Reshape and present the data in a clean, human-readable chat response.

Formatting rules:
- Present results as a structured product list.
- Each product should be clearly separated.
- Use the following format:

Product 1:
- Name: ...
- Brand: ...
- Price: ...
- Link: ...
- Any other available attributes (color, rating, category, etc.)

Product 2:
- Name: ...
- Brand: ...
- Price: ...
- Link: ...

Important rules:
- ALWAYS include the product link if it exists in the DATA (fields like: link, url, product_url, href).
- If multiple link fields exist, choose the most direct product page URL.
- If link is missing, write: "Link: Not available"
- Do not fabricate or hallucinate any values.
- If a field is missing, skip it (except Link which must always be shown).

Edge cases:
- If DATA is empty, respond: "No matching products found."
- Do not explain SQL or database logic.
- Do not return raw JSON, dataframe, or SQL output.

Keep the response concise, structured, and user-friendly.
"""
def data_comprehension(question: str, context) -> str:
    try:
        chat_completion= client_sql.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": comprehension_prompt
                },
                 {
                    "role": "user", 
                    "content": f"QUESTION: {question}\n DATA: {context}"
                },
            ],
                    
            model=os.getenv('GROQ_MODEL_NAME', GROQ_MODEL),
            temperature=0.2, 
            # max_tokens=1024,
        )

        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Sorry, I couldn't format the query results right now ({type(e).__name__})."



if __name__ == "__main__":
    question = "All product which has >0.3 discount and ratings above 4.8 and brand ADIDAS"
    answer = sql_chain(question)
    print("Answer: ", answer)
    # sql_query = generate_sql_query(question)
    # query = "SELECT * FROM product WHERE brand LIKE '%nike%'"
    #df = run_query(query)
    pass