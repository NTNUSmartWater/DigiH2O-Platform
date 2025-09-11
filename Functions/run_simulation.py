import os, subprocess, threading, asyncio
from Functions import functions
from fastapi import APIRouter, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT
from starlette.websockets import WebSocketDisconnect

router = APIRouter()
templates = Jinja2Templates(directory="static/templates")
processes = {}

@router.post("/check_project")
async def check_project(request: Request):
    body = await request.json()
    project_name = body.get('projectName')
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input", "output")
    if os.path.exists(path): status = 'ok'
    else: status = 'error'
    return JSONResponse({"status": status})

def register_websocket_routes(app):
    @app.websocket("/run_sim/{project_name}")
    async def run_sim(websocket: WebSocket, project_name: str):
        await websocket.accept()
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        exe_path = "C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dflowfm/scripts/run_dflowfm.bat"
        try:
            if not os.path.exists(exe_path):
                await websocket.send_text({f"[ERROR] Executable not found: {exe_path}"})
                return
            mdu_path = os.path.join(path, "FlowFM.mdu")
            if not os.path.exists(mdu_path):
                await websocket.send_text({f"[ERROR] MDU file not found: {mdu_path}"})
                return
            exe_path, mdu_path = os.path.normpath(exe_path), os.path.normpath(mdu_path)
            command, working_dir = [exe_path, "--autostartstop", mdu_path], os.path.dirname(mdu_path)
            # Run the process
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
                errors="replace", text=True, shell=True, bufsize=1, cwd=working_dir
            )
            processes[project_name] = process
            loop = asyncio.get_running_loop()
            def stream_logs(process, websocket: WebSocket):
                try:
                    # Read the output of the process and send it to the client
                    for line in process.stdout:
                        coro = websocket.send_text(line.strip())
                        asyncio.run_coroutine_threadsafe(coro, loop)
                    process.wait()
                except Exception: pass
            # Start a thread to read the output of the process
            threading.Thread(target=stream_logs, args=(process, websocket), daemon=True).start()
            # Wait for the process to finish
            return_code = await asyncio.to_thread(process.wait)
            try:
                # Send the return code to the client
                if return_code == 0: 
                    data = functions.postProcess(working_dir)
                    if data["status"] == "error": await websocket.send_text(f"[STATUS] Simulation ended with errors: {data['message']}")
                    else: await websocket.send_text("\n\n[STATUS] Simulation completed successfully.")
                else: await websocket.send_text(f"[STATUS] Simulation ended with errors: {return_code}.")
            except WebSocketDisconnect: pass
        except WebSocketDisconnect: print(f"Client disconnected from project {project_name}")
        finally:
            proc = processes.pop(project_name, None)
            if proc and proc.poll() is None: proc.terminate()
            if websocket.client_state.name != "DISCONNECTED":
                try: await websocket.close()
                except RuntimeError: pass

    @router.post("/stop_sim")
    async def stop_sim(request: Request):
        body = await request.json()
        project_name = body.get('projectName')
        process = processes.get(project_name)
        if process and process.poll() is None:
            process.terminate()
            processes.pop(project_name, None)
            return JSONResponse({"status": "ok", "message": f"Simulation for project '{project_name}' stopped."})
        return JSONResponse({"status": "error", "message": "No running process found."})
