FROM python:3.11-slim
# Cache-bust: 2026-01-04-15:06 - Force complete rebuild (Finvasia removal)

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway provides PORT env var, default to 8000 for local dev
ENV PORT=8000
EXPOSE $PORT

# Run the application - Railway will inject $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
