from flask import Flask
import os

app = Flask(name)

@app.get("/")
def home():
    return "Bit Ref 4U Bot is running!"

def run_web():
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
