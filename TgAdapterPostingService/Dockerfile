FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY tg_adapter_posting_service.py ./tg_adapter_posting_service.py

EXPOSE 8005

CMD ["uvicorn", "tg_adapter_posting_service:app", "--host", "0.0.0.0", "--port", "8005"]
