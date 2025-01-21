import openai
import mysql.connector

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