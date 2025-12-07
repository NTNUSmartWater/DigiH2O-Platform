import os, subprocess, threading, asyncio, re, requests
from Functions import functions
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, DELFT_PATH, WINDOWS_AGENT_URL
from starlette.websockets import WebSocketDisconnect

router = APIRouter()
processes = {}

# Utility: append to file log
def append_log(log_path, text):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8", errors="replace") as f:
        f.write(text + "\n")

@router.post("/check_folder")
async def check_folder(request: Request):
    body = await request.json()
    project_name, folder = body.get('projectName'), body.get('folder', [])
    if isinstance(folder, str): folder = [folder]
    path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, *folder))
    status = 'ok' if os.path.exists(path) else 'error'
    return JSONResponse({"status": status})

# Check if simulation is running
@router.post("/check_sim_status_hyd")
async def check_sim_status_hyd(request: Request):
    body = await request.json()
    project_name = body.get("projectName")
    info = processes.get(project_name)
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log.txt"))
    if info:
        # Read log file
        logs = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                logs = f.read().splitlines()
        return JSONResponse({ "status": info["status"], "progress": info["progress"], "logs": logs})
    # Simulation not in memory → check if log exists → means finished earlier
    if os.path.exists(log_path):
        logs = []
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            logs = f.read().splitlines()
        return JSONResponse({ "status": "finished", "progress": 100, "logs": logs })
    return JSONResponse({"status": "none", "progress": 0, "logs": []})

# Start a hydrodynamic simulation
@router.post("/start_sim_hyd")
async def start_sim_hyd(request: Request):
    body = await request.json()
    project_name = body.get("projectName")
    # Check if simulation already running
    if project_name in processes and processes[project_name]["status"] == "running":
        return JSONResponse({"status": "error", "message": "Simulation is already running."})
    path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
    mdu_path = os.path.normpath(os.path.join(path, "FlowFM.mdu"))
    bat_path = os.path.normpath(os.path.join(DELFT_PATH, "dflowfm/scripts/run_dflowfm.bat"))
    # Check if file exists
    if not os.path.exists(mdu_path): return JSONResponse({"status": "error", "message": "MDU file not found."})
    if not os.path.exists(bat_path): return JSONResponse({"status": "error", "message": "Executable file not found."})
    # Remove old log
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log.txt"))
    if os.path.exists(log_path): os.remove(log_path)
    percent_re = re.compile(r'(?P<percent>\d{1,3}(?:\.\d+)?)\s*%')
    time_re = re.compile(r'(?P<tt>\d+d\s+\d{1,2}:\d{2}:\d{2})')
    # Run the process
    if request.app.state.env == 'development':
        # Run the process on host
        command = [bat_path, "--autostartstop", mdu_path]
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1, cwd=path
        )
        processes[project_name] = {"process": process, "progress": 0.0, 
            "real_time_used": "N/A", "real_time_left": "N/A", "logs": [], "status": "running"}
        # Stream logs
        def stream_logs():
            try:
                for line in process.stdout:
                    line = line.strip()
                    if not line: continue
                    append_log(log_path, line)
                    # Catch error messages
                    if "forrtl:" in line.lower() or "error" in line.lower():
                        processes[project_name]["status"] = "error"
                        append_log(log_path, f"[ERROR] {line}")
                        try: process.kill()
                        except: pass
                        break
                    # Check for progress
                    match_pct = percent_re.search(line)
                    if match_pct: processes[project_name]["progress"] = float(match_pct.group("percent"))
                    # Extract run time
                    times = time_re.findall(line)
                    if len(times) >= 4:
                        processes[project_name]["real_time_used"] = times[2]
                        processes[project_name]["real_time_left"] = times[3]
                    elif len(times) == 3:
                        processes[project_name]["real_time_used"] = times[1]
                        processes[project_name]["real_time_left"] = times[2]
            finally:
                process.wait()
                status = processes[project_name]["status"]
                if status != "error":
                    try:
                        processes[project_name]["status"] = "finished"
                        post_result = functions.postProcess(path)
                        msg = f"[FINISHED] {post_result['message']}" if post_result["status"] == "ok" else f"[ERROR] {post_result['message']}"
                        append_log(log_path, msg)
                    except Exception as e: append_log(log_path, f"[POSTPROCESS FAILED] {str(e)}")
                append_log(log_path, "[CLEANUP] Done.")
                processes[project_name]["progress"] = 100.0
        threading.Thread(target=stream_logs, daemon=True).start()
        return JSONResponse({"status": "ok", "message": f"Simulation {project_name} started on Windows host."})
    else: # Run the process on docker
        try:
            payload = {"action": "run_hyd", "bat_path": bat_path, "mdu_path": mdu_path, "project_name": project_name, 
                   "log_path": log_path, "cwd_path": path, "percent_re": str(percent_re), "time_re": str(time_re)}
            res = requests.post(WINDOWS_AGENT_URL, json=payload, timeout=10)
            res.raise_for_status()
            return JSONResponse({"status": "ok", "message": f"Simulation {project_name} started (via Windows Agent)."})
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"Exception: {str(e)}"})

@router.websocket("/sim_progress_hyd/{project_name}")
async def sim_progress_hyd(websocket: WebSocket, project_name: str):
    try:
        await websocket.accept()
        log_path, last_pos = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log.txt")), 0        
        while True:
            info = processes.get(project_name)
            if not info:
                await websocket.send_text("[ERROR] Simulation not running.")
                break
            # Send new logs to the client
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(last_pos)
                    for line in f:
                        await websocket.send_text(line.strip())
                    last_pos = f.tell()
            # Send progress to the client if it has changed
            await websocket.send_text(f"[PROGRESS] {info['progress']:.2f}|{info['real_time_used']}|{info['real_time_left']}")
            if info["status"] != "running":
                await websocket.send_text(f"[FINISHED] Simulation {info['status']}.")
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect: pass