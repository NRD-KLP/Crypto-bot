FROM python:3.10
WORKDIR /app
COPY bot.py .
RUN pip install python-telegram-bot
CMD ["python", "bot.py"]
