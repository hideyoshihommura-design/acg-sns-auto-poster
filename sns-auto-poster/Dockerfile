FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p output

ENV PORT=8080

CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 "web_ui:create_app()"
