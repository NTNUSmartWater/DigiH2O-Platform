import os, subprocess, asyncio, re, shutil
import pandas as pd, numpy as np, xarray as xr
from fastapi import APIRouter, Request, WebSocket
from config import PROJECT_STATIC_ROOT, DELFT_PATH
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from Functions import wq_functions
from starlette.websockets import WebSocketDisconnect

router, processes = APIRouter(), {}

def path_process(full_path:str, head:int=3, tail:int=2):
    parts  = full_path.split('/')
    if len(parts) <= head + tail: return full_path
    return '/'.join(parts[:head]) + '/ ... /' + '/'.join(parts[-tail:])

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

@router.post("/select_hyd")
async def select_hyd(request: Request):
    body = await request.json()
    project_name = body.get('projectName')
    folder = [PROJECT_STATIC_ROOT, project_name, "DFM_DELWAQ", 'FlowFM.hyd']
    path = os.path.normpath(os.path.join(*folder))
    if os.path.exists(path):
        return JSONResponse({"status": 'ok', "content": wq_functions.hydReader(path)})
    message = f"Error: Cannot find .hyd file in project '{project_name}'.\nPlease run a hydrodynamic simulation first."
    return JSONResponse({"status": 'error', "message": message})

@router.post("/wq_time")
async def wq_time(request: Request):
    try:
        body = await request.json()
        load_data, time_data, key, folder = body.get('loadsData'), body.get('timeData'), body.get('key'), body.get('folderName')
        # Check whether the location in time-series is in the load data
        loads, times = [x[0] for x in load_data], [x[1] for x in time_data]
        if not any(x in times for x in loads):
            return JSONResponse({"status": 'error', 
                "message": 'Error: No Location found in the table.\nThe field "Location" has to be defined in the table "List of Loads".'})        
        # Read file and prepare data
        time_data = np.array(time_data)
        idx = [datetime.fromtimestamp(int(x)/1000.0, tz=timezone.utc) for x in time_data[:, 0]]
        df = pd.DataFrame(time_data[:, 1:], index=idx, columns=['source', 'substance', 'value'])
        # Sort data
        df = df.sort_index(ascending=True)
        # Structure data
        groups, result = df.groupby(['source']), []
        if len(groups) == 0: return JSONResponse({"status": 'error',
                "message": 'The inputed time-series data is not found in the table.'})
        for name, group in groups:
            if (len(group) == 0 or name[0] not in loads): continue
            gr_substance = [x[0][0] for x in group.groupby(['substance'])]
            subs = ' '.join(f"'{x}'" for x in gr_substance)
            temp = ["DATA_ITEM", name[0], "CONCENTRATIONS",
                f"INCLUDE 'includes_deltashell\\load_data_tables\\{folder}.usefors'",
                "TIME LINEAR DATA", subs]
            if key == 'simple-oxygen': from_ = ['NH4', 'CBOD5', 'OXY', 'SOD']
            elif key == 'oxygen-bod-water': from_ = ['OXY', 'CBOD5']
            elif key == 'cadmium': from_ = ['IM1', 'Cd', 'IM1S1', 'CdS1']
            elif key == 'eutrophication': from_ = ['A', 'DP', 'NORG', 'NH4', 'NO3']
            elif key == 'trace-metals': from_ = ['ASWTOT', 'CUWTOT', 'NIWTOT', 'PBWTOT', 'POCW', 'AOCW', 'DOCW', 'SSW', 'ZNWTOT',
                        'ASREDT', 'ASSTOT', 'ASSUBT', 'CUREDT', 'CUSTOT', 'CUSUBT', 'NIREDT', 'NISTOT', 'NISUBT',
                        'PBREDT', 'PBSTOT', 'PBSUBT', 'DOCB', 'DOCSUB', 'POCB', 'POCSUB', 'S', 'ZNREDT', 'ZNSTOT', 'ZNSUBT']
            elif key == 'conservative-tracers': from_ = ['cTR1', 'cTR2', 'cTR3', 'dTR1', 'dTR2', 'dTR3']
            elif key == 'suspend-sediment': from_ = ['IM1', 'IM2', 'IM3', 'IM1S1', 'IM2S1', 'IM3S1']
            elif key == 'coliform': from_ = ['Salinity', 'EColi']
            # Assign data
            temp_df = pd.DataFrame()
            for item in gr_substance:
                subset = group[group['substance'] == item].copy()
                subset.index = pd.to_datetime(subset.index)
                temp_df[item] = pd.to_numeric(subset.value, errors="coerce")
            temp_df = temp_df.sort_index(ascending=True).fillna(-999)
            temp_df.index = [x.strftime('%Y/%m/%d-%H:%M:%S') for x in temp_df.index]
            temp_df.reset_index(inplace=True)
            lst = temp_df.astype(str).values.tolist() # Convert to string
            lst = [' '.join(x) for x in lst]
            temp += lst
            result.append('\n'.join(temp))
        return JSONResponse({"status": 'ok',"content": '\n\n\n'.join(result), "froms": from_, "tos": gr_substance})
    except Exception as e:
        return JSONResponse({"status": 'error', "message":  f"Error: {str(e)}"})

# Check if simulation is running
@router.post("/check_sim_status_waq")
async def check_sim_status_waq(request: Request):
    body = await request.json()
    project_name = body.get("projectName")
    if project_name in processes:
        info = processes[project_name]
        status = "stopped" if info.get("stopped") else info.get("status", "none")
        return JSONResponse({ "status": status,
            "progress": info.get("progress", 0), "logs": info.get("logs", [])
        })
    return JSONResponse({"status": "none", "progress": 0, "logs": []})

@router.websocket("/sim_progress_waq/{project_name}")
async def sim_progress_waq(websocket: WebSocket, project_name: str):
    await websocket.accept()        
    body = await websocket.receive_json()
    if project_name in processes and processes[project_name]["status"] == "running":
        await websocket.send_json({"error": "Simulation for this project is already running."})
        return
    processes[project_name] = {"progress": 0, "logs": [], "status": "running", "process": None, "stopped": False}
    try:
        key, file_name, time_data, usefors = body['key'], body['folderName'], body['timeTable'], body['usefors']
        t_start = datetime.fromtimestamp(int(body['startTime']/1000.0), tz=timezone.utc)
        t_stop = datetime.fromtimestamp(int(body['stopTime']/1000.0), tz=timezone.utc)
        hyd_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "DFM_DELWAQ", body['hydName']))
        hyd_folder = os.path.dirname(hyd_path)
        sal_path, attr_path = os.path.normpath(os.path.join(hyd_folder, body['salPath'])), os.path.normpath(os.path.join(hyd_folder, body['attrPath']))
        vol_path, ptr_path = os.path.normpath(os.path.join(hyd_folder, body['volPath'])), os.path.normpath(os.path.join(hyd_folder, body['ptrPath']))
        area_path, flow_path = os.path.normpath(os.path.join(hyd_folder, body['areaPath'])), os.path.normpath(os.path.join(hyd_folder, body['flowPath']))
        length_path, srf_path = os.path.normpath(os.path.join(hyd_folder, body['lengthPath'])), os.path.normpath(os.path.join(hyd_folder, body['srfPath']))
        vdf_path, tem_path = os.path.normpath(os.path.join(hyd_folder, body['vdfPath'])), os.path.normpath(os.path.join(hyd_folder, body['temPath']))
        wq_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "WAQ"))
        os.makedirs(wq_folder, exist_ok=True)
        # Clear data if exists
        output_folder = os.path.normpath(os.path.join(wq_folder, file_name))
        if os.path.exists(output_folder): shutil.rmtree(output_folder, ignore_errors=True)
        os.makedirs(output_folder, exist_ok=True)
        parameters = {'hyd_path': hyd_path, "t_start": t_start, "t_stop": t_stop, 'sal_path': sal_path,
            "maxiter": body['maxiter'], "tolerance": body['tolerance'], "scheme": body['scheme'], 'srf_path': srf_path, 
            "t_step1": body['timeStep1'], "t_step2": body['timeStep2'], "obs_data": body['obsPoints'],
            'n_segments': body['nSegments'], 'attr_path': attr_path, 'vol_path': vol_path, 'exchange_x': body['exchangeX'],
            'exchange_y': body['exchangeY'], 'exchange_z': body['exchangeZ'], 'folder_name': file_name,
            'ptr_path': ptr_path, 'area_path': area_path, 'flow_path': flow_path, 'length_path': length_path,
            'n_layers': body['nLayers'], 'sources': body['sources'], 'loads_data': body['loadsData'],
            'vdf_path': vdf_path, 'tem_path': tem_path, 'initial_list': body['initialList'], 'initial_set': body['initial'].split('\n')
        }
        includes_folder = os.path.normpath(os.path.join(output_folder, "includes_deltashell"))
        os.makedirs(includes_folder, exist_ok=True)
        table_folder = os.path.normpath(os.path.join(includes_folder, "load_data_tables"))
        os.makedirs(table_folder, exist_ok=True)
        # Write *.tbl file
        tbl_path = os.path.normpath(os.path.join(table_folder, f"{file_name}.tbl"))
        with open(tbl_path, 'w', encoding='ascii', newline='\n') as f:
            f.write(time_data)
        # Write *.usefors file
        usefor_path = os.path.normpath(os.path.join(table_folder, f"{file_name}.usefors"))
        with open(usefor_path, 'w', encoding='ascii', newline='\n') as f:
            f.write(usefors)
        # Prepare external inputs
        inp_file, ms = wq_functions.wqPreparation(parameters, key, output_folder, includes_folder)
        if not inp_file:
            await websocket.send_json({'error': ms})
            return
        # Run WAQ simulation
        delwaq1_path = os.path.normpath(os.path.join(DELFT_PATH, 'dwaq/bin/delwaq1.exe'))
        delwaq2_path = os.path.normpath(os.path.join(DELFT_PATH, 'dwaq/bin/delwaq2.exe'))
        bloom_path = os.path.normpath(os.path.join(DELFT_PATH, 'dwaq/default/bloom.spe'))
        proc_path = os.path.normpath(os.path.join(DELFT_PATH, 'dwaq/default/proc_def.def'))
        paths_to_check = [ delwaq1_path, delwaq2_path, proc_path, bloom_path ]
        # Check if all paths exist and are valid to run the simulation
        for path in paths_to_check:
            if not os.path.exists(path):
                await websocket.send_json({'error': f"File not found: {path_process(path)}"})
                processes[project_name]["status"] = "finished"
                return
            if not os.access(path, os.R_OK):
                await websocket.send_json({'error': f"No read permission: {path_process(path)}"})
                processes[project_name]["status"] = "finished"
                return
        # Add dll path
        dll_path = os.path.normpath(os.path.join(DELFT_PATH, 'share/bin'))
        os.environ["PATH"] += os.pathsep + dll_path
        # Run Simulation and get output
        inp_name = os.path.basename(inp_file)
        progress_regex = re.compile(r"(\d+(?:\.\d+)?)% Completed")
        # if websocket.app.state.env == "development":
        # === Run delwaq1 ===
        await websocket.send_json({'status': "Checking inputs for WAQ simulation..."})
        print('=== Run delwaq1 ===')
        cmd1 = [delwaq1_path, inp_name, "-p", proc_path, "-eco", bloom_path]
        ok1 = await subprocessRunner(cmd1, output_folder, websocket, project_name)
        if not ok1:
            await websocket.send_json({'error': "Prepare inputs failed."})
            processes[project_name]["status"] = "finished"
            return
        # === Run delwaq2 ===
        await websocket.send_json({'status': "Running WAQ simulation..."})
        print('=== Run delwaq2 ===')
        cmd2 = [delwaq2_path, inp_name]
        ok2 = await subprocessRunner(cmd2, output_folder, websocket, project_name, progress_regex, "ERROR in GMRES")
        if not ok2:
            await websocket.send_json({'error': "Run failed."})
            processes[project_name]["status"] = "finished"
            return
        print('=== Finished ===')
        # Move WAQ output files to output folder
        await websocket.send_json({'status': "Reorganizing output files ..."})
        try:
            output_dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "output"))
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            output_WAQ_dir = os.path.normpath(os.path.join(output_dir, 'WAQ'))
            if not os.path.exists(output_WAQ_dir): os.makedirs(output_WAQ_dir)
            for suffix in ["_his.nc", "_map.nc", ".json"]:
                filename = f"{file_name}{suffix}"
                src = os.path.normpath(os.path.join(output_folder, filename))
                if os.path.exists(src):
                    if suffix == ".json": shutil.copy(src, os.path.normpath(os.path.join(output_WAQ_dir, filename)))
                    else: # Convert .nc files to .zarr
                        ds = xr.open_dataset(src, chunks={'nTimesDlwq': 1})
                        zarr_path = os.path.normpath(os.path.join(output_WAQ_dir, filename.replace('.nc', '.zarr')))
                        ds.to_zarr(zarr_path, mode='w', consolidated=True)
                        ds.close()
                        os.remove(src) # Delete .nc files
            # Delete folder
            if os.path.exists(wq_folder): shutil.rmtree(wq_folder, ignore_errors=True)
        except Exception as e: await websocket.send_json({'status': str(e)})
        processes[project_name]["status"] = "finished"
        await websocket.send_json({'status': "Simulation completed successfully."})
    except WebSocketDisconnect: pass
    finally:
        if project_name in processes and not processes[project_name].get("stopped", False):
            processes.pop(project_name, None)
        elif project_name in processes and processes[project_name].get("stopped", False):
            await asyncio.sleep(2)
            processes.pop(project_name, None)

async def subprocessRunner(cmd, cwd, websocket, project_name, progress_regex=None, stop_on_error=None):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd, bufsize=1,
                                universal_newlines=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    processes[project_name]["process"], success = process, False
    try:
        while True:
            # Check if simulation is stopped
            if processes[project_name]["status"] == "stopped":
                res = kill_process(process)
                await websocket.send_json({"status": res["message"]})                
                return False
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None: break
                await asyncio.sleep(0.1)
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
                    await websocket.send_json({"progress": percent})     
            # Check special errors
            if stop_on_error and stop_on_error in line:
                if "ERROR in GMRES" in line: await websocket.send_json({"error": "GMRES solver failed.\nConsider increasing the maximum number of iterations."})
                await websocket.send_json({"error": f"Error detected: {line}"})
                kill_process(process)
                processes[project_name]["status"] = "error"
                return False
            if "Normal end" in line: success = True
        for line in process.stdout:
            if not line.strip(): continue
            print("[ERR]", line.strip())
            await websocket.send_json({"error": line.strip()}) 
    finally:
        process.stdout.close()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: kill_process(process)
        if process.poll() is None: kill_process(process)
    return success

# async def subprocessRunner(cmd, cwd, websocket, project_name, progress_regex=None, stop_on_error=None):
#     process = await asyncio.create_subprocess_exec(
#         *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=cwd)
#     try:
#         processes[project_name]["process"], success = process, False
#         while True:
#             # Check if simulation is stopped
#             if processes[project_name]["status"] == "stopped":
#                 process.kill()
#                 await websocket.send_json({"status": "Simulation stopped."})
#                 return False
#             line = await process.stdout.readline()
#             if not line:
#                 if process.returncode is not None: break
#                 await asyncio.sleep(0.05)
#                 continue
#             line = line.decode().strip()
#             if not line: continue
#             print("[OUT]", line)
#             # Check for progress
#             if progress_regex:
#                 match = progress_regex.search(line)
#                 if match:
#                     percent = float(match.group(1))
#                     processes[project_name]["progress"] = percent
#                     await websocket.send_json({"progress": percent})     
#             # Check special errors
#             if stop_on_error and stop_on_error in line:
#                 if "ERROR in GMRES" in line: await websocket.send_json({"error": "GMRES solver failed.\nConsider increasing the maximum number of iterations."})
#                 await websocket.send_json({"error": f"Error detected: {line}"})
#                 processes[project_name]["status"] = "error"
#                 process.kill()
#                 return False
#             if "Normal end" in line: success = True
#         return success
#     finally:
#         if process.returncode is None: process.kill()