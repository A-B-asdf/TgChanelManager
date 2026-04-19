FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY tg_adapter_channel_service.py ./tg_adapter_channel_service.py

EXPOSE 8004

CMD ["uvicorn", "tg_adapter_channel_service:app", "--host", "0.0.0.0", "--port", "8004"]
