# --- backend/Dockerfile ---
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend code
COPY . .

# Expose backend port
EXPOSE 8000

# Set environment variable for Delft3D path (default, can override in docker-compose)
ENV DELFT3D_PATH="/delft3d"

# Run backend (Flask or FastAPI)
CMD ["python", "main.py"]
