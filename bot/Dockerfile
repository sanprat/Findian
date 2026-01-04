# CACHE BUST v4 - 2026-01-04 22:34
FROM python:3.11-slim

# Force rebuild by embedding timestamp
ARG BUILD_DATE=2026-01-04-22:34
RUN echo "Build date: ${BUILD_DATE}"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CRITICAL: Copy main.py FIRST to break cache
COPY main.py .

# Copy rest of application code
COPY . .

EXPOSE 8443

CMD ["python", "main.py"]
