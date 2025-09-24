import os, subprocess, asyncio, re, shutil
import pandas as pd, numpy as np
from fastapi import APIRouter, Request, WebSocket
from config import PROJECT_STATIC_ROOT
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from Functions import wq_functions, functions
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
        time_data = pd.DataFrame(time_data[:, 1:], index=idx, columns=['source', 'substance', 'value'])
        # Sort data
        time_data = time_data.sort_index()
        status, message, data = 'ok', "", None
        # Structure data
        groups = time_data.groupby(['source'])
        if len(groups) == 0: return JSONResponse({"status": 'error', "content": data,
                "message": 'The inputed time-series data No Location/Substance found in the table.'})
        result = []
        for name, group in groups:
            if (len(group) == 0 or name[0] not in loads): continue
            gr_substance = [x[0][0] for x in group.groupby(['substance'])]
            subs = ' '.join(f"'{x}'" for x in gr_substance)
            if key == 'simple-oxygen':
                temp = ["DATA_ITEM", name[0], "CONCENTRATIONS",
                f"INCLUDE 'includes_deltashell\\load_data_tables\\{folder}.usefors'",
                "TIME LINEAR DATA", subs]
                to_ = ['NH4', 'CBOD5', 'OXY', 'SOD']

            elif key == 'oxygen-bod-water':
                temp = []
                to_ = ['OXY', 'CBOD5']
            
            elif key == 'cadmium':
                temp = []
                to_ = ['IM1', 'Cd', 'IM1S1', 'CdS1']
            elif key == 'eutrophication':
                temp = []
                to_ = ['A', 'DP', 'NORG', 'NH4', 'NO3']
            elif key == 'tracer-metals':
                temp = []
                to_ = ['ASWTOT', 'CUWTOT', 'NIWTOT', 'PBWTOT', 'POCW', 'AOCW', 'DOCW', 'SSW', 'ZNWTOT',
                        'ASREDT', 'ASSTOT', 'ASSUBT', 'CUREDT', 'CUSTOT', 'CUSUBT', 'NIREDT', 'NISTOT', 'NISUBT',
                        'PBREDT', 'PBSTOT', 'PBSUBT', 'DOCB', 'DOCSUB', 'POCB', 'POCSUB', 'S', 'ZNREDT', 'ZNSTOT', 'ZNSUBT']
            elif key == 'conservative-tracers':
                temp = []
                to_ = ['cTR1', 'cTR2', 'cTR3', 'dTR1', 'dTR2', 'dTR3']
            elif key == 'suspend-sediment':
                temp = []
                to_ = ['IM1', 'IM2', 'IM3', 'IM1S1', 'IM2S1', 'IM3S1']
            elif key == 'coliform':
                temp = []
                to_ = ['Salinity', 'EColi']
            
            # Assign data
            df = pd.DataFrame(index=group.index)
            for item in gr_substance:
                df[item] = group[group['substance'] == item].value
            df.replace(np.nan, -999, inplace=True)
            df.index = [x.strftime('%Y/%m/%d-%H:%M:%S') for x in df.index]
            df.reset_index(inplace=True)
            lst = df.astype(str).values.tolist() # Convert to string
            lst = [' '.join(x) for x in lst]
            temp += lst
            result.append('\n'.join(temp))
        status, message, data, from_ = 'ok', "", '\n\n\n'.join(result), gr_substance
    except Exception as e:
        status, message, data, from_, to_ = 'error', f"Error: {str(e)}", None, None, None
    return JSONResponse({"status": status, "message": message, "content": data, "froms": from_, "tos": to_})

@router.websocket("/run_wq")
async def run_wq(websocket: WebSocket):
    await websocket.accept()
    try:
        # Get parameters from frontend
        body = await websocket.receive_json()
        project_name, key = body.get('projectName'), body.get('key')
        hyd_name, file_name = body.get('hydName'), body.get('folderName')
        obs_data, usefors = body.get('obsPoints'), body.get('usefors')
        time_data, ref_time = body.get('timeTable'), body.get('refTime')
        start_time, stop_time = body.get('startTime'), body.get('stopTime')
        time_step1, time_step2 = body.get('timeStep1'), body.get('timeStep2')
        n_segments, attr_path = body.get('nSegments'), body.get('attrPath')
        vol_path, exchange_x = body.get('volPath'), body.get('exchangeX')
        exchange_y, exchange_z = body.get('exchangeY'), body.get('exchangeZ')
        ptr_path, area_path = body.get('ptrPath'), body.get('areaPath')
        flow_path, length_path = body.get('flowPath'), body.get('lengthPath')
        parameters_path, vdf_path = body.get('parametersPath'), body.get('vdfPath')
        tem_path, initial = body.get('temPath'), body.get('initial')
        t_ref = datetime.fromtimestamp(int(ref_time)/1000.0, tz=timezone.utc)
        t_start = datetime.fromtimestamp(int(start_time)/1000.0, tz=timezone.utc)
        t_stop = datetime.fromtimestamp(int(stop_time)/1000.0, tz=timezone.utc)
        hyd_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "DFM_DELWAQ", hyd_name)
        hyd_folder, initial_list = os.path.dirname(hyd_path), body.get('initialList')
        parameters = {'hyd_path': hyd_path, "t_ref": t_ref, "t_start": t_start, "t_stop": t_stop,
            "t_step1": time_step1, "t_step2": time_step2, "obs_data": obs_data, 'n_segments': n_segments,
            'attr_path': os.path.join(hyd_folder, attr_path), 'vol_path': os.path.join(hyd_folder, vol_path),
            'exchange_x': exchange_x, 'exchange_y': exchange_y, 'exchange_z': exchange_z, 'folder_name': file_name,
            'ptr_path': os.path.join(hyd_folder, ptr_path), 'area_path': os.path.join(hyd_folder, area_path),
            'flow_path': os.path.join(hyd_folder, flow_path), 'length_path': os.path.join(hyd_folder, length_path),
            'n_layers': body.get('nLayers'), 'sources': body.get('sources'), 'loads_data': body.get('loadsData'),
            'parameters_path': os.path.join(hyd_folder, parameters_path), 'vdf_path': os.path.join(hyd_folder, vdf_path),
            'tem_path': os.path.join(hyd_folder, tem_path), 'initial_list': initial_list, 'initial_set': initial.split('\n')
        }
        wq_folder = os.path.join(PROJECT_STATIC_ROOT, project_name, "WAQ")
        if not os.path.exists(wq_folder): os.makedirs(wq_folder)
        output_folder = os.path.join(wq_folder, file_name)
        if not os.path.exists(output_folder): os.makedirs(output_folder)
        # Run WAQ simulation
        delwaq1_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/bin/delwaq1.exe'
        delwaq2_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/bin/delwaq2.exe'
        proc_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/default/proc_def.def'
        bloom_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/default/bloom.spe'
        paths_to_check = [ delwaq1_path, delwaq2_path, proc_path, bloom_path ]
        # Check if all paths exist and are valid to run the simulation
        for path in paths_to_check:
            if not os.path.exists(path):
                return JSONResponse({"status": 'error', "message": f"File not found: {path}"})
            if not os.access(path, os.R_OK):
                return JSONResponse({"status": 'error', "message": f"No read permission: {path}"})
        delwaq1_path, delwaq2_path = os.path.normpath(delwaq1_path), os.path.normpath(delwaq2_path)
        proc_path, bloom_path = os.path.normpath(proc_path), os.path.normpath(bloom_path)
        # Prepare input files
        includes_folder = os.path.join(output_folder, "includes_deltashell")
        if not os.path.exists(includes_folder): os.makedirs(includes_folder)
        table_folder = os.path.join(includes_folder, "load_data_tables")
        if not os.path.exists(table_folder): os.makedirs(table_folder)
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
        if inp_file is None: return JSONResponse({"status": 'error', "message": ms})
        inp_name = os.path.basename(inp_file)
        # Add dll path
        dll_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/share/bin'
        os.environ["PATH"] += ";" + dll_path
        # Run Simulation and get output
        progress_pattern = re.compile(r"(\d+\.\d+)% Completed")
        # === Run delwaq1 ===
        await websocket.send_json({"status": "Preparing inputs for WAQ simulation..."})
        run1 = subprocess.Popen([delwaq1_path, inp_name, "-p", proc_path, "-eco", bloom_path],
            cwd=output_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        for line in iter(run1.stdout.readline, ""):
            if not line: break
            await websocket.send_json({"log": line.strip()})
            await asyncio.sleep(0)
        run1.wait()
        await websocket.send_json({"status": "Finished preparing inputs"})
        # === Run delwaq2 ===
        await websocket.send_json({"status": "Running WAQ simulation..."})
        run2 = subprocess.Popen( [delwaq2_path, inp_name], cwd=output_folder, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        for line in iter(run2.stdout.readline, ""):
            if not line: break
            match = progress_pattern.search(line)
            if match:
                percent = float(match.group(1))
                await websocket.send_json({"progress": percent})
            await asyncio.sleep(0)
        run2.wait()
        await websocket.send_json({"status": "Simulation completed"})
        # Move WAQ output files to output folder
        await websocket.send_json({"status": "Reorganizing NC files..."})
        out_folder = os.path.join(PROJECT_STATIC_ROOT, project_name, "output")
        if not os.path.exists(out_folder): os.makedirs(out_folder)
        output_WAQ_folder = os.path.join(out_folder, 'WAQ')
        if not os.path.exists(output_WAQ_folder): os.makedirs(output_WAQ_folder)
        his_path = os.path.join(output_folder, f"{file_name}_his.nc")
        map_path = os.path.join(output_folder, f"{file_name}_map.nc")
        # Copy NC files
        if os.path.exists(his_path):
            tem_path = os.path.join(output_WAQ_folder, f"{file_name}_his.nc")
            shutil.copy(his_path, tem_path)
        if os.path.exists(map_path):
            tem_path = os.path.join(output_WAQ_folder, f"{file_name}_map.nc")
            shutil.copy(map_path, tem_path)
        await websocket.send_json({"status": "NC files moved"})
        # Delete folder
        try: shutil.rmtree(wq_folder, onexc=functions.remove_readonly)
        except Exception as e: await websocket.send_json({'error': str(e)})
        await websocket.send_json({"status": "Done"})
        await websocket.close()
    except WebSocketDisconnect: pass
    except Exception as e:
        try: await websocket.send_json({"error": str(e)})
        except Exception: pass
