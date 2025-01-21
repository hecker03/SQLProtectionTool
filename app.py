import mysql.connector
import openai
import re

base_url = "https://api.aimlapi.com/v1"
api_key = "4e18cfb70cae4c1e8caeecf8fd97ffee"
openai.api_key = api_key 
openai.api_base = base_url

def connect_to_database():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="P@ssw0rd",  # Replace with your MySQL password
        database="hackathon"  # Replace with your database name
    )

# Connection with the OpenAI framework
def get_response(usrprompt, model="mistralai/Mistral-7B-Instruct-v0.2"):
    try:
        completion = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": usrprompt}],
        )
        return completion['choices'][0]['message']['content']
    except Exception as e:
        return f"An error occurred: {e}"
    
# Identify the programming language and vulnerable query
def get_proglang_by_code(source_code):
    lines = source_code.splitlines()
    prompt = ""
    vulnerable_query = ""
    db = connect_to_database()
    cur = db.cursor(dictionary=True)
    q = "Select * from identify"
    cur.execute(q)
    res = cur.fetchall()
    for x in res:
        for line in lines:
            if x[2] in line:
                prompt = line
            else:
                pattern = r"SELECT\s+.*?\s+FROM\s+\w+"
                matches = re.findall(pattern, line)
                if matches:
                    vulnerable_query = line
    if prompt:
        prompt += "\nWhich language is this?(one-word answer)"
    return get_response(prompt), vulnerable_query