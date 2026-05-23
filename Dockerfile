FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Tesseract, OpenCV, and MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY OccaShare/requirements.txt ./OccaShare/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Start the application from the OccaShare directory
CMD cd OccaShare && gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 600 --workers 2
