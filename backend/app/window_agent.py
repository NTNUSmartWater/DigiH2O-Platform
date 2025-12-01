from fastapi import FastAPI
import subprocess, uvicorn, os, traceback, threading, re

app = FastAPI()
processes = {}


def append_log(log_file, line):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding="utf-8", errors="replace") as f:
        f.write(line + "\n")

def kill_process(process):
    try:
        # Try terminate
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill for Windows
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "ok", "message": "Simulation stopped."}
    except Exception as e: 
        return {"status": "error", "message": str(e)}


# ---- Run Grid Tool ----
def run_grid_tool(path):
    subprocess.Popen([path], shell=False)

# ---- Run Hydro Simulation ----
def run_hyd_sim(path_bat, mdu_path, project_name, log_file, cwd, percent_re, time_re):
    processes[project_name] = {"process": process, "progress": 0.0, 
        "real_time_used": "N/A", "real_time_left": "N/A", "logs": [], "status": "running"}
    # Open log
    append_log(log_file, "[START] Running simulation...")
    process = subprocess.Popen( [path_bat, "--autostartstop", mdu_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, shell=True, encoding="utf-8", errors="replace", bufsize=1, cwd=cwd
    )
    processes[project_name]["process"] = process
    # Stream logs
    try:
        for line in process.stdout:
            if not line: continue
            line = line.strip()
            append_log(log_file, line)
            processes[project_name]["logs"].append(line)
            # Catch error messages
            if "forrtl:" in line.lower():
                processes[project_name]["status"] = "error"
                append_log(log_file, f"[ERROR] {line}")
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
            append_log(log_file, "[END] Simulation completed.")
        else: append_log(log_file, "[END] Simulation failed.")
        append_log(log_file, "[CLEANUP] Done.")
        processes[project_name]["progress"] = 100.0

def run_waq_sim(cmd, project_name, cwd, websocket, progress_regex, stop_on_error):
    processes[project_name] = {"progress": 0, "logs": [], "status": "running", "process": None, "stopped": False}
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, bufsize=1,
        universal_newlines=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    processes[project_name]["process"], success = process, False
    try:
        while True:
            # Check if simulation is stopped
            if processes[project_name]["status"] == "stopped":
                res = kill_process(process)
                # await websocket.send_json({"status": res["message"]})                
                return False
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None: break
                # await asyncio.sleep(0.1)
                continue
            line = line.strip()
            if not line: continue
            print("[OUT]", line)
            # Check for progress
            if progress_regex:
                match = progress_regex.search(line)
                if match:
                    percent = float(match.group(1))
                    processes[project_name]["progress"] = percent
                    # await websocket.send_json({"progress": percent})     
            # Check special errors
            if stop_on_error and stop_on_error in line:
                # if "ERROR in GMRES" in line: await websocket.send_json({"error": "GMRES solver failed.\nConsider increasing the maximum number of iterations."})
                # await websocket.send_json({"error": f"Error detected: {line}"})
                kill_process(process)
                processes[project_name]["status"] = "error"
                return False
            if "Normal end" in line: success = True
        for line in process.stderr:
            if not line.strip(): continue
            print("[ERR]", line.strip())
            # await websocket.send_json({"error": line.strip()}) 
    finally:
        process.stdout.close()
        process.stderr.close()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: kill_process(process)
        if process.poll() is None: kill_process(process)
    return success






@app.post("/run")
async def run_program(data: dict):
    action = data.get("action")
    if action == "run_grid_tool":
        path = data.get("path")
        if not os.path.exists(path): return {"status": "error", "message": "GridTool not found"}
        threading.Thread(target=run_grid_tool, args=(path,), daemon=True).start()
        return {"status": "ok"}
    if action == "run_hyd":
        bat_path, mdu_path, cwd_path = data.get("bat_path"), data.get("mdu_path"), data.get("cwd_path")
        log_path, project_name = data.get("log_path"), data.get("project_name")
        percent_re, time_re = re.compile(data.get("percent_re")), re.compile(data.get("time_re"))
        threading.Thread(target=run_hyd_sim, args=(bat_path, mdu_path, project_name, 
            log_path, cwd_path, percent_re, time_re), daemon=True).start()
        return {"status": "ok", "message": "Simulation started"}
    if action == "run_waq":
        cmd, project_name = data.get("cmd"), data.get("project_name")
        cwd, websocket = data.get("cwd"), data.get("websocket")
        progress_regex = re.compile(data.get("progress_regex"))
        stop_on_error = data.get("stop_on_error")
        threading.Thread(target=run_waq_sim, args=(cmd, project_name, 
            cwd, websocket, progress_regex, stop_on_error), daemon=True).start()
        return {"status": "ok", "message": "Simulation started"}
    return {"status": "error", "message": "Unknown action"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5055)
