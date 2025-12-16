import os, subprocess, threading, asyncio, re
from Functions import functions
from fastapi import APIRouter, Request, WebSocket, Depends
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, DELFT_PATH, WINDOWS_AGENT_URL
from starlette.websockets import WebSocketDisconnect

router, processes = APIRouter(), {}
TEMP_LOGS: dict[str, str] = {}

# Utility: append to file log
def append_log(log_path, text):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8", errors="replace") as f:
        f.write(text.strip() + "\n")
        f.flush()

@router.post("/check_folder")
async def check_folder(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name = functions.project_definer(body.get('projectName'), user)
    folder = body.get('folder', [])
    if isinstance(folder, str): folder = [folder]
    path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, *folder))
    status = 'ok' if os.path.exists(path) else 'error'
    return JSONResponse({"status": status})

# Check if simulation is running
@router.post("/check_sim_status_hyd")
async def check_sim_status_hyd(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name = functions.project_definer(body.get('projectName'), user)
    info, logs = processes.get(project_name), []
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log_hyd.txt"))
    if info:
        # Read log file
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                logs = f.read().splitlines()
        complete = f'Completed: {info["progress"]}% [Used: {info["time_used"]} → Left: {info["time_left"]}]'
        return JSONResponse({ "status": info["status"], "progress": info["progress"], "complete": complete,
            "time_used": info["time_used"], "time_left": info["time_left"], "logs": logs})
    return JSONResponse({"status": "none"})

# Start a hydrodynamic simulation
@router.post("/start_sim_hyd")
async def start_sim_hyd(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name = functions.project_definer(body.get('projectName'), user)
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
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log_hyd.txt"))
    if os.path.exists(log_path): os.remove(log_path)
    percent_re = re.compile(r'(?P<percent>\d{1,3}(?:\.\d+)?)\s*%')
    time_re = re.compile(r'(?P<tt>\d+d\s+\d{1,2}:\d{2}:\d{2})')
    # Run the process
    # if request.app.state.env == 'development':
    # Run the process on host
    command = [bat_path, "--autostartstop", mdu_path]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", bufsize=1, cwd=path
    )
    processes[project_name] = {"process": process, "progress": 0.0, "status": "running", "logs": []}
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
                    append_log(log_path, line)
                    try: process.kill()
                    except: pass
                    break
                # Check for progress
                match_pct = percent_re.search(line)
                if match_pct: 
                    processes[project_name]["progress"] = float(match_pct.group("percent"))
                # Extract run time
                times = time_re.findall(line)
                if len(times) >= 4:
                    processes[project_name]["time_used"] = times[2]
                    processes[project_name]["time_left"] = times[3]
                elif len(times) == 3:
                    processes[project_name]["time_used"] = times[1]
                    processes[project_name]["time_left"] = times[2]
        finally:
            process.wait()
            status = processes[project_name]["status"]
            if status != "error":
                try:
                    processes[project_name]["status"] = "postprocessing"
                    post_result = functions.postProcess(path)
                    if not post_result["status"] == "ok": 
                        return JSONResponse({"status": "error", "message": f"Exception: {str(e)}"})
                except Exception as e: 
                    return JSONResponse({"status": "error", "message": f"Exception: {str(e)}"})
            # processes[project_name]["progress"] = 100.0
            processes.pop(project_name, None)
    threading.Thread(target=stream_logs, daemon=True).start()
    return JSONResponse({"status": "ok", "message": f"Simulation {project_name} started on Windows host."})
    # else: # Run the process on docker
    #     try:
    #         payload = {"action": "run_hyd", "bat_path": bat_path, "mdu_path": mdu_path, "project_name": project_name, 
    #                "log_path": log_path, "cwd_path": path, "percent_re": str(percent_re), "time_re": str(time_re)}
    #         res = requests.post(WINDOWS_AGENT_URL, json=payload, timeout=10)
    #         res.raise_for_status()
    #         return JSONResponse({"status": "ok", "message": f"Simulation {project_name} started (via Windows Agent)."})
    #     except Exception as e:
    #         return JSONResponse({"status": "error", "message": f"Exception: {str(e)}"})

@router.get("/sim_log_full/{project_name}")
async def sim_log_full(project_name: str, user=Depends(functions.basic_auth)):
    project_name = functions.project_definer(project_name, user)
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log_hyd.txt"))
    if not os.path.exists(log_path): return {"content": ""}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return {"content": content}

@router.get("/sim_log_tail/{project_name}")
async def sim_log_tail(project_name: str, user=Depends(functions.basic_auth)):
    project_name = functions.project_definer(project_name, user)
    log_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "log_hyd.txt")
    if not os.path.exists(log_path): return {"lines": [], "finished": False}
    last_pos, lines = TEMP_LOGS.get(project_name, 0), []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(last_pos)
        for line in f:
            lines.append(line.rstrip())
        TEMP_LOGS[project_name] = f.tell()
    info = processes.get(project_name)
    finished = info is None or info.get("status") == "finished"
    if finished: TEMP_LOGS.pop(project_name, None)
    return {"lines": lines, "finished": finished}



# @router.get("/sim_temp_log/{project_name}")
# async def sim_temp_log(project_name: str, user=Depends(functions.basic_auth)):
#     project_name = functions.project_definer(project_name, user)
#     content = TEMP_LOGS.get(project_name)
#     return {"content": content}

# @router.websocket("/sim_progress_hyd/{project_name}")
# async def sim_progress_hyd(websocket: WebSocket, project_name: str):
#     await websocket.accept()
#     try:
#         auth_header = websocket.headers.get("authorization")
#         user = functions.basic_auth_ws(auth_header)
#         if not user:
#             # TEMP_LOGS[project_name] = "[ERROR] Unauthorized"
#             await websocket.close(code=1008)
#             return
#         project_name = functions.project_definer(project_name, user)
#         wait = 0
#         log_path, last_pos = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log_hyd.txt")), 0
#         while True:
#             info = processes.get(project_name)
#             if not info:
#                 wait += 1
#                 if wait > 30:
#                     TEMP_LOGS[project_name] = "[ERROR] Simulation not found."
#                     break
#                 # TEMP_LOGS[project_name] = "[INFO] Waiting for simulation..."
#                 # await asyncio.sleep(1)
#                 # continue
#             # Send new logs to the client
#             if os.path.exists(log_path):

#                 with open(log_path, "r", encoding="utf-8", errors="replace") as f:
#                     f.seek(last_pos)
#                     for line in f:
#                         TEMP_LOGS[project_name] = line.strip()
#                     last_pos = f.tell()
#             TEMP_LOGS[project_name] = f"[PROGRESS] {info['progress']:.2f}|{info['real_time_used']}|{info['real_time_left']}"
#             if info["status"] == "postprocessing": 
#                 TEMP_LOGS[project_name] = "[POSTPROCESS] Reorganizing outputs. Please wait..."
#             if info["status"] == "finished":
#                 TEMP_LOGS[project_name] = "[FINISHED] Simulation finished."
#                 break
#             await asyncio.sleep(1)
#     except WebSocketDisconnect: pass
#     finally:
#         await asyncio.sleep(2)
#         TEMP_LOGS.pop(project_name, None)
#         await websocket.close()