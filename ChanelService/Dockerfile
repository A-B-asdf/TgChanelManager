FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY chanel_service.py ./chanel_service.py

EXPOSE 8002

CMD ["uvicorn", "chanel_service:app", "--host", "0.0.0.0", "--port", "8002"]
