import os, subprocess, threading, asyncio
from fastapi import APIRouter, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT

router = APIRouter()
templates = Jinja2Templates(directory="static/templates")


@router.post("/check_project")
async def check_project(request: Request):
    body = await request.json()
    project_name = body.get('projectName')
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, "output")
    if os.path.exists(path): status = 'ok'
    else: status = 'error'
    return JSONResponse({"status": status})


def register_websocket_routes(app):
    @app.websocket("/run_sim/{project_name}")
    async def run_sim(websocket: WebSocket, project_name: str):
        await websocket.accept()
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        exe_path = "C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dflowfm/scripts/run_dflowfm.bat"
        if not os.path.exists(exe_path):
            # Send an error message to the client
            await websocket.send_text({f"[ERROR] Executable not found: {exe_path}"})
            await websocket.close()
            return
        mdu_path = os.path.join(path, "FlowFM.mdu")
        if not os.path.exists(mdu_path):
            # Send an error message to the client
            await websocket.send_text({f"[ERROR] MDU file not found: {mdu_path}"})
            await websocket.close()
            return
        exe_path, mdu_path = os.path.normpath(exe_path), os.path.normpath(mdu_path)
        command, working_dir = [exe_path, "--autostartstop", mdu_path], os.path.dirname(mdu_path)
        # Run the process
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
            errors="replace", text=True, shell=True, bufsize=1, cwd=working_dir
        )
        loop = asyncio.get_running_loop()
        def stream_logs(process, websocket: WebSocket):
            # Read the output of the process and send it to the client
            for line in process.stdout:
                coro = websocket.send_text(line.strip())
                asyncio.run_coroutine_threadsafe(coro, loop)
            process.wait()
        # Start a thread to read the output of the process
        threading.Thread(target=stream_logs, args=(process, websocket), daemon=True).start()
        # Wait for the process to finish
        return_code = await asyncio.to_thread(process.wait)
        # Send the return code to the client
        await websocket.send_text(f"[PROCESS EXITED] Code: {return_code}")
        # Close the connection
        await websocket.close()


# def main():
#     # # Run simulation
#     path_EXE = "C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dflowfm/scripts/run_dflowfm.bat"
#     path_MDU = "D:/Programming_Codes/Delft3D/folder/Test/FlowFM.mdu"
#     path_EXE, path_MDU = os.path.normpath(path_EXE), os.path.normpath(path_MDU)
#     command, working_dir = [path_EXE, "--autostartstop", path_MDU], os.path.dirname(path_MDU) 
#     # Get files before running simulation
#     files = os.listdir(os.path.dirname(path_MDU))
#     runSim.run(command, working_dir)
#     # Reorganize the data
#     parent_path = os.path.abspath(os.path.join(path_MDU, "..", ".."))
#     selected_files = [file for file in os.listdir(os.path.dirname(path_MDU)) if file not in files]
#     # # Move the files and folders
#     # for file in selected_files:
#     #     if os.path.isfile(os.path.join(parent_path, file)):
#     #         os.replace(os.path.join(parent_path, file), os.path.join(path_MDU, file))
#     #     elif os.path.isdir(os.path.join(parent_path, file)):
#     #         os.replace(os.path.join(parent_path, file), os.path.join(path_MDU, file))
#     # print(files)
#     # print(selected_files)
