import os, subprocess, threading, asyncio
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

def register_websocket_routes(app):
    # Run a hydrodynamics simulation
    @app.websocket("/run_sim/{project_name}")
    async def run_sim(websocket: WebSocket, project_name: str):
        await websocket.accept()
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        bat_path = "C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dflowfm/scripts/run_dflowfm.bat"
        try:
            if not os.path.exists(bat_path):
                await websocket.send_text({f"[ERROR] Executable not found: {bat_path}"})
                return
            mdu_path = os.path.join(path, "FlowFM.mdu")
            if not os.path.exists(mdu_path):
                await websocket.send_text({f"[ERROR] MDU file not found: {mdu_path}"})
                return
            bat_path, mdu_path = os.path.normpath(bat_path), os.path.normpath(mdu_path)
            command = [bat_path, "--autostartstop", mdu_path]
            # Run the process
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
                errors="replace", text=True, shell=True, bufsize=1, cwd=path
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
            if return_code == 0:
                data = functions.postProcess(path)
                if data["status"] == "error": message = f"\n\n[STATUS] Error: {data['message']}."
                else: message = f"\n\n[STATUS] {data['message']}."
            else: message = f"\n\n[STATUS] Simulation ended with errors: {return_code}."
            try: await websocket.send_text(message)
            except WebSocketDisconnect: pass
        except WebSocketDisconnect: websocket.send_text(f"Client disconnected from project: '{project_name}'")
        finally:
            proc = processes.pop(project_name, None)
            if proc and proc.poll() is None: proc.terminate()
            if websocket.client_state.name != "DISCONNECTED":
                try: await websocket.close()
                except RuntimeError: pass

    # Stop simulation
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
