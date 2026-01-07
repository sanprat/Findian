FROM python:3.11-slim
# Cache-bust: 2026-01-07-21:50 - Fixed TA-Lib installation (numpy + LD_LIBRARY_PATH)

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib C Library
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Set LD_LIBRARY_PATH for TA-Lib
ENV LD_LIBRARY_PATH=/usr/lib:$LD_LIBRARY_PATH

# Install Python dependencies
# Install numpy first (required for TA-Lib)
RUN pip install --no-cache-dir numpy

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway provides PORT env var, default to 8000 for local dev
ENV PORT=8000
EXPOSE $PORT

# Run the application - Railway will inject $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
