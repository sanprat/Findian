# CACHE-BUST: 2026-01-04-v3
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8443

CMD ["python", "main.py"]
