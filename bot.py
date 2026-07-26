import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler

TOKEN = os.environ.get("TOKEN")
bot = Bot(token=TOKEN)
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Bot is running!"
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Привет!")))
        application.process_update(update)
        return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
