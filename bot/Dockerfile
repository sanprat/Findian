FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if any (none for now)

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run the bot
CMD ["python", "main.py"]
