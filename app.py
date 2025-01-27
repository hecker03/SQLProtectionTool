from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
import openai
import re

base_url = "https://api.aimlapi.com/v1"
api_key = "4e18cfb70cae4c1e8caeecf8fd97ffee"
openai.api_key = api_key 
openai.api_base = base_url
app = Flask(__name__)

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

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        try:
            # Connect to the database
            db = connect_to_database()
            cursor = db.cursor(dictionary=True)

            # Query to check user credentials
            query = "SELECT * FROM users WHERE username = %s AND password = %s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

            db.close()

            if user:
                return redirect(url_for('home'))  # Redirect to home page on successful login
            else:
                return jsonify({"error": "Invalid username or password"}), 401

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return render_template('login.html')

# Signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Add signup logic here
        username = request.form.get('username')
        password = request.form.get('password')
        repassword = request.form.get('re-password')
        email = request.form.get('email')

        if password != repassword :
            return jsonify({"error": "Password doesn't match"}), 400

        if not username or not password or not email or not repassword:
            return jsonify({"error": "Username, password, and email are required"}), 400

        try:
            # Connect to the database
            db = connect_to_database()
            cursor = db.cursor()

            # Query to insert new user
            query = "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)"
            cursor.execute(query, (username, password, email))

            db.commit()
            db.close()

            return redirect(url_for('index'))  # Redirect to home page on successful signup

        except mysql.connector.Error as err:
            return jsonify({"error": f"Database error: {err}"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return render_template('signup.html')

# Source code submission page
@app.route('/source', methods=['GET', 'POST'])
def source():
    if request.method == 'POST':
        source_code = request.form.get('source_code')
        return redirect(url_for('get_protected_query', source_code=source_code))
    return render_template('source.html')

# Process the source code and provide the protected query
@app.route('/get_protected_query', methods=['GET', 'POST'])
def get_protected_query():
    source_code = request.args.get('source_code', '')

    programming_lang, vulnerable = get_proglang_by_code(source_code)

    if not programming_lang or not vulnerable:
        return jsonify({"error": "Unable to identify programming language or vulnerable query."}), 400

    try:
        db = connect_to_database()
        cursor = db.cursor(dictionary=True)

        query = "SELECT procQuery AS query_template FROM sqlapl WHERE language = %s"
        cursor.execute(query, (programming_lang,))
        result = cursor.fetchone()

        db.close()

        if result:
            return jsonify({
                "programming_language": programming_lang,
                "vulnerable_query": vulnerable,
                "protected_query": result["query_template"]
            })
        else:
            return jsonify({"error": f"No protected query found for language: {programming_lang}"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)