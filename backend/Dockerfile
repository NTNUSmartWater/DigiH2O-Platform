FROM python:3.11-slim
# Set working directory
WORKDIR /app
# Copy only backend code first (faster caching)
COPY requirements.txt .
# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
# Add user to run the app
RUN useradd -m lamnguyen
USER lamnguyen
# Copy all file in ./backend folder to working directory /app
COPY . . 
# Create folder projects (optional)
RUN mkdir -p /app/Delft_Projects
# Optional: set environment flag
ENV ENV=production
ENV PYTHONPATH=/app/app

EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000"]
