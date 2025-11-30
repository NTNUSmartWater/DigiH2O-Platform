FROM python:3.11-slim
# Set working directory
WORKDIR /app
# Copy only backend code first (faster caching)
COPY backend/requirements.txt requirements.txt
# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
# Create required directories and ensure they exist
RUN mkdir -p /app/Delft_Projects && \
    mkdir -p /app/static && \
    mkdir -p /app/backend && \
    mkdir -p /app/frontend
# Copy all file in ./backend folder to working directory /app
COPY backend /app
# Copy frontend build folder to image
COPY frontend /app/frontend
COPY backend/Delft_Projects /app/Delft_Projects
# Optional: set environment flag
ENV ENV=production
ENV PYTHONPATH=/app/app
EXPOSE 8000
# Disable Uvicorn access logs via env
ENV UVICORN_ACCESS_LOG=false
ENV UVICORN_LOG_LEVEL=info
CMD ["gunicorn", "app.main:app",\
    "-k", "uvicorn.workers.UvicornWorker",\
    "--timeout", "120",\
    "-w", "1", "-b", "0.0.0.0:8000",\
    "--config", "app/gunicorn_conf.py"]