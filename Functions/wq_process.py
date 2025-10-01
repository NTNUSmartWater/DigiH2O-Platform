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
        srf_path, vdf_path = body.get('srfPath'), body.get('vdfPath')
        tem_path, initial = body.get('temPath'), body.get('initial')
        sal_path = body.get('salPath')
        t_ref = datetime.fromtimestamp(int(ref_time)/1000.0, tz=timezone.utc)
        t_start = datetime.fromtimestamp(int(start_time)/1000.0, tz=timezone.utc)
        t_stop = datetime.fromtimestamp(int(stop_time)/1000.0, tz=timezone.utc)
        hyd_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "DFM_DELWAQ", hyd_name)
        hyd_folder, initial_list = os.path.dirname(hyd_path), body.get('initialList')
        parameters = {'hyd_path': hyd_path, "t_ref": t_ref, "t_start": t_start, "t_stop": t_stop,
            "maxiter": body.get('maxiter'), "tolerance": body.get('tolerance'), "scheme": body.get('scheme'),
            "t_step1": time_step1, "t_step2": time_step2, "obs_data": obs_data, 'n_segments': n_segments,
            'attr_path': os.path.join(hyd_folder, attr_path), 'vol_path': os.path.join(hyd_folder, vol_path),
            'exchange_x': exchange_x, 'exchange_y': exchange_y, 'exchange_z': exchange_z, 'folder_name': file_name,
            'ptr_path': os.path.join(hyd_folder, ptr_path), 'area_path': os.path.join(hyd_folder, area_path),
            'flow_path': os.path.join(hyd_folder, flow_path), 'length_path': os.path.join(hyd_folder, length_path),
            'n_layers': body.get('nLayers'), 'sources': body.get('sources'), 'loads_data': body.get('loadsData'),
            'srf_path': os.path.join(hyd_folder, srf_path), 'vdf_path': os.path.join(hyd_folder, vdf_path),
            'tem_path': os.path.join(hyd_folder, tem_path), 'initial_list': initial_list, 'initial_set': initial.split('\n'),
            'sal_path': os.path.join(hyd_folder, sal_path)
        }
        wq_folder = os.path.join(PROJECT_STATIC_ROOT, project_name, "WAQ")
        if not os.path.exists(wq_folder): os.makedirs(wq_folder)
        output_folder = os.path.join(wq_folder, file_name)
        if os.path.exists(output_folder):
            try: shutil.rmtree(output_folder, onexc=functions.remove_readonly)
            except Exception as e: await websocket.send_json({'error': str(e)})
        os.makedirs(output_folder)
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
        # Run WAQ simulation
        delwaq1_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/bin/delwaq1.exe'
        delwaq2_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/bin/delwaq2.exe'
        bloom_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/default/bloom.spe'
        proc_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/dwaq/default/proc_def.def'
        paths_to_check = [ delwaq1_path, delwaq2_path, proc_path, bloom_path ]
        # Check if all paths exist and are valid to run the simulation
        for path in paths_to_check:
            if not os.path.exists(path):
                return JSONResponse({"status": 'error', "message": f"File not found: {path}"})
            if not os.access(path, os.R_OK):
                return JSONResponse({"status": 'error', "message": f"No read permission: {path}"})
        delwaq1_path, delwaq2_path = os.path.normpath(delwaq1_path), os.path.normpath(delwaq2_path)
        proc_path, bloom_path = os.path.normpath(proc_path), os.path.normpath(bloom_path)
        # Add dll path
        dll_path = 'C:/Program Files/Deltares/Delft3D FM Suite 2023.02 HMWQ/plugins/DeltaShell.Dimr/kernels/x64/share/bin'
        os.environ["PATH"] += os.pathsep + dll_path
        # Run Simulation and get output
        success1, success2 = False, False
        # === Run delwaq1 ===
        print('=== Run delwaq1 ===')
        await websocket.send_json({"status": "Preparing inputs for WAQ simulation..."})
        process1 = subprocess.Popen([delwaq1_path, inp_name, "-p", proc_path, "-eco", bloom_path],
            cwd=output_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        for line in process1.stdout:
            line = line.strip()
            if not line: continue
            if "Normal end" in line: success1 = True
            if line: print("[OUT]", line)
            await asyncio.sleep(0)
        for line in process1.stderr:
            line = line.strip()
            if line: print("[ERR]", line)
        process1.wait()
        if not success1:
            await websocket.send_json({"status": "Error: Prepare inputs failed."})
            await websocket.close()
            return
        await websocket.send_json({"status": "Finished preparing inputs."})
        # === Run delwaq2 ===
        print('=== Run delwaq2 ===')
        progress_pattern = re.compile(r"(\d+(?:\.\d+)?)% Completed")
        await websocket.send_json({"status": "Running WAQ simulation..."})
        process2 = subprocess.Popen( [delwaq2_path, inp_name], cwd=output_folder, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        for line in process2.stdout:
            line = line.strip()
            if not line: continue
            if "ERROR in GMRES" in line:
                await websocket.send_json({"status": "Error: GMRES solver failed.\nConsider increasing the maximum number of iterations."})
                process2.terminate()
                await websocket.close()
                return
            if "Normal end" in line: success2 = True
            print("[OUT]", line)
            match = progress_pattern.search(line)
            if match:
                percent = float(match.group(1))
                await websocket.send_json({"progress": percent})
            await asyncio.sleep(0)
        for line in process2.stderr:
            line = line.strip()
            if line: print("[ERR]", line)
        process2.wait()
        if not success2:
            await websocket.send_json({"status": "Error: WAQ simulation failed."})
            await websocket.close()
            return
        await websocket.send_json({"progress": 100.0})
        print('=== Finished ===')
        # Move WAQ output files to output folder
        await websocket.send_json({"status": "Reorganizing NC files..."})
        out_folder = os.path.join(PROJECT_STATIC_ROOT, project_name, "output")
        if not os.path.exists(out_folder): os.makedirs(out_folder)
        output_WAQ_folder = os.path.join(out_folder, 'WAQ')
        if not os.path.exists(output_WAQ_folder): os.makedirs(output_WAQ_folder)
        his_path = os.path.join(output_folder, f"{file_name}_his.nc")
        map_path = os.path.join(output_folder, f"{file_name}_map.nc")
        if not os.path.exists(his_path) and not os.path.exists(map_path):
            await websocket.send_json({"status": "Error: Cannot find both his and map NC files."})
            await websocket.close()
            return
        # Copy NC files
        if os.path.exists(his_path):
            tem_path = os.path.join(output_WAQ_folder, f"{file_name}_his.nc")
            shutil.copy(his_path, tem_path)
        if os.path.exists(map_path):
            tem_path = os.path.join(output_WAQ_folder, f"{file_name}_map.nc")
            shutil.copy(map_path, tem_path)
        await websocket.send_json({"status": "NC files moved."})
        # Delete folder
        try: shutil.rmtree(wq_folder, onexc=functions.remove_readonly)
        except Exception as e: await websocket.send_json({'error': str(e)})
        await websocket.send_json({"status": "Simulation completed successfully."})
        await websocket.close()
    except WebSocketDisconnect: pass
    except Exception as e:
        try: await websocket.send_json({"error": str(e)})
        except Exception: pass
