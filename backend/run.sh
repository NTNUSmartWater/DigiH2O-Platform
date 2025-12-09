cd "$(dirname "$0")"

while true
do
    echo "Starting FastAPI server..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    echo "Server crashed. Restarting in 2 seconds..."
    sleep 2
done