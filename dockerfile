FROM python:3.13.3-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry" \
    PATH="/opt/poetry/bin:${PATH}"

# system deps (add any you need later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash mercury
WORKDIR /app

# Install pip deps from requirements.txt
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
  && pip install --no-cache-dir -r /app/requirements.txt

# Copy application code (dockerignore below prevents copying mounted dev folders)
COPY . /app

# Ensure app files owned by non-root user
RUN chown -R mercury:mercury /app

USER mercury

# Default command - run the FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]