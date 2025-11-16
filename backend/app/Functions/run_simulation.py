import os, subprocess, threading, asyncio, re
from Functions import functions
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, DELFT_PATH
from starlette.websockets import WebSocketDisconnect

router = APIRouter()
processes = {}

def get_log_path(project_name):
    log_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "log.txt")
    return log_path
# Utility: append to file log
def append_log(project_name, text):
    log_path = get_log_path(project_name)
    with open(log_path, "a", encoding="utf-8", errors="replace") as f:
        f.write(text + "\n")

@router.post("/check_folder")
async def check_folder(request: Request):
    body = await request.json()
    project_name, folder = body.get('projectName'), body.get('folder', [])
    if isinstance(folder, str): folder = [folder]
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, *folder)
    status = 'ok' if os.path.exists(path) else 'error'
    return JSONResponse({"status": status})

# Check if simulation is running
@router.post("/check_sim_status_hyd")
async def check_sim_status_hyd(request: Request):
    body = await request.json()
    project_name = body.get("projectName")
    info = processes.get(project_name)
    if info:
        # Read log file
        log_path = get_log_path(project_name)
        logs = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                logs = f.read().splitlines()
        return JSONResponse({ "status": info["status"],
            "progress": info["progress"], "logs": logs[-4000:] })
    # Simulation not in memory → check if log exists → means finished earlier
    log_path = get_log_path(project_name)
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            logs = f.read().splitlines()
        return JSONResponse({ "status": "finished", "progress": 100, "logs": logs[-4000:] })
    return JSONResponse({"status": "none", "progress": 0, "logs": []})

# Start a hydrodynamic simulation
@router.post("/start_sim_hyd")
async def start_sim_hyd(request: Request):
    body = await request.json()
    project_name = body.get("projectName")
    # Check if simulation already running
    if project_name in processes and processes[project_name]["status"] == "running":
        return JSONResponse({"status": "error", "message": "Simulation is already running."})
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
    mdu_path = os.path.join(path, "FlowFM.mdu")
    bat_path = os.path.join(DELFT_PATH, "dflowfm/scripts/run_dflowfm.bat")
    if not os.path.exists(bat_path) or not os.path.exists(mdu_path):
        return JSONResponse({"status": "error", "message": "Executable or MDU file not found."})
    # Remove old log
    log_path = get_log_path(project_name)
    if os.path.exists(log_path): os.remove(log_path)
    # Run the process
    command = [bat_path, "--autostartstop", mdu_path]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", bufsize=1, cwd=path
    )
    processes[project_name] = {"process": process, "progress": 0.0, 
        "real_time_used": "N/A", "real_time_left": "N/A", "logs": [], "status": "running"}
    # Stream logs
    def stream_logs():
        percent_re = re.compile(r'(?P<percent>\d{1,3}(?:\.\d+)?)\s*%')
        time_re = re.compile(r'(?P<tt>\d+d\s+\d{1,2}:\d{2}:\d{2})')
        try:
            for line in process.stdout:
                line = line.strip()
                if not line: continue
                append_log(project_name, line)
                # Catch error messages
                if "forrtl:" in line.lower():
                    processes[project_name]["status"] = "error"
                    append_log(project_name, f"[ERROR] {line}")
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
                processes[project_name]["status"] = "finished"
                try:
                    post_result = functions.postProcess(path)
                    msg = f"[FINISHED] {post_result['message']}" if post_result["status"] == "ok" else f"[ERROR] {post_result['message']}"
                    append_log(project_name, msg)
                except Exception as e: append_log(project_name, f"[POSTPROCESS FAILED] {str(e)}")
            append_log(project_name, "[CLEANUP] Done.")
            processes[project_name]["progress"] = 100.0
    threading.Thread(target=stream_logs, daemon=True).start()
    return JSONResponse({"status": "ok", "message":  f"Simulation {project_name} started."})

@router.websocket("/sim_progress_hyd/{project_name}")
async def sim_progress_hyd(websocket: WebSocket, project_name: str):
    await websocket.accept()
    log_path = get_log_path(project_name)
    last_pos = 0
    try:
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