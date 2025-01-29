from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
import openai
import os
import re

# OpenAI Configuration
base_url = "https://api.aimlapi.com/v1"
api_key = "4e18cfb70cae4c1e8caeecf8fd97ffee"
openai.api_key = api_key 
openai.api_base = base_url

app = Flask(__name__)
app.secret_key = os.urandom(24)

def connect_to_database():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="P@ssw0rd",  # Replace with your MySQL password
        database="hackathon"  # Replace with your database name
    )

# OpenAI query processing
def get_response(usrprompt, model="mistralai/Mistral-7B-Instruct-v0.2"):
    try:
        completion = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": usrprompt}],
        )
        return completion['choices'][0]['message']['content']
    except Exception as e:
        return f"An error occurred: {e}"

# Identify programming language and extract vulnerable query
def get_proglang_by_code(source_code):
    lines = source_code.splitlines()
    prompt, vulnerable_query = "", ""
    db = connect_to_database()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM identify")
    res = cur.fetchall()
    
    for x in res:
        for line in lines:
            if x.get('line','') in line:
                prompt = line
            else:
                matches = re.findall(r"SELECT\s+.*?\s+FROM\s+\w+", line)
                if matches:
                    vulnerable_query = line
    
    if prompt:
        prompt += "\nWhich language is this? (one-word answer)"
    return get_response(prompt), vulnerable_query

@app.route('/')
def index():
    return render_template('index.html', logged_in=session.get('logged_in', False), username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = request.form.get('username'), request.form.get('password')
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        try:
            db = connect_to_database()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()
            db.close()
            
            if user:
                session['logged_in'] = True
                session['username'] = user['username']
                return redirect(url_for('source'))
            else:
                return jsonify({"error": "Invalid username or password"}), 401
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/source', methods=['GET', 'POST'])
def source():
    protected_query, error = None, None
    
    if request.method == 'POST':
        source_code = request.form.get('source_code')
        if not source_code:
            error = "Source code is required."
        else:
            code = get_protected_query(source_code)
            return jsonify({"processed_code": code})
            # if isinstance(response, dict) and "protected_query" in response:
            #     protected_query = response["protected_query"]
            # else:
            #     error = "An error occurred while processing the source code."

    return render_template('source.html', protected_query=protected_query, error=error)

@app.route('/get_protected_query', methods=['POST'])
def get_protected_query(source_code):
    if not source_code:
        return jsonify({"error": "No source code provided"}), 400

    # Identify programming language and extract vulnerable query
    programming_lang, vulnerable_query = get_proglang_by_code(source_code)
    if not programming_lang or not vulnerable_query:
        return jsonify({"error": "Unable to identify programming language or vulnerable query."}), 400
    try :
        # Regular expressions to detect vulnerabilities
        unsafe_patterns = [
            (r"'\{(\w+)\}'", r"%s"),  # Replace '{username}' -> %s
            (r"'\%s'", r"%s"),  # Replace '%s' -> %s
            (r"\"%s\"", r"%s"),  # Handle double-quoted '%s'
            (r"\+\s*\w+\s*\+\s*", r"%s")  # Replace string concatenation (e.g., '+ username +')
        ]

        secure_query = vulnerable_query
        for pattern, replacement in unsafe_patterns:
            secure_query = re.sub(pattern, replacement, secure_query)
        lines = source_code.splitlines()
        codesource=""
        for line in lines:
            if line == vulnerable_query:
                codesource+=f"\n{secure_query}"
            else:
                codesource+=f"\n{line}"
        # Return JSON response
        return codesource
    # jsonify({
    #         "programming_language": programming_lang,
    #         "vulnerable_query": vulnerable_query,
    #         "protected_query": secure_query
    #     })
    #     # return jsonify({"error": f"What we got {vulnerable_query}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#No protected query found for language:
if __name__ == "__main__":
    app.run(debug=True)