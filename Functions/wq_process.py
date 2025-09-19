import os
from fastapi import APIRouter, Request
from config import PROJECT_STATIC_ROOT
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter()

@router.post("/select_hyd")
async def select_hyd(request: Request):
    body = await request.json()
    project_name = body.get('projectName')
    folder = [PROJECT_STATIC_ROOT, project_name, "DFM_DELWAQ", 'FlowFM.hyd']
    path = os.path.join(*folder)
    status, data = 'error', None
    message = f"Error: Cannot find .hyd file in project '{project_name}'.\nPlease run a hydrodynamic simulation first."
    if os.path.exists(path):
        # Read file
        data, sources, check = {'filename': 'FlowFM.hyd'}, [], False
        with open(path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if "number-hydrodynamic-layers" in line: data['n_layers'] = line.split()[1]
            if "reference-time" in line:
                temp = line.split()[1].replace("'", "")
                dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
                data['ref_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            if "hydrodynamic-start-time" in line:
                temp = line.split()[1].replace("'", "")
                dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
                data['start_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            if "hydrodynamic-stop-time" in line:
                temp = line.split()[1].replace("'", "")
                dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
                data['stop_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            if line.strip() == "sink-sources":
                check = True; continue
            if line.strip() == "end-sink-sources": check = False
            if check: 
                temp = line.split()
                sources.append([temp[-1], temp[-2], temp[-3]])
        data['sources'] = sources
        status, message = 'ok', ""
    return JSONResponse({"status": status, "message": message, "content": data})

@router.post("/run_wq")
async def run_wq(request: Request):
    body = await request.json()
    project_name, key = body.get('projectName'), body.get('key')
    hyd_name, file_name = body.get('hydName'), body.get('fileName')
    ref_time, start_time, stop_time = body.get('refTime'), body.get('startTime'), body.get('stopTime')
    t_ref = datetime.fromtimestamp(int(ref_time)/1000.0, tz=timezone.utc)
    t_start = datetime.fromtimestamp(int(start_time)/1000.0, tz=timezone.utc)
    t_stop = datetime.fromtimestamp(int(stop_time)/1000.0, tz=timezone.utc)
    try:
        wq_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "WAQ")
        if not os.path.exists(wq_path): os.makedirs(wq_path)
        file_path = os.path.join(wq_path, file_name)
        if not os.path.exists(file_path): os.makedirs(file_path)
        table_path = os.path.join(file_path, "tables")
        if not os.path.exists(table_path): os.makedirs(table_path)
        # Write *.tbl file


        # Write *.usefors file

        # if os.path.exists(path):
        #     # Read file
        #     data, sources, check = {'filename': 'FlowFM.hyd'}, [], False
        #     with open(path, 'r') as f:
        #         lines = f.readlines()
        #     for line in lines:
        #         if "number-hydrodynamic-layers" in line: data['n_layers'] = line.split()[1]
        #         if "reference-time" in line:
        #             temp = line.split()[1].replace("'", "")
        #             dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
        #             data['ref_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        #         if "hydrodynamic-start-time" in line:
        #             temp = line.split()[1].replace("'", "")
        #             dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
        #             data['start_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        #         if "hydrodynamic-stop-time" in line:                
        #             temp = line.split()[1].replace("'", "")
        #             dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
        #             data['stop_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        #         if line.strip() == "sink-sources":
        #             check = True; continue
        #         if line.strip() == "end-sink-sources": check = False
        #         if check: 
        #             temp = line.split()
        #             sources.append([temp[-1], temp[-2], temp[-3]])
        #     data['sources'] = sources

        # Move output files to output folder



        status, message = 'ok', "Simulation generated successfully."
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# # Run a water quality simulation
# @app.websocket("/run_wq/{project_name}")
# async def run_wq(websocket: WebSocket, project_name: str, sed_filename: str):
#     await websocket.accept()
#     path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
#     bat_path = "C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins\DeltaShell.Dimr/kernels/x64/dwaq/scripts/run_delwaq.bat"
#     sed_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input", 'wq', sed_filename)
#     WQ_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input", 'DFM_DELWAQ')
#     try:
#         if not os.path.exists(WQ_path):
#             await websocket.send_text({f"[ERROR] Directory not found: {WQ_path}"})
#             return
#         if not os.path.exists(bat_path):
#             await websocket.send_text({f"[ERROR] Executable not found: {bat_path}"})
#             return
#         if not os.path.exists(sed_path):
#             await websocket.send_text({f"[ERROR] Water quality file not found: {sed_filename}"})
#             return
#         bat_path, sed_path = os.path.normpath(bat_path), os.path.normpath(sed_path)
#         command = [bat_path, sed_path]
#         # Run the process
#         process = subprocess.Popen(
#             command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
#             errors="replace", text=True, shell=True, bufsize=1, cwd=path
#         )
#         processes[project_name] = process
#         loop = asyncio.get_running_loop()
#         def stream_logs(process, websocket: WebSocket):
#             try:
#                 # Read the output of the process and send it to the client
#                 for line in process.stdout:
#                     coro = websocket.send_text(line.strip())
#                     asyncio.run_coroutine_threadsafe(coro, loop)
#                 process.wait()
#             except Exception: pass
#         # Start a thread to read the output of the process
#         threading.Thread(target=stream_logs, args=(process, websocket), daemon=True).start()
#         # Wait for the process to finish
#         return_code = await asyncio.to_thread(process.wait)
#         # Send the return code to the client
#         if return_code == 0: 
#             await websocket.send_text("\n\n[STATUS] Simulation completed successfully.")
#             # data = functions.postProcess(working_dir)
#             # if data["status"] == "error": await websocket.send_text(f"[STATUS] Simulation ended with errors: {data['message']}")
#             # else: await websocket.send_text("\n\n[STATUS] Simulation completed successfully.")
#         else: await websocket.send_text(f"[STATUS] Simulation ended with errors: {return_code}.")
#     except WebSocketDisconnect: print(f"Client disconnected from project: '{project_name}'")
#     finally:
#         proc = processes.pop(project_name, None)
#         if proc and proc.poll() is None: proc.terminate()
#         if websocket.client_state.name != "DISCONNECTED":
#             try: await websocket.close()
#             except RuntimeError: pass