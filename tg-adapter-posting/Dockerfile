FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ /app/src/
COPY create_session.py .
ENV PYTHONPATH=/app/src
EXPOSE 8005
CMD ["uvicorn", "tg_adapter_posting.main:app", "--host", "0.0.0.0", "--port", "8005"]
