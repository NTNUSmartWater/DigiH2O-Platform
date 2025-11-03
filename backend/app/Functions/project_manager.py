
import os, shutil, subprocess, re, json, asyncio
import numpy as np
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from Functions import functions
from config import PROJECT_STATIC_ROOT, STATIC_DIR_BACKEND

router = APIRouter()

# Create a new project with necessary folders
@router.post("/setup_new_project")
async def setup_new_project(request: Request):
    body = await request.json()
    project_name = body.get('projectName')
    project_folder = os.path.join(PROJECT_STATIC_ROOT, project_name)
    # Check if project already exists
    if os.path.exists(project_folder):
        return JSONResponse({"status": 'ok', "message": f"Project '{project_name}' already exists."})
    try:
        # Create project directories
        os.makedirs(project_folder, exist_ok=True)
        os.makedirs(os.path.join(project_folder, "input"), exist_ok=True)
        status, message = 'ok', f"Project '{project_name}' created successfully!"
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Set up the database depending on the project
@router.post("/setup_database")
async def setup_database(request: Request):
    body = await request.json()
    project_name, params = body.get('projectName'), body.get('params')
    loop = asyncio.get_running_loop()
    dm = request.app.state.dataset_manager
    # Set PROJECT_DIR
    project_folder = os.path.join(PROJECT_STATIC_ROOT, project_name)
    output_dir = os.path.join(project_folder, "output")
    config_dir = os.path.join(output_dir, "config")
    hyd_dir, waq_dir = os.path.join(output_dir, 'HYD'), os.path.join(output_dir, 'WAQ')
    request.app.state.PROJECT_DIR = project_folder
    request.app.state.templates = Jinja2Templates(directory="static/templates")
    try:
        os.makedirs(config_dir, exist_ok=True)
        # Reset app state
        request.app.state.hyd_his = request.app.state.hyd_map = None
        request.app.state.waq_his = request.app.state.waq_map = None
        # Load datasets asynchronously
        async def load_dataset(dir: str, filename: str):
            path = os.path.join(dir, filename)
            if os.path.exists(path): return await loop.run_in_executor(None, lambda: dm.get(path))
            return None
        # Assign datasets (only load if file path exists)
        mapping = [
            ('hyd_his', hyd_dir, params[0]), ('hyd_map', hyd_dir, params[1]),
            ('waq_his', waq_dir, params[2]), ('waq_map', waq_dir, params[3])
        ]
        for key, dir, filename in mapping:
            if filename: setattr(request.app.state, key, await load_dataset(dir, filename))
        # Load or init config
        config_path = os.path.join(config_dir, 'config.json')
        if os.path.exists(config_path) and os.path.getsize(config_path) > 0:
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {"hyd": {}, "waq": {}, "meta": {"hyd_scanned": False, "waq_scanned": False}}
            with open(config_path, "w") as f:
                json.dump(config, f)
        # Delete waq option if no waq files
        if request.app.state.waq_his is None and request.app.state.waq_map is None:
            config['waq'], config['meta']['waq_scanned'] = {}, False
            if "wq_obs" in config: del config["wq_obs"]
            if "wq_loads" in config: del config["wq_loads"]
        # Transfer data to app state
        if request.app.state.hyd_map is not None:
            # Grid/layers generation
            request.app.state.grid = functions.unstructuredGridCreator(request.app.state.hyd_map)
            # Get number of layers
            layer_path = os.path.join(config_dir, 'layers.json')
            if os.path.exists(layer_path):
                with open(layer_path, 'r') as f:
                    request.app.state.n_layers = json.load(f)
            else:
                request.app.state.n_layers = functions.layerCounter(request.app.state.hyd_map)
                with open(layer_path, 'w') as f:
                    json.dump(request.app.state.n_layers, f)
            request.app.state.layer_reverse = {v: k for k, v in request.app.state.n_layers.items()}
        # Lazy scan HYD variables only once
        if (request.app.state.hyd_map or request.app.state.hyd_his) and not config['meta']['hyd_scanned']:
            hyd_files = [request.app.state.hyd_his, request.app.state.hyd_map]
            hyd_vars = functions.getVariablesNames(hyd_files)
            config["hyd"], config["meta"]["hyd_scanned"] = hyd_vars, True
        # Get WAQ model
        temp = params[2].replace('_his.zarr', '') if params[2] != '' else params[3].replace('_map.zarr', '')
        model_path, waq_model = os.path.join(waq_dir, f'{temp}.json'), ''
        if os.path.exists(model_path):
            with open(model_path, 'r') as f:
                temp_data = json.load(f)
            waq_model, request.app.state.obs = temp_data['model_type'], {}
            if 'wq_obs' in temp_data: 
                config['wq_obs'], request.app.state.obs['wq_obs'] = True, temp_data['wq_obs']
            if 'wq_loads' in temp_data:
                config['wq_loads'], request.app.state.obs['wq_loads'] = True, temp_data['wq_loads']
        if (request.app.state.waq_his or request.app.state.waq_map) and waq_model == '':
            return JSONResponse({"status": 'error', "message": "Some WAQ-related parameters are missing.\nConsider running the model again."})  
        # Lazy scan WAQ
        if (request.app.state.waq_map or request.app.state.waq_his) and not config['meta']['waq_scanned']:
            waq_files = [request.app.state.waq_his, request.app.state.waq_map]
            waq_vars = functions.getVariablesNames(waq_files, waq_model)
            config["waq"], config["meta"]["waq_scanned"] = waq_vars, True
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f)
        # Restructure configuration
        result = {**config.get("hyd", {}), **config.get("waq", {})}
        for k, v in config.items():
            if k not in ("hyd", "waq", "meta"):
                result[k] = v
        request.app.state.config, status, message = result, 'ok', ''
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Delete a project
@router.post("/delete_project")
async def delete_project(request: Request):
    body = await request.json()
    project_name = body.get('projectName')
    project_folder = os.path.join(PROJECT_STATIC_ROOT, project_name)
    if not os.path.exists(project_folder): 
        return JSONResponse({"status": 'error', "message": f"Project '{project_name}' does not exist."})
    try:
        shutil.rmtree(project_folder, onexc=functions.remove_readonly)
        return JSONResponse({"status": "ok", "message": f"Project '{project_name}' was deleted successfully."})
    except PermissionError as e:
        if os.name == 'nt':
            try:
                subprocess.run(['rmdir', '/s', '/q', project_folder], shell=True, check=True)
                return JSONResponse({"status": "ok", "message": f"Project '{project_name}' was deleted successfully."})
            except subprocess.CalledProcessError as e2:
                return JSONResponse({"status": "error", "message": f"Error: {str(e2)}"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Error: {str(e)}"}) 

# Open a project
@router.post("/select_project")
async def select_project(request: Request):
    body = await request.json()
    project_name, key, folder_check = body.get('filename'), body.get('key'), body.get('folder_check')
    try:
        if key == 'getProjects': # List the projects that doesn't have a folder output
            project = [p.name for p in os.scandir(PROJECT_STATIC_ROOT) if p.is_dir()]
            project = [p for p in project if os.path.exists(os.path.join(PROJECT_STATIC_ROOT, p, folder_check))]
            data = sorted(project)
        elif key == 'getFiles': # List the files
            project_folder = os.path.join(PROJECT_STATIC_ROOT, project_name)
            hyd_folder = os.path.join(project_folder, "output", 'HYD')
            waq_folder = os.path.join(project_folder, "output", 'WAQ')
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
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

# Get list of files in a directory
@router.post("/get_files")
async def get_files():
    try:
        path = os.path.join(STATIC_DIR_BACKEND, 'samples', 'sources')
        files = [f for f in os.listdir(path) if f.endswith(".csv")]
        data = [f.replace('.csv', '') for f in files]
        status, message = 'ok', 'Files loaded successfully.'
    except Exception as e:
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

# Get a list of sources from CSV file in sample folder
@router.post("/get_source")
async def get_source(request: Request):
    body = await request.json()
    filename = body.get('filename')
    try:
        path = os.path.join(STATIC_DIR_BACKEND, 'samples', 'sources')
        with open(os.path.join(path, f"{filename}.csv"), 'r') as f:
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
async def save_obs(request: Request):
    body = await request.json()
    project_name, file_name = body.get('projectName'), body.get('fileName')
    data, key = body.get('data'), body.get('key')
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
    def write_file(path, file_name, data, key):
        with open(os.path.join(path, file_name), 'w', encoding="utf-8") as f:
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
    try:
        await asyncio.to_thread(write_file, path, file_name, data, key)
        status, message = 'ok', 'Observations saved successfully.'
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Save source to CSV file
@router.post("/save_source")
async def save_source(request: Request):
    body = await request.json()
    project_name, source_name = body.get('projectName'), body.get('nameSource')
    lat, lon, data = body.get('lat'), body.get('lon'), body.get('data')
    try:
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        os.makedirs(path, exist_ok=True)
        update_content = 'QUANTITY=discharge_salinity_temperature_sorsin\n' + \
            f'FILENAME={source_name}.pli\n' + 'FILETYPE=9\n' + 'METHOD=1\n' + 'OPERAND=O\n' + 'AREA=1'
        # Write old format boundary file (*.ext)
        ext_path = os.path.join(path, "FlowFM.ext")
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
        pli_path = os.path.join(path, f"{source_name}.pli")
        with open(pli_path, 'w', encoding="utf-8") as f:
            f.write(f'{source_name}\n')
            f.write('    1    2\n')
            f.write(f"{lon}  {lat}")
        # Write .tim file
        tim_path = os.path.join(path, f"{source_name}.tim")
        with open(tim_path, 'w', encoding="utf-8") as f:
            for row in data:
                try: t = float(row[0])/(1000.0*60.0)
                except Exception: t = 0
                values = [str(t)] + [str(r) for r in row[1:]]
                f.write('  '.join(values) + '\n')
        return JSONResponse({"status": 'ok', "message": f"Source '{source_name}' saved successfully."})
    except Exception as e:
        return JSONResponse({"status": 'error', "message": f"Error: {str(e)}"})

# Get list of source from .ext file
@router.post("/init_source")
async def init_source(request: Request):
    body = await request.json()
    project_name, key = body.get('projectName'), body.get('key')
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input", "FlowFM.ext")
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
                temp_path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
                for part in parts:
                    if item_remove in part:
                        parts.remove(part)
                        pli_path = os.path.join(temp_path, f"{item_remove}.pli")
                        tim_path = os.path.join(temp_path, f"{item_remove}.tim")
                        if os.path.exists(pli_path): os.remove(pli_path)
                        if os.path.exists(tim_path): os.remove(tim_path)
            with open(path, 'w', encoding="utf-8") as file:
                file.write(f"\n{'\n\n'.join(parts)}\n")
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
async def save_meteo(request: Request):
    body = await request.json()
    project_name, data = body.get('projectName'), body.get('data')
    content = 'QUANTITY=humidity_airtemperature_cloudiness_solarradiation\n' + \
            'FILENAME=FlowFM_meteo.tim\n' + 'FILETYPE=1\n' + 'METHOD=1\n' + 'OPERAND=O'
    # Time difference in minutes
    status, message = functions.contentWriter(project_name, "FlowFM_meteo.tim", data, content, 'min')
    return JSONResponse({"status": status, "message": message})

# Save meteo data to project
@router.post("/save_weather")
async def save_weather(request: Request):
    body = await request.json()
    project_name, data = body.get('projectName'), body.get('data')
    content = 'QUANTITY=windxy\n' + 'FILENAME=windxy.tim\n' + 'FILETYPE=2\n' + 'METHOD=1\n' + 'OPERAND=+'
    # Time difference in minutes
    status, message = functions.contentWriter(project_name, "windxy.tim", data, content, 'min')
    return JSONResponse({"status": status, "message": message})