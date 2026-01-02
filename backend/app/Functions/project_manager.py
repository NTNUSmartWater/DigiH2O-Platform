import os, shutil, subprocess, re, json, msgpack
import asyncio, traceback, datetime
import numpy as np
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from Functions import functions
from config import PROJECT_STATIC_ROOT, STATIC_DIR_BACKEND

router = APIRouter()

@router.post("/auth_check")
async def auth_check(user=Depends(functions.basic_auth)):
    output = 'ok' if user == 'admin' else 'error'
    return {"user": user, "output": output}

# Remove folder configuration
@router.post("/reset_config")
async def reset_config(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        redis = request.app.state.redis
        lock = redis.lock(f"{project_name}:reset_config", timeout=20)        
        async with lock:
            # Reset project data in Redis
            folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))
            if not os.path.exists(folder): return JSONResponse({"message": "Project folder doesn't exist."})
            config_dir = os.path.normpath(os.path.join(folder, "output", "config"))
            if not os.path.exists(config_dir): return JSONResponse({"message": "Configuration folder doesn't exist."})
            try:
                shutil.rmtree(config_dir, onerror=functions.remove_readonly)
            except Exception as e:
                return JSONResponse({"message": f"Failed to delete config folder: {e}"})
            # Delete config in Redis
            await redis.hdel(project_name, "config", "layer_reverse_hyd", "layer_reverse_waq")
            return JSONResponse({"message": "Configuration reset successfully!"})
    except Exception as e:
        print('/reset_config:\n==============')
        traceback.print_exc()
        return JSONResponse({"message": f"Error: {e}"})

# Create a new project with necessary folders
@router.post("/setup_new_project")
async def setup_new_project(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        project_dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))
        # Check if project already exists
        if os.path.exists(project_dir):
            return JSONResponse({"status": 'ok', "message": f"Project '{body.get('projectName')}' already exists."})
        # Create project directories
        user_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, user))
        if not os.path.exists(user_path): os.makedirs(user_path, exist_ok=True)
        os.makedirs(project_dir, exist_ok=True)
        input_dir = os.path.normpath(os.path.join(project_dir, "input"))
        os.makedirs(input_dir, exist_ok=True)
        status, message = 'ok', f"Scenario '{body.get('projectName')}' created successfully!"
    except Exception as e:
        print('/setup_new_project:\n==============')
        traceback.print_exc()
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Get parameters for an existing scenario
@router.post("/get_scenario")
async def get_scenario(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        project_dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))
        in_dir, data = os.path.normpath(os.path.join(project_dir, "input")), {}
        if os.path.exists(in_dir):
            mdu_path = os.path.normpath(os.path.join(in_dir, "FlowFM.mdu"))
            if not os.path.exists(mdu_path):
                return JSONResponse({"status": 'error', "message": f"Scenario '{body.get('projectName')}' doesn't have an *.mdu file."})
            with open(mdu_path, 'r', encoding=functions.encoding_detect(mdu_path)) as f:
                for raw_line in f:
                    line = raw_line.split("#")[0].strip()
                    if line.startswith('AngLat'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2: data["avgLat"] = parts[1].strip()
                    elif line.startswith('NetFile'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2: data["gridPath"] = parts[1].strip()
                    elif line.startswith('Kmx'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2: data["nLayers"] = parts[1].strip()
                    elif line.startswith('TStart'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            temp = datetime.datetime.fromtimestamp(int(parts[1].strip()))
                            data["startDate"] = temp.strftime("%Y-%m-%d %H:%M:%S")
                    elif line.startswith('TStop'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            temp = datetime.datetime.fromtimestamp(int(parts[1].strip()))
                            data["stopDate"] = temp.strftime("%Y-%m-%d %H:%M:%S")
                    elif line.startswith('ObsFile'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            obs_path = os.path.normpath(os.path.join(in_dir, parts[1].strip()))
                            with open(obs_path, 'r', encoding=functions.encoding_detect(obs_path)) as f:
                                lines = f.readlines()
                            data["obsPointTable"] = [[z.replace("'", ""), y, x] 
                                for x, y, z in [line.split() for line in lines if len(line.split()) == 3]]
                    elif line.startswith('CrsFile'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            crs_path = os.path.normpath(os.path.join(in_dir, parts[1].strip()))
                            with open(crs_path, 'r', encoding=functions.encoding_detect(crs_path)) as f:
                                lines = f.readlines()
                            data["crossSectionTable"] = [[z, y, x] 
                                for x, y, z in [line.split() for line in lines if len(line.split()) == 3]]
                    elif line.startswith('ExtForceFileNew'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            boundary_path = os.path.normpath(os.path.join(in_dir, parts[1].strip()))
                            boundary, boundary_names, forcing = [], [], []
                            with open(boundary_path, 'r', encoding=functions.encoding_detect(boundary_path)) as f:
                                for line1 in f:
                                    if line1.strip().startswith('locationFile'):
                                        parts = line1.split("=")
                                        if len(parts) >= 2 and parts[1] not in boundary_names:
                                            file_path = os.path.normpath(os.path.join(in_dir, parts[1].replace("\n", "")))
                                            with open(file_path, 'r', encoding=functions.encoding_detect(file_path)) as f:
                                                line_files = f.readlines()
                                            boundary.append([[z, y, x] for x, y, z in [line.split() for line in line_files if len(line.split()) == 3]])
                                            boundary_names.append(parts[1])
                                    elif line1.strip().startswith('forcingFile'):
                                        parts = line1.split("=")
                                        if len(parts) >= 2 and parts[1] not in forcing: forcing.append(parts[1])
                            data["boundaryTable"] = boundary[0]
                    elif line.startswith('DtUser'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            values = functions.seconds_datetime(int(parts[1].strip()))
                            data["userTimestepDate"], data["userTimestepTime"] = values[0], values[1]
                    elif line.startswith('DtNodal'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            values = functions.seconds_datetime(int(parts[1].strip()))
                            data["nodalTimestepDate"], data["nodalTimestepTime"] = values[0], values[1]
                    elif line.startswith('HisInterval'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            temp = parts[1].strip()
                            seconds = int(temp.split(" ")[0].strip())
                            values = functions.seconds_datetime(seconds)
                            data["hisIntervalDate"], data["hisIntervalTime"] = values[0], values[1]
                            temp_start = int(temp.split(" ")[1].strip())
                            temp_stop = int(temp.split(" ")[2].strip())
                            start = datetime.datetime.fromtimestamp(temp_start)
                            stop = datetime.datetime.fromtimestamp(temp_stop)
                            data["hisStart"] = start.strftime("%Y-%m-%d %H:%M:%S")
                            data["hisStop"] = stop.strftime("%Y-%m-%d %H:%M:%S")
                    elif line.startswith('MapInterval'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            temp = parts[1].strip()
                            seconds = int(temp.split(" ")[0].strip())
                            values = functions.seconds_datetime(seconds)
                            data["mapIntervalDate"], data["mapIntervalTime"] = values[0], values[1]
                            temp_start = int(temp.split(" ")[1].strip())
                            temp_stop = int(temp.split(" ")[2].strip())
                            start = datetime.datetime.fromtimestamp(temp_start)
                            stop = datetime.datetime.fromtimestamp(temp_stop)
                            data["mapStart"] = start.strftime("%Y-%m-%d %H:%M:%S")
                            data["mapStop"] = stop.strftime("%Y-%m-%d %H:%M:%S")
                    elif line.startswith('WaqInterval'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            temp = parts[1].strip()
                            seconds = int(temp.split(" ")[0].strip())
                            values = functions.seconds_datetime(seconds)
                            data["wqIntervalDate"], data["wqIntervalTime"] = values[0], values[1]
                            temp_start = int(temp.split(" ")[1].strip())
                            temp_stop = int(temp.split(" ")[2].strip())
                            start = datetime.datetime.fromtimestamp(temp_start)
                            stop = datetime.datetime.fromtimestamp(temp_stop)
                            data["wqStart"] = start.strftime("%Y-%m-%d %H:%M:%S")
                            data["wqStop"] = stop.strftime("%Y-%m-%d %H:%M:%S")
                    elif line.startswith('StatsInterval'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            values = functions.seconds_datetime(int(parts[1].strip()))
                            data["statisticDate"], data["statisticTime"] = values[0], values[1]
                    elif line.startswith('TimingsInterval'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2:
                            values = functions.seconds_datetime(int(parts[1].strip()))
                            data["timingDate"], data["timingTime"] = values[0], values[1]
                    elif line.startswith('WaterLevIni'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2: data["initWaterLevel"] = parts[1].strip()
                    elif line.startswith('InitialSalinity'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2: data["initSalinity"] = parts[1].strip()
                    elif line.startswith('Temperature'):
                        parts = [p.strip() for p in line.split("=") if p.strip()]
                        if len(parts) == 2: data["initTemperature"] = parts[1].strip()
            data["meteoPath"], meteos, data["meteoName"] = '', [], "FlowFM_meteo.tim"
            meteo_path = os.path.normpath(os.path.join(in_dir, data["meteoName"]))
            if os.path.exists(meteo_path):
                with open(meteo_path, 'r', encoding=functions.encoding_detect(meteo_path)) as f:
                    lines = f.readlines()
                for line in lines:
                    line = line.replace("\n", "")
                    if len(line.strip().split()) != 5: continue
                    temp = line.strip().split()
                    temp[0] = datetime.datetime.fromtimestamp(int(temp[0].strip())*60).strftime("%Y-%m-%d %H:%M:%S")
                    meteos.append(temp)
                data["meteoPath"] = meteos
            data["weatherPath"], weathers, data["weatherType"], data["weatherName"] = '', [], '', "windxy.tim"
            weather_path = os.path.normpath(os.path.join(in_dir, data["weatherName"]))
            if os.path.exists(weather_path):
                with open(weather_path, 'r', encoding=functions.encoding_detect(weather_path)) as f:
                    lines = f.readlines()
                for line in lines:
                    line = line.replace("\n", "")
                    if not line.strip(): continue
                    temp = line.strip().split()
                    temp[0] = datetime.datetime.fromtimestamp(int(temp[0].strip())*60).strftime("%Y-%m-%d %H:%M:%S")
                    weathers.append(temp)
                if len(temp) == 3: data["weatherType"] = "wind-magnitude-direction"
                data["weatherPath"] = weathers
            return JSONResponse({"status": 'ok', "content": data})
        else: return JSONResponse({"status": 'new'})
    except Exception as e:
        print('/get_scenario:\n==============')
        traceback.print_exc()
        return JSONResponse({"status": 'error', "message": f"Error: {str(e)}\nConsider deleting the scenario and creating a new one."})

# Set up the database depending on the project
@router.post("/setup_database")
async def setup_database(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        redis, params = request.app.state.redis, body.get('params')
        extend_task, lock = None, redis.lock(f"{project_name}:setup_database", timeout=600)
        async with lock:
            extend_task = asyncio.create_task(functions.auto_extend(lock, interval=10))
            project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))
            demo_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, 'demo'))
            if user != 'admin':
                if not os.path.exists(project_folder):
                    print(f"Copying project 'demo' folder to '{project_folder}'")
                    os.makedirs(project_folder, exist_ok=True)
                    shutil.copytree(demo_folder, project_folder, dirs_exist_ok=True)
            output_dir = os.path.normpath(os.path.join(project_folder, "output"))
            config_dir = os.path.normpath(os.path.join(output_dir, "config"))
            hyd_dir = os.path.normpath(os.path.join(output_dir, 'HYD'))
            waq_dir = os.path.normpath(os.path.join(output_dir, 'WAQ'))
            os.makedirs(config_dir, exist_ok=True)
            project_cache_dict = getattr(request.app.state, "project_cache", None)
            if project_cache_dict is None:
                request.app.state.project_cache = {}
                project_cache_dict = request.app.state.project_cache
            project_cache = project_cache_dict.setdefault(project_name, {})
            dm = request.app.state.dataset_manager
            # Assign datasets (only load if file path exists)
            hyd_his = await functions.load_dataset_cached(project_cache, 'hyd_his', dm, hyd_dir, params[0])
            hyd_map = await functions.load_dataset_cached(project_cache, 'hyd_map', dm, hyd_dir, params[1])
            waq_his = await functions.load_dataset_cached(project_cache, 'waq_his', dm, waq_dir, params[2])
            waq_map = await functions.load_dataset_cached(project_cache, 'waq_map', dm, waq_dir, params[3])
            # Load or init config
            config_path = os.path.normpath(os.path.join(config_dir, 'config.json'))
            if os.path.exists(config_path) and os.path.getsize(config_path) > 0:
                print('Config already exists. Loading...')
                config = json.loads(open(config_path, "r", encoding=functions.encoding_detect(config_path)).read())
            else:
                print('Config doesn\'t exist. Creating...')
                config = {"hyd": {}, "waq": {}, "meta": {"hyd_scanned": False, "waq_scanned": False}, "model_type": ''}
                if os.path.exists(config_path): os.remove(config_path)
                open(config_path, "w", encoding=functions.encoding_detect(config_path)).write(json.dumps(config))
            # ---------------- Grid & Layer ----------------
            layer_reverse_hyd, layer_reverse_waq = {}, {}
            if hyd_map:
                print('Creating grid and layers for hydrodynamic simulation...')
                # Grid/layers generation
                grid = functions.unstructuredGridCreator(hyd_map)
                project_cache['grid'] = grid
                # Get number of layers
                layer_path = os.path.normpath(os.path.join(config_dir, 'layers_hyd.json'))
                if not os.path.exists(layer_path):
                    layer_reverse_hyd = functions.layerCounter(hyd_map, 'hyd')
                    json.dump(layer_reverse_hyd, open(layer_path, "w", encoding=functions.encoding_detect(layer_path)))                    
                else: layer_reverse_hyd = json.load(open(layer_path, "r", encoding=functions.encoding_detect(layer_path)))
            if waq_map:
                print('Creating grid and layers for water quality simulation...')
                layer_path = os.path.normpath(os.path.join(config_dir, 'layers_waq.json'))
                if not os.path.exists(layer_path):
                    layer_reverse_waq = functions.layerCounter(waq_map, 'waq')
                    json.dump(layer_reverse_waq, open(layer_path, "w", encoding=functions.encoding_detect(layer_path)))                    
                else: layer_reverse_waq = json.load(open(layer_path, "r", encoding=functions.encoding_detect(layer_path)))
            # Lazy scan HYD variables only once
            if (hyd_map or hyd_his) and not config['meta']['hyd_scanned']:
                print('Scanning HYD variables...')
                hyd_vars = functions.getVariablesNames([hyd_his, hyd_map], 'hyd')
                config["hyd"], config["meta"]["hyd_scanned"] = hyd_vars, True
            # Get WAQ model
            temp = params[2].replace('_his.zarr', '') if params[2] != '' else params[3].replace('_map.zarr', '')
            model_path, waq_model, obs = os.path.normpath(os.path.join(waq_dir, f'{temp}.json')), '', {}
            if os.path.exists(model_path):
                print('Loading WAQ model...')
                temp_data = json.load(open(model_path, "r", encoding=functions.encoding_detect(model_path)))
                waq_model = temp_data['model_type']
                if 'wq_obs' in temp_data: config['wq_obs'], obs['wq_obs'] = True, temp_data['wq_obs']
                if 'wq_loads' in temp_data: config['wq_loads'], obs['wq_loads'] = True, temp_data['wq_loads']
            if (waq_his or waq_map) and waq_model == '':
                return JSONResponse({"status": 'error', "message": "Some WAQ-related parameters are missing.\nConsider running the model again."})  
            # Lazy scan WAQ
            if (waq_map or waq_his) and config['model_type'] != waq_model:
                print('Scanning WAQ variables...')
                waq_vars = functions.getVariablesNames([waq_his, waq_map], waq_model)
                config["waq"], config["meta"]["waq_scanned"], config['model_type'] = waq_vars, True, waq_model
            # Delete waq option if no waq files
            if waq_his is None and waq_map is None:
                print('No waq files. Deleting waq option...')
                config['waq'], config['meta']['waq_scanned'], config['model_type'] = {}, False, ''
                config.pop("wq_obs", None)
                config.pop("wq_loads", None)
            # Save config
            open(config_path, "w", encoding=functions.encoding_detect(config_path)).write(json.dumps(config))
            # Restructure configuration
            result = {**config.get("hyd", {}), **config.get("waq", {})}
            for k, v in config.items():
                if k not in ("hyd", "waq", "meta"):
                    result[k] = v
            # Serialize grid & layer_reverse to JSON-safe formats
            redis_mapping = {
                "hyd_his_path": params[0], "hyd_map_path": params[1], "waq_his_path": params[2], "waq_map_path": params[3],
                "layer_reverse_hyd": msgpack.packb(layer_reverse_hyd, use_bin_type=True),
                "layer_reverse_waq": msgpack.packb(layer_reverse_waq, use_bin_type=True),
                "config": msgpack.packb(result, use_bin_type=True),
                "waq_obs": msgpack.packb(obs, use_bin_type=True), "waq_model": waq_model
            }
            # Save to Redis
            await redis.delete(project_name)
            await redis.hset(project_name, mapping=redis_mapping)
            print('Configuration loaded successfully.')
            return JSONResponse({"status": 'ok'})
    except Exception as e:
        print('/setup_database:\n==============')
        traceback.print_exc()
        return JSONResponse({"status": 'error', "message": f"Error: {str(e)}"})
    finally:
        if extend_task:
            extend_task.cancel()
            try: await extend_task
            except asyncio.CancelledError: pass

# Copy a project
@router.post("/copy_project")
async def copy_project(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        old_name = functions.project_definer(body.get('oldName'), user)
        new_name = functions.project_definer(body.get('newName'), user)
        project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, old_name))
        redis = request.app.state.redis
        extend_task, lock = None, redis.lock(f"{old_name}:copy_project", timeout=600)
        async with lock:
            # Optional: auto-extend lock if deletion may take long
            extend_task = asyncio.create_task(functions.auto_extend(lock))
            if not os.path.exists(project_folder): 
                return JSONResponse({"status": 'error', "message": f"Project '{old_name}' does not exist."})
            shutil.copytree(project_folder, os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, new_name)))
            return JSONResponse({"message": f"Scenario '{new_name}' was cloned successfully!"})
    except Exception as e:
        print('/copy_project:\n==============')
        traceback.print_exc()
        return JSONResponse({"message": f"Error: {str(e)}"})
    finally:
        if extend_task:
            extend_task.cancel()
            try: await extend_task
            except asyncio.CancelledError: pass

@router.post("/clone_waq")
async def clone_waq(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        old_name, new_name = body.get('oldName'), body.get('newName')
        project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, 'output', 'scenarios'))
        redis = request.app.state.redis
        extend_task, lock = None, redis.lock(f"{project_name}:clone_waq", timeout=100, blocking_timeout=10)
        async with lock:
            extend_task = asyncio.create_task(functions.auto_extend(lock))
            old_path = os.path.normpath(os.path.join(project_folder, f"{old_name}.json"))
            new_path = os.path.normpath(os.path.join(project_folder, f"{new_name}.json"))
            if not os.path.exists(old_path): 
                return JSONResponse({"status": 'error', "message": f"Path '{old_path}' does not exist."})
            data = json.load(open(old_path, 'r', encoding=functions.encoding_detect(old_path)))
            data['folderName'] = new_name.replace('.json', '')
            json.dump(data, open(new_path, 'w', encoding=functions.encoding_detect(new_path)))
            return JSONResponse({"message": f"Scenario '{new_name}' was cloned successfully!"})
    except Exception as e:
        print('/clone_waq:\n==============')
        traceback.print_exc()
        return JSONResponse({"message": f"Error: {str(e)}"})
    finally:
        if extend_task:
            extend_task.cancel()
            try: await extend_task
            except asyncio.CancelledError: pass

# Delete a file
@router.post("/delete_file")
async def delete_file(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, 'output', 'scenarios'))
        redis, file = request.app.state.redis, body.get('name')
        extend_task, lock = None, redis.lock(f"{project_name}:delete_file", timeout=300)
        async with lock:
            extend_task = asyncio.create_task(functions.auto_extend(lock))
            file_name = os.path.normpath(os.path.join(project_folder, f"{file}.json"))
            if not os.path.exists(file_name): 
                return JSONResponse({"status": 'error', "message": f"Path '{file_name}' does not exist."})
            functions.safe_remove(file_name)
            return JSONResponse({"message": f"Scenario '{file}' was deleted successfully!"})
    except Exception as e:
        print('/delete_file:\n==============')
        traceback.print_exc()
        return JSONResponse({"message": f"Error: {str(e)}"})
    finally:
        if extend_task:
            extend_task.cancel()
            try: await extend_task
            except asyncio.CancelledError: pass

# Delete a project
@router.post("/delete_project")
async def delete_project(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        redis = request.app.state.redis
        name = project_name if '/' not in project_name else project_name.split('/')[-1]
        lock = redis.lock(f"{project_name}:delete_project", timeout=600)
        project_folder, extend_task = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name)), None        
        async with lock:
            # Optional: auto-extend lock if deletion may take long
            extend_task = asyncio.create_task(functions.auto_extend(lock))
            if not os.path.exists(project_folder): 
                return JSONResponse({"status": 'error', "message": f"Project '{project_name}' does not exist."})
            try:
                shutil.rmtree(project_folder, onerror=functions.remove_readonly)
                # Optional: remove project cache in app.state if exists
                if hasattr(request.app.state, "project_cache"):
                    request.app.state.project_cache.pop(project_name, None)
                return JSONResponse({"status": "ok", "message": f"Project '{name}' was deleted successfully."})
            except PermissionError as e:
                try:
                    subprocess.run(['rmdir', '/s', '/q', project_folder], shell=True, check=True)
                    return JSONResponse({"status": "ok", "message": f"Project '{name}' was deleted successfully."})
                except subprocess.CalledProcessError as e2:
                    return JSONResponse({"status": "error", "message": f"Error: {str(e2)}"})
            except Exception as e:
                return JSONResponse({"status": "error", "message": f"Error: {str(e)}"})
    except Exception as e:
        print('/delete_project:\n==============')
        traceback.print_exc()
        return JSONResponse({"status": 'error', "message": f"Error: {str(e)}"})
    finally:
        if extend_task:
            extend_task.cancel()
            try: await extend_task
            except asyncio.CancelledError: pass

# Delete a Water Quality file
@router.post("/delete_waq")
async def delete_waq(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        file_name = body.get('fileName')
        project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "WAQ"))
        found_files = [f for f in os.listdir(project_folder)]
        if len(found_files) == 0: 
            return JSONResponse({"status": 'error', "message": f"File '{file_name}' does not exist."})
        for f in found_files:
            file = os.path.normpath(os.path.join(project_folder, f))
            if os.path.exists(file):
                if f.endswith('.json'): functions.safe_remove(file)
                else: shutil.rmtree(file, onerror=functions.remove_readonly)
        return JSONResponse({"status": "ok", "message": f"File '{file_name}' was deleted successfully."})
    except Exception as e:
        print('/delete_waq:\n==============')
        traceback.print_exc()
        return JSONResponse({"status": 'error', "message": f"Error: {str(e)}"})

# Open a project
@router.post("/select_project")
async def select_project(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        key, folder_check = body.get('key'), body.get('folder_check')
        project_name = functions.project_definer(body.get('filename'), user)
        if key == 'getProjects': # List the projects in a folder that contains the "folder_check"
            project = [p.name for p in os.scandir(os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))) if p.is_dir()]
            project = [p for p in project if os.path.exists(os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, p, folder_check)))]
            data = sorted(project)
        elif key == 'getWAQs': # List the scenarios for water quality
            project = [p.name for p in os.scandir(os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, 'output', 'scenarios')))]
            project = [p.replace('.json', '') for p in project if os.path.exists(os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, 'output', 'scenarios', p)))]
            data = sorted(project)
        elif key == 'getFiles': # List the files
            project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))
            hyd_folder = os.path.normpath(os.path.join(project_folder, "output", 'HYD'))
            waq_folder = os.path.normpath(os.path.join(project_folder, "output", 'WAQ'))
            hyd_files, waq_files = [], []
            if os.path.exists(hyd_folder):
                hyd_files = [f for f in os.listdir(hyd_folder) if f.endswith(".zarr")]
                hyd_files = set([f.replace('_his.zarr', '').replace('_map.zarr', '') for f in hyd_files])
            if os.path.exists(waq_folder):
                waq_files = [f for f in os.listdir(waq_folder) if f.endswith(".json")]
                waq_files = set([f.replace('.json', '') for f in waq_files])
            data = {'hyd': list(hyd_files), 'waq': sorted(list(waq_files))}
        status, message = 'ok', 'JSON loaded successfully.'
    except Exception as e:
        print('/select_project:\n==============')
        traceback.print_exc()
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

# Get list of files in a directory
@router.post("/get_files")
async def get_files():
    try:
        path = os.path.normpath(os.path.join(STATIC_DIR_BACKEND, 'samples', 'sources'))
        files = [f for f in os.listdir(path) if f.endswith(".csv")]
        data = [f.replace('.csv', '') for f in files]
        status, message = 'ok', 'Files loaded successfully.'
    except Exception as e:
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

# Get a list of sources from CSV file in sample folder
@router.post("/get_source")
async def get_source(request: Request):
    try:
        body = await request.json()
        filename = body.get('filename')        
        path = os.path.normpath(os.path.join(STATIC_DIR_BACKEND, 'samples', 'sources'))
        file_path = os.path.normpath(os.path.join(path, f"{filename}.csv"))
        with open(file_path, 'r', encoding=functions.encoding_detect(file_path)) as f:
            lines = f.readlines()
        first_row = lines[0].strip().split(',')
        latitude, longitude = first_row[0], first_row[1]
        data_rows = lines[2:]
        data = {'lat': latitude, 'lon': longitude, 'data': data_rows}    
        status, message = 'ok', 'Source loaded successfully.'
    except Exception as e:
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

# Save observations data to project
@router.post("/save_obs")
async def save_obs(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        data, key, file_name = body.get('data'), body.get('key'), body.get('fileName')
        path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
        redis = request.app.state.redis
        lock = redis.lock(f"{project_name}:save_obs:{file_name}", timeout=10)
        def write_file(path, file_name, data, key):
            file_path = os.path.normpath(os.path.join(path, file_name))
            with open(file_path, 'w', encoding=functions.encoding_detect(file_path)) as f:
                if key == 'obs':
                    for line in data:
                        f.write(f"{line[2]}  {line[1]}  '{line[0]}'\n")
                elif key == 'crs':
                    name = file_name.replace('_crs.pli', '')
                    data = np.array(data)
                    f.write(f"{name}\n")
                    f.write(f"    {data.shape[0]}    2\n")
                    for line in data:
                        f.write(f"{line[2]}  {line[1]}  {line[0]}\n")
        async with lock:
            await asyncio.to_thread(write_file, path, file_name, data, key)
            status, message = 'ok', 'Observations saved successfully.'
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Save source to CSV file
@router.post("/save_source")
async def save_source(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        lat, lon, BCCheck = body.get('lat'), body.get('lon'), body.get('BC')
        data, source_name = body.get('data'), body.get('nameSource')
        redis = request.app.state.redis
        lock = redis.lock(f"{project_name}:save_source:{source_name}", timeout=10)
        path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))        
        async with lock:
            os.makedirs(path, exist_ok=True)
            update_content = 'QUANTITY=discharge_salinity_temperature_sorsin\n' + \
                f'FILENAME={source_name}.pli\n' + 'FILETYPE=9\n' + 'METHOD=1\n' + 'OPERAND=O\n' + 'AREA=1'
            # Write old format boundary file (*.ext)
            ext_path = os.path.normpath(os.path.join(path, "FlowFM.ext"))
            if os.path.exists(ext_path):
                with open(ext_path, 'r', encoding=functions.encoding_detect(ext_path)) as f:
                    content = f.read()
                blocks = re.split(r'\n\s*\n', content)
                blocks = [p.strip() for p in blocks if p.strip()]
                updated = False
                for i, block in enumerate(blocks):
                    if f'FILENAME={source_name}.pli' in block:
                        blocks[i] = update_content
                        updated = True
                        break
                if not updated:
                    blocks.append(update_content)
                new_content = '\n\n'.join(blocks)
            else: new_content = f"\n{update_content}\n"
            with open(ext_path, 'w', encoding=functions.encoding_detect(ext_path)) as f:
                f.write(new_content.strip() + "\n")
            # Write .pli file
            pli_path = os.path.normpath(os.path.join(path, f"{source_name}.pli"))
            with open(pli_path, 'w', encoding=functions.encoding_detect(pli_path)) as f:
                f.write(f'{source_name}\n')
                f.write('    1    2\n')
                f.write(f"{lon}  {lat}\n")
            # Write .tim file
            tim_path = os.path.normpath(os.path.join(path, f"{source_name}.tim"))
            with open(tim_path, 'w', encoding=functions.encoding_detect(tim_path)) as f:
                for row in data:
                    try: t = float(row[0])/(1000.0*60.0)
                    except Exception: t = 0
                    if int(BCCheck)==1: values = [str(t)] + [str(r) for r in row[1:]]
                    else: values = [str(t)] + [str(r) for r in row[1:-1]]
                    f.write('  '.join(values) + '\n')
            return JSONResponse({"status": 'ok', "message": f"Source '{source_name}' saved successfully."})
    except Exception as e:
        return JSONResponse({"status": 'error', "message": f"Error: {str(e)}"})

# Get list of source from .ext file
@router.post("/init_source")
async def init_source(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, key = functions.project_definer(body.get('projectName'), user), body.get('key')
    path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input", "FlowFM.ext"))
    if os.path.exists(path):
        with open(path, 'r', encoding=functions.encoding_detect(path)) as f:
            content = f.read()
        parts = re.split(r'\n\s*\n', content)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) == 0: 
            os.remove(path)
            return JSONResponse({"status": 'error', "content": [], "type": []})
        lts = [re.search(r'FILENAME=(.+?)\.pli', p).group(1) for p in parts if re.search(r'FILENAME=(.+?)\.pli', p)]
        if len(lts) == 0: return JSONResponse({"status": 'error', "content": [], "type": []})        
        if not key == '':
            check = [i[0] for i in key]
            item_remove = [p for p in lts if p not in check]
            if len(item_remove) > 0:
                item_remove = item_remove[0]
                temp_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
                for part in parts:
                    if item_remove in part:
                        parts.remove(part)
                        pli_path = os.path.normpath(os.path.join(temp_path, f"{item_remove}.pli"))
                        tim_path = os.path.normpath(os.path.join(temp_path, f"{item_remove}.tim"))
                        if os.path.exists(pli_path): os.remove(pli_path)
                        if os.path.exists(tim_path): os.remove(tim_path)
            with open(path, 'w', encoding=functions.encoding_detect(path)) as file:
                joined_parts = '\n\n'.join(parts)
                file.write(f"\n{joined_parts}\n")
        status, data, type = 'ok', [], []
        for part in parts:
            if 'QUANTITY=discharge_salinity_temperature_sorsin' in part:
                match = re.search(r'FILENAME=(.+?)\.pli', part)
                if match:
                    data.append(match.group(1))
                    type.append('discharge_salinity_temperature_sorsin')
    else: status, data, type = 'error', [], []
    return JSONResponse({"status": status, "content": data, "type": type})

# Save meteo data to project
@router.post("/save_meteo")
async def save_meteo(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, data = functions.project_definer(body.get('projectName'), user), body.get('data')
    content = 'QUANTITY=humidity_airtemperature_cloudiness_solarradiation\n' + \
            'FILENAME=FlowFM_meteo.tim\n' + 'FILETYPE=1\n' + 'METHOD=1\n' + 'OPERAND=O'
    # Time difference in minutes
    status, message = functions.contentWriter(project_name, "FlowFM_meteo.tim", data, content, 'min')
    return JSONResponse({"status": status, "message": message})

# Save meteo data to project
@router.post("/save_weather")
async def save_weather(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, data = functions.project_definer(body.get('projectName'), user), body.get('data')
    content = 'QUANTITY=windxy\n' + 'FILENAME=windxy.tim\n' + 'FILETYPE=2\n' + 'METHOD=1\n' + 'OPERAND=+'
    # Time difference in minutes
    status, message = functions.contentWriter(project_name, "windxy.tim", data, content, 'min')
    return JSONResponse({"status": status, "message": message})