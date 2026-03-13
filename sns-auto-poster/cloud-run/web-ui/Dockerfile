FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8081

CMD ["gunicorn", "--bind", "0.0.0.0:8081", "--workers", "2", "main:app"]
