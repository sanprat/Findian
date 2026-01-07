FROM python:3.11-slim
# Cache-bust: 2026-01-07-22:43 - Fixed CMD PORT expansion with exec form

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway provides PORT env var, default to 8000 for local dev
ENV PORT=8000
EXPOSE $PORT

# Run the application - Use exec form with shell to expand $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

