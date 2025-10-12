# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system build deps for some Python packages (kept minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libffi-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app
COPY . /app

# Create non-root user and give ownership
RUN useradd -m botuser \
    && chown -R botuser:botuser /app

USER botuser

# Default command
CMD ["python", "bot.py"]

