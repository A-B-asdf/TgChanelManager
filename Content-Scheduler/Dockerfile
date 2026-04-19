FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY Content-Scheduler.py ./Content-Scheduler.py

EXPOSE 8000

CMD ["uvicorn", "Content-Scheduler:app", "--host", "0.0.0.0", "--port", "8000"]
