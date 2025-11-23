from fastapi import FastAPI
import subprocess, uvicorn, os

app = FastAPI()

@app.post("/run")
async def run_program(data: dict):
    path = data.get("path")
    args = data.get("args", [])
    if not os.path.exists(path):
        return {"status": "error", "message": f"File not found: {path}"}
    try:
        subprocess.Popen([path] + args, shell=True)
        return {"status": "ok", "message": "Program started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5055)
