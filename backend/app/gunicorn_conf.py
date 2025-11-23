import logging

# Disable access log
accesslog = None

# Keep only error log
errorlog = '-'

# Uvicorn log level
loglevel = "warning"

# Disable uvicorn access log:
# (Gunicorn passes this to Uvicorn worker)
raw_env = [
    "UVICORN_ACCESS_LOG=false",
    "UVICORN_LOG_LEVEL=warning"
]
