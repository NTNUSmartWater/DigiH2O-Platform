import os, subprocess, threading, re
from Functions import functions
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, DELFT_PATH

router, processes = APIRouter(), {}

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
    folder, key = body.get('folder'), body.get('key')
    if key == "hyd": path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, folder))
    elif key == "waq":
        waq_dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "WAQ"))
        if not os.path.exists(waq_dir): return JSONResponse({"status": 'error'})
        files = [f for f in os.listdir(waq_dir) if f.split('.')[0] == folder]
        if len(files) == 0: return JSONResponse({"status": 'error'})
        path = os.path.normpath(os.path.join(waq_dir, files[0]))
    status = 'ok' if os.path.exists(path) else 'error'
    return JSONResponse({"status": status})

# Check if simulation is running
@router.post("/check_sim_status_hyd")
async def check_sim_status_hyd(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name = functions.project_definer(body.get('projectName'), user)
    info, logs = processes.get(project_name), []
    if not info: 
        return JSONResponse({"status": "not_started", "progress": 0, "complete": 'Completed: --% [Used: N/A → Left: N/A]',
                         "time_used": "N/A", "time_left": "N/A", "logs": [], "message": ''})
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log_hyd.txt"))
    # Read log file
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            logs = f.read().splitlines()
    complete = f'Completed: {info["progress"]}% [Used: {info["time_used"]} → Left: {info["time_left"]}]'
    return JSONResponse({ "status": info["status"], "progress": info["progress"], "complete": complete,
        "time_used": info["time_used"], "time_left": info["time_left"], "logs": logs, "message": info["message"]})
    
# Start a hydrodynamic simulation
@router.post("/start_sim_hyd")
async def start_sim_hyd(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name = functions.project_definer(body.get('projectName'), user)
    redis = request.app.state.redis
    lock = redis.lock(f"{project_name}:sim_hyd", timeout=1000, blocking_timeout=10)
    async with lock:
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
        command = ["cmd.exe", "/c", bat_path, "--autostartstop", mdu_path]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1, cwd=path)
        processes[project_name] = {"process": process, "progress": 0.0, "status": "running", 
                                "time_used": "N/A", "time_left": "N/A", "logs": [], "message": ''}
        # Stream logs
        def stream_logs():
            try:
                for line in process.stdout:
                    line = line.strip()
                    if not line: continue
                    append_log(log_path, line)
                    # Catch error messages
                    if "forrtl:" in line.lower() or "error" in line.lower():
                        processes[project_name]["status"], processes[project_name]["message"] = "error", line
                        append_log(log_path, line)
                        res = functions.kill_process(process)
                        append_log(log_path, res["message"])
                    # Check for progress
                    match_pct = percent_re.search(line)
                    if match_pct: processes[project_name]["progress"] = float(match_pct.group("percent"))
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
                        processes[project_name]["message"] = 'Reorganizing outputs. Please wait...'
                        post_result = functions.postProcess(path)
                        if not post_result["status"] == "ok":
                            processes[project_name]["status"], processes[project_name]["message"] = "error", f"Exception: {str(e)}"
                        processes[project_name]["status"] = "finished"
                        processes[project_name]["message"] = f"Simulation completed successfully."
                    except Exception as e:
                        processes[project_name]["status"], processes[project_name]["message"] = "error", f"Exception: {str(e)}"
                processes[project_name]["progress"] = 100.0
                processes.pop(project_name, None)
        threading.Thread(target=stream_logs, daemon=True).start()
    return JSONResponse({"status": "ok", "message": f"Simulation {project_name} started on Windows host."})

@router.get("/sim_log_full/{project_name}")
async def sim_log_full(project_name: str, log_file: str = Query(""), user=Depends(functions.basic_auth)):
    project_name = functions.project_definer(project_name, user)
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, log_file))
    if not os.path.exists(log_path): return {"content": ""}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return {"content": content, "offset": os.path.getsize(log_path)}

@router.get("/sim_log_tail_hyd/{project_name}")
async def sim_log_tail_hyd(project_name: str, offset: int = Query(0), log_file: str = Query(""), user=Depends(functions.basic_auth)):
    project_name = functions.project_definer(project_name, user)
    log_path, lines = os.path.join(PROJECT_STATIC_ROOT, project_name, log_file), []
    if not os.path.exists(log_path): return {"lines": lines, "offset": offset}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        for line in f:
            lines.append(line.rstrip())
    return {"lines": lines, "offset": os.path.getsize(log_path)}