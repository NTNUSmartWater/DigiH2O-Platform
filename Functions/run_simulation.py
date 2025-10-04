import os, subprocess, threading, asyncio, re
from Functions import functions
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT
from starlette.websockets import WebSocketDisconnect

router = APIRouter()
processes = {}

@router.post("/check_folder")
async def check_folder(request: Request):
    body = await request.json()
    project_name, folder = body.get('projectName'), list(body.get('folder'))
    folders = [PROJECT_STATIC_ROOT, project_name] + folder
    path = os.path.join(*folders)
    status = 'ok' if os.path.exists(path) else 'error'
    return JSONResponse({"status": status})

# Check if simulation is running
@router.post("/check_sim_status")
async def check_sim_status(request: Request):
    body = await request.json()
    project_name = body.get("projectName")
    if project_name in processes:
        info = processes[project_name]
        return JSONResponse({
            "status": "running" if info["status"] == "running" else "finished",
            "progress": info["progress"],
            "logs": info["logs"]
        })
    return JSONResponse({"status": "none", "progress": 0, "logs": []})

# Start simulation
@router.post("/start_sim")
async def start_sim(request: Request):
    body = await request.json()
    project_name = body["projectName"]
    if project_name in processes and processes[project_name]["status"] == "running":
        return JSONResponse({"status": "error", "message": "Simulation is already running."})
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
    bat_path = os.path.normpath("C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dflowfm/scripts/run_dflowfm.bat")
    mdu_path = os.path.join(path, "FlowFM.mdu")
    if not os.path.exists(bat_path) or not os.path.exists(mdu_path):
        return JSONResponse({"status": "error", "message": "Executable or MDU file not found."})
    command = [bat_path, "--autostartstop", mdu_path]
    # Run the process
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
        errors="replace", text=True, shell=False, bufsize=1, cwd=path
    )
    processes[project_name] = {"process": process, "progress": 0, "logs": [], "status": "running"}
    def stream_logs():
        progress_pattern = re.compile(r"(\d+(?:\.\d+)?)%")
        for line in process.stdout:
            line = line.strip()
            if not line: continue
            processes[project_name]["logs"].append(line)
            # Catch error messages
            if "forrtl:" in line.lower():
                processes[project_name]["logs"].append(f"[ERROR] {line}")
                if process.poll() is None: process.terminate()
                processes[project_name]["status"] = "error"
                break
            # Check for progress
            match = progress_pattern.search(line)
            if match:
                processes[project_name]["progress"] = float(match.group(1))
        process.wait()
        processes[project_name]["status"] = "finished"
    threading.Thread(target=stream_logs, daemon=True).start()
    return JSONResponse({"status": "ok", "message": "Simulation started."})

@router.websocket("/sim_progress/{project_name}")
async def sim_progress(websocket: WebSocket, project_name: str):
    await websocket.accept()
    try:
        last_log, last_progress = 0, None
        while True:
            if project_name not in processes:
                await websocket.send_text("[ERROR] No such simulation.")
                break
            info = processes[project_name]
            logs = info["logs"]
            # Send new logs to the client
            while last_log < len(logs):
                await websocket.send_text(logs[last_log])
                last_log += 1
            # Send progress to the client if it has changed
            if info["progress"] != last_progress:
                last_progress = info["progress"]
                await websocket.send_text(f"[PROGRESS] {last_progress}")
            if info["status"] != "running":
                await websocket.send_text(f"[FINISHED] Simulation {info['status']}.")
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect: pass

# Stop simulation
@router.post("/stop_sim")
async def stop_sim(request: Request):
    body = await request.json()
    project_name = body["projectName"]
    if project_name in processes:
        proc = processes[project_name]["process"]
        if proc.poll() is None:
            proc.terminate()
            processes[project_name]["status"] = "stopped"
            return {"status": "ok", "message": "Simulation stopped."}
    return {"status": "error", "message": "No running simulation found."}