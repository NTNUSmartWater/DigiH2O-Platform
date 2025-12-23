import os, subprocess, re, shutil, json, asyncio, signal, traceback, threading
import pandas as pd, numpy as np, xarray as xr
from fastapi import APIRouter, Request, Depends, Query
from config import PROJECT_STATIC_ROOT, DELFT_PATH
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from Functions import wq_functions, functions

router, processes = APIRouter(), {}

def path_process(full_path:str, head:int=3, tail:int=2):
    parts  = full_path.split('/')
    if len(parts) <= head + tail: return full_path
    return '/'.join(parts[:head]) + '/ ... /' + '/'.join(parts[-tail:])



@router.post("/select_hyd")
async def select_hyd(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name = functions.project_definer(body.get('projectName'), user)
    folder = [PROJECT_STATIC_ROOT, project_name, "DFM_DELWAQ", 'FlowFM.hyd']
    path = os.path.normpath(os.path.join(*folder))
    if os.path.exists(path):
        return JSONResponse({"status": 'ok', "content": wq_functions.hydReader(path)})
    message = f"Error: Cannot find .hyd file in project '{project_name}'.\nPlease run a hydrodynamic simulation first."
    return JSONResponse({"status": 'error', "message": message})

@router.post("/select_waq")
async def select_waq(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        folder = [PROJECT_STATIC_ROOT, project_name, "output", 'scenarios']
        path = os.path.normpath(os.path.join(*folder))
        files = [f.replace('.json', '') for f in os.listdir(path) if f.endswith('.json')]
        if len(files) == 0: return JSONResponse({"status": 'error'})
        return JSONResponse({"status": 'ok', "content": files})
    except: return JSONResponse({"status": 'error'})

@router.post("/load_waq")
async def load_waq(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        folder = [PROJECT_STATIC_ROOT, project_name, "output", 'scenarios', f"{body.get('waqName')}.json"]
        path, data = os.path.normpath(os.path.join(*folder)), {}
        if not os.path.exists(path): return JSONResponse({"status": 'error', "message": 'Configuration file not found.'})
        with open(path, 'r', encoding='utf-8') as f:
            files = json.load(f)
        data['key'], data['name'], data['mode'] = files['key'], files['folderName'], files['mode']
        data['obs'], data['loads'] = files['obsPoints'], files['loadsData']
        data['times'], data['usefors'] = files['timeTable'], files['usefors']
        data['initial'], data['scheme'] = files['initial'], files['scheme']
        data['maxiter'], data['tolerance'] = files['maxiter'], files['tolerance']
        data['useforsFrom'], data['useforsTo'] = files['useforsFrom'], files['useforsTo']
        return JSONResponse({"status": 'ok', "content": data})
    except: return JSONResponse({"status": 'error'})

@router.post("/wq_time_from_waq")
async def wq_time_from_waq(request: Request):
    try:
        body = await request.json()
        key = body.get('key')
        if key == 'Simple_Oxygen': from_ = ['NH4', 'CBOD5', 'OXY', 'SOD']
        elif key == 'Oxygen_BOD': from_ = ['OXY', 'CBOD5']
        elif key == 'Cadmium': from_ = ['IM1', 'Cd', 'IM1S1', 'CdS1']
        elif key == 'Eutrophication': from_ = ['A', 'DP', 'NORG', 'NH4', 'NO3']
        elif key == 'Trace_Metals': from_ = ['ASWTOT', 'CUWTOT', 'NIWTOT', 'PBWTOT', 'POCW', 'AOCW', 'DOCW', 'SSW', 'ZNWTOT',
                    'ASREDT', 'ASSTOT', 'ASSUBT', 'CUREDT', 'CUSTOT', 'CUSUBT', 'NIREDT', 'NISTOT', 'NISUBT',
                    'PBREDT', 'PBSTOT', 'PBSUBT', 'DOCB', 'DOCSUB', 'POCB', 'POCSUB', 'S', 'ZNREDT', 'ZNSTOT', 'ZNSUBT']
        elif key == 'Conservative_Tracers': from_ = ['cTR1', 'cTR2', 'cTR3', 'dTR1', 'dTR2', 'dTR3']
        elif key == 'Suspend_Sediment': from_ = ['IM1', 'IM2', 'IM3', 'IM1S1', 'IM2S1', 'IM3S1']
        elif key == 'Coliform': from_ = ['Salinity', 'EColi']
        return JSONResponse({"status": 'ok', "froms": from_})
    except Exception as e:
        return JSONResponse({"status": 'error', "message":  f"Error: {str(e)}"})

@router.post("/wq_time_to_waq")
async def wq_time(request: Request):
    try:
        body = await request.json()
        load_data, time_data, folder = body.get('loadsData'), body.get('timeData'), body.get('folderName')
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
        return JSONResponse({"status": 'ok',"content": '\n\n\n'.join(result), "tos": gr_substance})
    except Exception as e: return JSONResponse({"status": 'error', "message":  f"Error: {str(e)}"})

@router.post("/waq_config_writer")
async def waq_config_writer(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        config_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "scenarios"))
        if not os.path.exists(config_path): os.makedirs(config_path)
        config_file = os.path.normpath(os.path.join(config_path, f"{body.get('folderName')}.json"))
        if os.path.exists(config_file): os.remove(config_file)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(body, f, indent=4)
        return JSONResponse({"status": 'ok', "message": 'Model configuration saved successfully.'})
    except Exception as e: return JSONResponse({"status": 'error', "message":  f"Error: {str(e)}"})

# Check if simulation is running
@router.post("/check_sim_status_waq")
async def check_sim_status_waq(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name = functions.project_definer(body.get('projectName'), user)
    info, logs = processes.get(project_name), []
    if not info:
        return JSONResponse({"status": "not_started", "progress": 0, "logs": logs, "message": '', "complete": 'Completed: --%'})
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log_waq.txt"))
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            logs = f.read().splitlines()
    return JSONResponse({ "status": info["status"], "progress": info["progress"], "logs": logs, "message": info["message"],
                            "complete": f"Completed: {info['progress']}%"})

@router.get("/sim_log_tail_waq/{project_name}")
async def sim_log_tail_waq(project_name: str, offset: int = Query(0), log_file: str = Query(""), user=Depends(functions.basic_auth)):
    project_name = functions.project_definer(project_name, user)
    log_path, lines = os.path.join(PROJECT_STATIC_ROOT, project_name, log_file), []
    if not os.path.exists(log_path): return {"lines": lines, "offset": offset}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        for line in f:
            lines.append(line.rstrip())
    return {"lines": lines, "offset": os.path.getsize(log_path)}

# Start a waq simulation
@router.post("/start_sim_waq")
async def start_sim_waq(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, waq_name = functions.project_definer(body.get('projectName'), user), body.get('waqName')
    if project_name in processes and processes[project_name]["status"] == "running":
        old = processes[project_name]["status"]
        if old in ("finished", "error"): processes.pop(project_name)
        return JSONResponse({"status": "error", "message": "Simulation already running"})
    asyncio.create_task(run_waq_simulation(project_name, waq_name))
    return JSONResponse({"status": "ok", "message": "Simulation started"})

async def run_waq_simulation(project_name, waq_name):
    processes[project_name] = {"status": "not_started", "progress": 0, "message": "", "process": None}
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log_waq.txt"))
    if os.path.exists(log_path): os.remove(log_path)
    log_file = open(log_path, "a", encoding="utf-8", errors="replace")
    log_file.write(f"Project: {project_name}\n")
    log_file.write(f"Simulation started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write("===============================================\n\n")
    # Check if configuration exists
    config_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "scenarios")
    config_file = os.path.normpath(os.path.join(config_path, f"{waq_name}.json"))
    if not os.path.exists(config_file):
        log_file.write("Configuration file not found.\n")
        processes[project_name]["status"] = "error"
        processes[project_name]["message"] = "Configuration file not found."
        log_file.flush(); log_file.close()
        return
    log_file.write("Configuration file found. Reading configuration ...\n")
    with open(config_file, "r", encoding="utf-8", errors="replace") as f:
        body = json.load(f)
    # Start simulation
    try:
        key, file_name, time_data, usefors = body['key'], body['folderName'], body['timeTable'], body['usefors']
        t_start = datetime.fromtimestamp(int(body['startTime']/1000.0), tz=timezone.utc)
        t_stop = datetime.fromtimestamp(int(body['stopTime']/1000.0), tz=timezone.utc)
        hyd_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "DFM_DELWAQ"))
        hyd_path = os.path.normpath(os.path.join(hyd_folder, body['hydName']))
        sal_path, attr_path = os.path.normpath(os.path.join(hyd_folder, body['salPath'])), os.path.normpath(os.path.join(hyd_folder, body['attrPath']))
        vol_path, ptr_path = os.path.normpath(os.path.join(hyd_folder, body['volPath'])), os.path.normpath(os.path.join(hyd_folder, body['ptrPath']))
        area_path, flow_path = os.path.normpath(os.path.join(hyd_folder, body['areaPath'])), os.path.normpath(os.path.join(hyd_folder, body['flowPath']))
        length_path, srf_path = os.path.normpath(os.path.join(hyd_folder, body['lengthPath'])), os.path.normpath(os.path.join(hyd_folder, body['srfPath']))
        vdf_path, tem_path = os.path.normpath(os.path.join(hyd_folder, body['vdfPath'])), os.path.normpath(os.path.join(hyd_folder, body['temPath']))
        wq_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "WAQ"))
        os.makedirs(wq_folder, exist_ok=True)
        # Clear data if exists
        output_folder = os.path.normpath(os.path.join(wq_folder, file_name))
        if os.path.exists(output_folder): shutil.rmtree(output_folder, onerror=functions.remove_readonly)
        os.makedirs(output_folder, exist_ok=True)
        parameters = {'hyd_path': hyd_path, "t_start": t_start, "t_stop": t_stop, 'sal_path': sal_path,
            "maxiter": body['maxiter'], "tolerance": body['tolerance'], "scheme": body['scheme'], 'srf_path': srf_path, 
            "t_step1": body['timeStep1'], "t_step2": body['timeStep2'], "obs_data": body['obsPoints'],
            'n_segments': body['nSegments'], 'attr_path': attr_path, 'vol_path': vol_path, 'exchange_x': body['exchangeX'],
            'exchange_y': body['exchangeY'], 'exchange_z': body['exchangeZ'], 'folder_name': file_name,
            'ptr_path': ptr_path, 'area_path': area_path, 'flow_path': flow_path, 'length_path': length_path,
            'n_layers': body['nLayers'], 'sources': body['sources'], 'loads_data': body['loadsData'],
            'vdf_path': vdf_path, 'tem_path': tem_path, 'initial_list': body['useforsFrom'], 'initial_set': body['initial'].split('\n')
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
        inp_file = wq_functions.wqPreparation(parameters, key, output_folder, includes_folder)
        if inp_file is None:
            log_file.write("Error creating *.inp file.\n")
            processes[project_name]['status'] = "error"
            processes[project_name]['message'] = "Error creating *.inp file"
            log_file.flush(); log_file.close()
            return
        # Check if all paths are valid to run the simulation
        bat_path = os.path.normpath(os.path.join(DELFT_PATH, "dwaq/scripts/run_delwaq.bat"))
        bloom_path = os.path.normpath(os.path.join(DELFT_PATH, 'dwaq/default/bloom.spe'))
        proc_path = os.path.normpath(os.path.join(DELFT_PATH, 'dwaq/default/proc_def.def'))
        paths_to_check = [bat_path, proc_path, bloom_path]
        for path in paths_to_check:
            if not os.access(path, os.R_OK):
                log_file.write(f"No read permission: {path}\n")
                processes[project_name]["status"] = "error"
                processes[project_name]["message"] = "No read permission"
                log_file.flush(); log_file.close()
                return
        # Run Simulation and get output
        inp_name = os.path.basename(inp_file)
        progress_regex = re.compile(r"(\d+(?:\.\d+)?)% Completed")
        command = [bat_path, inp_name, "-p", proc_path.replace(".def", ""), "-eco", bloom_path]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1, cwd=output_folder)
        processes[project_name] = {"process": process, "progress": 0.0, "status": "running", "message": 'Checking inputs for WAQ simulation...'}
        log_file.write("Checking inputs for WAQ simulation\n\n")
        log_file.write("=== Starting simulation ===\n\n")
        # Stream logs
        def stream_logs():
            try:
                for line in process.stdout:
                    line = line.strip()
                    if not line: continue
                    log_file.write(line + "\n")
                    if "ERROR in GMRES" in line:
                        log_file.write(line + "\n")
                        processes[project_name]["status"] = "error" 
                        processes[project_name]["message"] = "\n\nGMRES solver failed.\nConsider increasing the maximum number of iterations."
                        res = functions.kill_process(process)
                        log_file.write(res["message"] + "\n")
                        log_file.write("\n\nGMRES solver failed.\nConsider increasing the maximum number of iterations.\n")
                        break
                    # Check for progress
                    match_pct = progress_regex.search(line)
                    if match_pct: processes[project_name]["progress"] = float(match_pct.group(1))
            finally:
                process.wait()
                status = processes[project_name]["status"]
                if status != "error":
                    try:
                        processes[project_name]["progress"] = 100.0
                        processes[project_name]["status"] = "postprocessing"
                        processes[project_name]["message"] = 'Reorganizing outputs. Please wait...'
                        output_dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "output"))
                        if not os.path.exists(output_dir): os.makedirs(output_dir)
                        output_WAQ_dir = os.path.normpath(os.path.join(output_dir, 'WAQ'))
                        if not os.path.exists(output_WAQ_dir): os.makedirs(output_WAQ_dir)
                        for suffix in ["_his.nc", "_map.nc", ".json"]:
                            new_name = f"{file_name}{suffix}"
                            src = os.path.normpath(os.path.join(output_folder, new_name))
                            if os.path.exists(src):
                                # # Using .nc format
                                # dst = os.path.normpath(os.path.join(output_WAQ_dir, new_name))
                                # shutil.copy2(src, dst)
                                
                                # Using .zarr format
                                zarr_path = os.path.normpath(os.path.join(output_WAQ_dir, new_name.replace('.nc', '.zarr')))
                                if suffix != ".json":
                                    tmp_path = zarr_path + "_tmp"
                                    if os.path.exists(tmp_path): shutil.rmtree(tmp_path, onerror=functions.remove_readonly)
                                    with xr.open_dataset(src, chunks='auto') as ds:
                                        ds.to_zarr(tmp_path, mode='w', consolidated=True, compute=True)
                                    if os.path.exists(zarr_path): shutil.rmtree(zarr_path, onerror=functions.remove_readonly)
                                    os.rename(tmp_path, zarr_path)                      
                                else: shutil.copy2(src, zarr_path)
                                functions.safe_remove(src)
                        # Delete folder
                        if os.path.exists(wq_folder): shutil.rmtree(wq_folder, onerror=functions.remove_readonly)
                        processes[project_name]["status"] = "finished"
                        processes[project_name]["message"] = f"Simulation completed successfully."
                        log_file.write(f"\n=== Simulation {project_name} completed successfully ===")
                        log_file.flush(); log_file.close()
                        return JSONResponse({"status": "ok", "message": f"Simulation completed successfully."})
                    except Exception as e:
                        processes[project_name]["status"], processes[project_name]["message"] = "error", str(e)
                        log_file.write(f"Exception: {str(e)}")
                        log_file.flush(); log_file.close()
                        return JSONResponse({"status": "error", "message": str(e)})
                processes.pop(project_name, None)
        threading.Thread(target=stream_logs, daemon=True).start()
    except Exception as e:
        processes[project_name]["status"], processes[project_name]["message"] = "error", str(e)
        print('/run_waq_simulation:\n==============')
        traceback.print_exc()
        log_file.write(f"Error running simulation: {str(e)}")
        log_file.flush(); log_file.close()
        return