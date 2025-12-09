import os, shutil, subprocess, re, json, msgpack
import asyncio, traceback
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
        project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))
        name = project_name if '/' not in project_name else project_name.split('/')[1]
        # Check if project already exists
        if os.path.exists(project_folder):
            return JSONResponse({"status": 'ok', "message": f"Project '{name}' already exists."})        
        # Create project directories
        os.makedirs(body.get('projectName'), exist_ok=True)
        os.makedirs(project_folder, exist_ok=True)
        os.makedirs(os.path.normpath(os.path.join(project_folder, "input")), exist_ok=True)
        status, message = 'ok', f"Project '{name}' created successfully!"
    except Exception as e:
        print('/setup_new_project:\n==============')
        traceback.print_exc()
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Set up the database depending on the project
@router.post("/setup_database")
async def setup_database(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        redis, params = request.app.state.redis, body.get('params')
        extend_task, lock = None, redis.lock(f"{project_name}:setup_database", timeout=300)
        async with lock:
            extend_task = asyncio.create_task(functions.auto_extend(lock, interval=10))
            project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))
            demo_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, 'demo'))
            if user != 'admin':
                if not os.path.exists(project_folder): 
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
                config = json.loads(open(config_path).read())
            else:
                print('Config doesn\'t exist. Creating...')
                config = {"hyd": {}, "waq": {}, "meta": {"hyd_scanned": False, "waq_scanned": False}, "model_type": ''}
                if os.path.exists(config_path): os.remove(config_path)
                open(config_path, "w").write(json.dumps(config))
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
                    json.dump(layer_reverse_hyd, open(layer_path, "w"))                    
                else: layer_reverse_hyd = json.load(open(layer_path))
            if waq_map:
                print('Creating grid and layers for water quality simulation...')
                layer_path = os.path.normpath(os.path.join(config_dir, 'layers_waq.json'))
                if not os.path.exists(layer_path):
                    layer_reverse_waq = functions.layerCounter(waq_map, 'waq')
                    json.dump(layer_reverse_waq, open(layer_path, "w"))                    
                else: layer_reverse_waq = json.load(open(layer_path))
            # Lazy scan HYD variables only once
            if (hyd_map or hyd_his) and not config['meta']['hyd_scanned']:
                print('Scanning HYD variables...')
                hyd_vars = functions.getVariablesNames([hyd_his, hyd_map], 'hyd')
                config["hyd"], config["meta"]["hyd_scanned"] = hyd_vars, True
            # Get WAQ model
            temp = params[2].replace('_his.nc', '') if params[2] != '' else params[3].replace('_map.nc', '')
            model_path, waq_model, obs = os.path.normpath(os.path.join(waq_dir, f'{temp}.json')), '', {}
            if os.path.exists(model_path):
                print('Loading WAQ model...')
                temp_data = json.load(open(model_path))
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
            open(config_path, "w").write(json.dumps(config))
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

# Delete a project
@router.post("/delete_project")
async def delete_project(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name = functions.project_definer(body.get('projectName'), user)
        redis = request.app.state.redis
        name = project_name if '/' not in project_name else project_name.split('/')[-1]
        lock = redis.lock(f"{project_name}:delete_project", timeout=10)
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
        elif key == 'getFiles': # List the files
            project_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name))
            hyd_folder = os.path.normpath(os.path.join(project_folder, "output", 'HYD'))
            waq_folder = os.path.normpath(os.path.join(project_folder, "output", 'WAQ'))
            hyd_files, waq_files = [], []
            if os.path.exists(hyd_folder):
                hyd_files = [f for f in os.listdir(hyd_folder) if f.endswith(".nc")]
                hyd_files = set([f.replace('_his.nc', '').replace('_map.nc', '') for f in hyd_files])
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
        with open(os.path.normpath(os.path.join(path, f"{filename}.csv")), 'r') as f:
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
            with open(os.path.normpath(os.path.join(path, file_name)), 'w', encoding="utf-8") as f:
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
        lat, lon, data, source_name = body.get('lat'), body.get('lon'), body.get('data'), body.get('nameSource')
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
                with open(ext_path, encoding="utf-8") as f:
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
            with open(ext_path, 'w', encoding="utf-8") as f:
                f.write(new_content.strip() + "\n")
            # Write .pli file
            pli_path = os.path.normpath(os.path.join(path, f"{source_name}.pli"))
            with open(pli_path, 'w', encoding="utf-8") as f:
                f.write(f'{source_name}\n')
                f.write('    1    2\n')
                f.write(f"{lon}  {lat}\n")
            # Write .tim file
            tim_path = os.path.normpath(os.path.join(path, f"{source_name}.tim"))
            with open(tim_path, 'w', encoding="utf-8") as f:
                for row in data:
                    try: t = float(row[0])/(1000.0*60.0)
                    except Exception: t = 0
                    t = int(t)
                    values = [str(t)] + [str(r) for r in row[1:]]
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
        with open(path, encoding="utf-8") as f:
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
            with open(path, 'w', encoding="utf-8") as file:
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