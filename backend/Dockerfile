FROM python:3.10-slim
# Set working directory
WORKDIR /app
# Copy only backend code first (faster caching)
COPY backend/requirements.txt ./requirements.txt
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy backend source code only
COPY backend ./
# Create folder projects (optional)
RUN mkdir -p /app/Delft_Projects
# Copy frontend static files (optional)
COPY frontend /app/frontend
# Optional: set environment flag
ENV ENV=production
EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000"]
