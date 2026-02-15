FROM python:3.12-slim

# Install system deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates fonts-liberation libnss3 libatk-bridge2.0-0 \
    libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 \
    libpangocairo-1.0-0 libgtk-3-0 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install chromium

COPY . .

# Production defaults
ENV HEADLESS=true
ENV LOG_LEVEL=INFO
ENV CHECKPOINT_ENABLED=true

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
