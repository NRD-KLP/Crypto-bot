from flask import Flask



app = Flask(__name__)



@app.route("/")
def home():

    return "Bit Ref 4U Bot is running!"



def run_web():

    app.run(
        host="0.0.0.0",
        port=8080
    )
