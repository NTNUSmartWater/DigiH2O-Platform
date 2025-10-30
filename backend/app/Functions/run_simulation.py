import os, subprocess, threading, asyncio, re
from Functions import functions
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, DELFT_PATH
from starlette.websockets import WebSocketDisconnect

router = APIRouter()
processes = {}

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
        return JSONResponse({ "status": "running" if info["status"] == "running" else "finished",
            "progress": info["progress"], "logs": info["logs"] })
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
    bat_path = os.path.normpath(os.path.join(DELFT_PATH, "dflowfm/scripts/run_dflowfm.bat"))
    mdu_path = os.path.join(path, "FlowFM.mdu")
    if not os.path.exists(bat_path) or not os.path.exists(mdu_path):
        return JSONResponse({"status": "error", "message": "Executable or MDU file not found."})
    command = [bat_path, "--autostartstop", mdu_path]
    # Run the process
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
        errors="replace", text=True, shell=True, bufsize=1, cwd=path
    )
    processes[project_name] = {"process": process, "progress": 0, "logs": [], "status": "running"}
    def safe_append(project, text):
        """Helper function to safely append logs."""
        if project in processes:
            logs = processes[project]["logs"]
            logs.append(text)
            if len(logs) > 4000:
                processes[project]["logs"] = logs[-4000:]
    def stream_logs():
        progress_pattern = re.compile(
            r"(?P<sim_time_done>\d+d\s+\d+:\d+:\d+)\s+"
            r"(?P<sim_time_left>\d+d\s+\d+:\d+:\d+)\s+"
            r"(?P<real_time_used>\d+d\s+\d+:\d+:\d+)\s+"
            r"(?P<real_time_left>\d+d\s+\d+:\d+:\d+)\s+"
            r"\d+\s+"
            r"(?P<percent>\d+(?:\.\d+)?)%"
        )
        try:
            for line in process.stdout:
                line = line.strip()
                if not line: continue
                if project_name not in processes:
                    break  # Project was removed externally
                safe_append(project_name, line)
                # Catch error messages
                if "forrtl:" in line.lower():
                    safe_append(project_name, f"[ERROR] {line}")
                    processes[project_name]["status"] = "error"
                    process.kill()
                    break
                # Check for progress
                match = progress_pattern.search(line)
                if match and project_name in processes:
                    processes[project_name]["progress"] = float(match.group("complete"))
                    processes[project_name]["real_time_used"] = match.group("real_time_used")
                    processes[project_name]["real_time_left"] = match.group("real_time_left")
        finally:
            process.wait()
            if project_name not in processes:
                return  # Project removed during execution
            status = processes[project_name]["status"]
            if status != "error":
                processes[project_name]["status"] = "finished"
                try:
                    post_result = functions.postProcess(path)
                    msg = f"[FINISHED] {post_result['message']}" if post_result["status"] == "ok" else f"[ERROR] {post_result['message']}"
                    safe_append(project_name, msg)
                except Exception as e: safe_append(project_name, f"[POSTPROCESS FAILED] {str(e)}")
             # Clean up safely
            if project_name in processes:
                processes[project_name]["progress"] = 100
                safe_append(project_name, "[CLEANUP] Done.")
    threading.Thread(target=stream_logs, daemon=True).start()
    return JSONResponse({"status": "ok", "message":  f"Simulation {project_name} started."})

@router.websocket("/sim_progress_hyd/{project_name}")
async def sim_progress_hyd(websocket: WebSocket, project_name: str):
    await websocket.accept()
    try:
        last_log, last_progress = 0, None
        while True:
            info = processes.get(project_name)
            if not info:
                await websocket.send_text("[ERROR] No such simulation.")
                break
            logs = info["logs"]
            # Send new logs to the client
            while last_log < len(logs):
                msg = logs[last_log]
                await websocket.send_text(msg[:4000])  # Limit message size
                last_log += 1
            # Send progress to the client if it has changed
            if info["progress"] != last_progress:
                last_progress = info["progress"]
                real_used = info.get("real_time_used", "N/A")
                real_left = info.get("real_time_left", "N/A")
                await websocket.send_text(f"[PROGRESS] {last_progress:.2f}|{real_used}|{real_left}")
            if info["status"] != "running":
                await websocket.send_text(f"[FINISHED] Simulation {info['status']}.")
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect: pass
    finally:
        # Clean up if the simulation is finished
        if project_name in processes and processes[project_name]["status"] != "running":
            del processes[project_name]
            
