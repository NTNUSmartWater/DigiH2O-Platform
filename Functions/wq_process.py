import os, subprocess, asyncio, re, shutil
import pandas as pd, numpy as np
from fastapi import APIRouter, Request, WebSocket
from config import PROJECT_STATIC_ROOT
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from Functions import wq_functions
from starlette.websockets import WebSocketDisconnect

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
        data = wq_functions.hydReader(path)
        status, message = 'ok', ""
    return JSONResponse({"status": status, "message": message, "content": data})

@router.post("/wq_time")
async def wq_time(request: Request):
    body = await request.json()
    load_data, time_data, key, folder = body.get('loadsData'), body.get('timeData'), body.get('key'), body.get('folderName')
    # Check whether the location in time-series is in the load data
    loads = [x[0] for x in load_data]
    times = [x[1] for x in time_data]
    if not any(x in times for x in loads):
        return JSONResponse({"status": 'error', "message": 'Error: No Location/Substance found in the table.'})
    try:
        # Read file and prepare data
        time_data = np.array(time_data)
        idx = [datetime.fromtimestamp(int(x)/1000.0, tz=timezone.utc) for x in time_data[:, 0]]
        df = pd.DataFrame(time_data[:, 1:], index=idx, columns=['source', 'substance', 'value'])
        # Sort data
        df = df.sort_index(ascending=True)
        status, message, data = 'ok', "", None
        # Structure data
        groups = df.groupby(['source'])
        if len(groups) == 0: return JSONResponse({"status": 'error', "content": data,
                "message": 'The inputed time-series data No Location/Substance found in the table.'})
        result = []
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
            elif key == 'tracer-metals': from_ = ['ASWTOT', 'CUWTOT', 'NIWTOT', 'PBWTOT', 'POCW', 'AOCW', 'DOCW', 'SSW', 'ZNWTOT',
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
            temp_df = temp_df.sort_index(ascending=True)
            temp_df = temp_df.fillna(-999)
            temp_df.index = [x.strftime('%Y/%m/%d-%H:%M:%S') for x in temp_df.index]
            temp_df.reset_index(inplace=True)
            lst = temp_df.astype(str).values.tolist() # Convert to string
            lst = [' '.join(x) for x in lst]
            temp += lst
            result.append('\n'.join(temp))
        status, message, data, to_ = 'ok', "", '\n\n\n'.join(result), gr_substance
    except Exception as e:
        status, message, data, from_, to_ = 'error', f"Error: {str(e)}", None, None, None
    return JSONResponse({"status": status, "message": message, "content": data, "froms": from_, "tos": to_})

@router.websocket("/run_wq")
async def run_wq(websocket: WebSocket):
    await websocket.accept()
    try:
        # Get parameters from frontend
        body = await websocket.receive_json()
        project_name, key = body['projectName'], body['key']
        file_name, time_data, usefors = body['folderName'], body['timeTable'], body['usefors']
        t_start = datetime.fromtimestamp(int(body['startTime']/1000.0), tz=timezone.utc)
        t_stop = datetime.fromtimestamp(int(body['stopTime']/1000.0), tz=timezone.utc)
        hyd_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "DFM_DELWAQ", body['hydName'])
        hyd_folder = os.path.dirname(hyd_path)
        sal_path, attr_path = os.path.join(hyd_folder, body['salPath']), os.path.join(hyd_folder, body['attrPath'])
        vol_path, ptr_path = os.path.join(hyd_folder, body['volPath']), os.path.join(hyd_folder, body['ptrPath'])
        area_path, flow_path = os.path.join(hyd_folder, body['areaPath']), os.path.join(hyd_folder, body['flowPath'])
        length_path, srf_path = os.path.join(hyd_folder, body['lengthPath']), os.path.join(hyd_folder, body['srfPath'])
        vdf_path, tem_path = os.path.join(hyd_folder, body['vdfPath']), os.path.join(hyd_folder, body['temPath'])
        wq_folder = os.path.join(PROJECT_STATIC_ROOT, project_name, "WAQ")
        os.makedirs(wq_folder, exist_ok=True)
        # Clear data if exists
        output_folder = os.path.join(wq_folder, file_name)
        if os.path.exists(output_folder): shutil.rmtree(output_folder, ignore_errors=True)
        os.makedirs(output_folder, exist_ok=True)
        # Prepare input files
        await websocket.send_json({"status": "Preparing inputs for WAQ simulation..."})
        parameters = {'hyd_path': hyd_path, "t_start": t_start, "t_stop": t_stop, 'sal_path': sal_path,
            "maxiter": body['maxiter'], "tolerance": body['tolerance'], "scheme": body['scheme'], 'srf_path': srf_path, 
            "t_step1": body['timeStep1'], "t_step2": body['timeStep2'], "obs_data": body['obsPoints'],
            'n_segments': body['nSegments'], 'attr_path': attr_path, 'vol_path': vol_path, 'exchange_x': body['exchangeX'],
            'exchange_y': body['exchangeY'], 'exchange_z': body['exchangeZ'], 'folder_name': file_name,
            'ptr_path': ptr_path, 'area_path': area_path, 'flow_path': flow_path, 'length_path': length_path,
            'n_layers': body['nLayers'], 'sources': body['sources'], 'loads_data': body['loadsData'],
            'vdf_path': vdf_path, 'tem_path': tem_path, 'initial_list': body['initialList'], 'initial_set': body['initial'].split('\n')
        }
        includes_folder = os.path.join(output_folder, "includes_deltashell")
        os.makedirs(includes_folder, exist_ok=True)
        table_folder = os.path.join(includes_folder, "load_data_tables")
        os.makedirs(table_folder, exist_ok=True)
        # Write *.tbl file
        tbl_path = os.path.join(table_folder, f"{file_name}.tbl")
        with open(tbl_path, 'w', encoding='ascii', newline='\n') as f:
            f.write(time_data)
        # Write *.usefors file
        usefor_path = os.path.join(table_folder, f"{file_name}.usefors")
        with open(usefor_path, 'w', encoding='ascii', newline='\n') as f:
            f.write(usefors)
        # Prepare external inputs
        inp_file, ms = wq_functions.wqPreparation(parameters, key, output_folder, includes_folder)
        if not inp_file: 
            await websocket.send_json({'error': ms})
            return
        # Run WAQ simulation
        delwaq1_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/bin/delwaq1.exe'
        delwaq2_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/bin/delwaq2.exe'
        bloom_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/default/bloom.spe'
        proc_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/default/proc_def.def'
        paths_to_check = [ delwaq1_path, delwaq2_path, proc_path, bloom_path ]
        # Check if all paths exist and are valid to run the simulation
        for path in paths_to_check:
            if not os.path.exists(path): await websocket.send_json({'error': f"File not found: {path}"})
            if not os.access(path, os.R_OK): await websocket.send_json({'error': f"No read permission: {path}"})
        delwaq1_path, delwaq2_path = os.path.normpath(delwaq1_path), os.path.normpath(delwaq2_path)
        proc_path, bloom_path = os.path.normpath(proc_path), os.path.normpath(bloom_path)
        # Add dll path
        dll_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/share/bin'
        os.environ["PATH"] += os.pathsep + dll_path
        # Run Simulation and get output
        inp_name = os.path.basename(inp_file)
        # === Run delwaq1 ===
        print('=== Run delwaq1 ===')
        await websocket.send_json({"status": "Running WAQ simulation..."})
        cmd = [delwaq1_path, inp_name, "-p", proc_path, "-eco", bloom_path]
        process1 = await subprocessRunner(cmd, output_folder, websocket)
        if not process1:
            await websocket.send_json({"error": "Prepare inputs failed."})
            return
        await websocket.send_json({"status": "Finished preparing inputs."})    
        # === Run delwaq2 ===
        print('=== Run delwaq2 ===')
        progress_pattern = re.compile(r"(\d+(?:\.\d+)?)% Completed")
        await websocket.send_json({"status": "Starting simulation..."})
        cmd, stop_on_error = [delwaq2_path, inp_name], "ERROR in GMRES"
        process2 = await subprocessRunner(cmd, output_folder, websocket, progress_pattern, stop_on_error)
        if not process2:
            await websocket.send_json({"status": "Run WAQ failed."})
            return
        await websocket.send_json({"progress": 100.0})
        print('=== Finished ===')
        # Move WAQ output files to output folder
        await websocket.send_json({"status": "Moving NC output files..."})
        output_folder = os.path.join(PROJECT_STATIC_ROOT, project_name, "output")
        if not os.path.exists(output_folder): os.makedirs(output_folder)
        output_WAQ_folder = os.path.join(output_folder, 'WAQ')
        if not os.path.exists(output_WAQ_folder): os.makedirs(output_WAQ_folder)
        for suffix in ["_his.nc", "_map.nc", ".json"]:
            src = os.path.join(output_folder, f"{file_name}{suffix}")
            if os.path.exists(src):
                shutil.copy(src, os.path.join(output_WAQ_folder, f"{file_name}{suffix}"))
        await websocket.send_json({"status": "NC files copied."})
        # Delete folder
        try: shutil.rmtree(wq_folder, ignore_errors=True)
        except Exception as e: await websocket.send_json({'error': str(e)})
        await websocket.send_json({"status": "Simulation completed successfully."})
    except WebSocketDisconnect: pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally: await websocket.close()

async def subprocessRunner(cmd, cwd, websocket, progress_regex=None, stop_on_error=None):
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, universal_newlines=True)
    success = False
    for line in process.stdout:
        line = line.strip()
        if not line: continue
        print("[OUT]", line)
        # Check for progress
        if progress_regex:
            match = progress_regex.search(line)
            if match:
                percent = float(match.group(1))
                await websocket.send_json({"progress": percent})
        # Check special errors
        if stop_on_error and stop_on_error in line:
            if "ERROR in GMRES" in line: await websocket.send_json({"error": "GMRES solver failed.\nConsider increasing the maximum number of iterations."})
            await websocket.send_json({"error": f"Error detected: {line}"})
            process.terminate()
            return False
        if "Normal end" in line: success = True
    for line in process.stderr:
        if not line.strip(): continue
        print("[ERR]", line.strip())
        await websocket.send_json({"error": line.strip()})    
    await asyncio.to_thread(process.wait)
    return success
