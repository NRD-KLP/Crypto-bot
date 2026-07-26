FROM python:3.10
WORKDIR /app
COPY reqiurements.txt .
RUN pip install -r requirements.txt
COPY bot.py .
CMD ["python", "bot.py"]
