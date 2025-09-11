from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os, json, shutil, stat, subprocess, re
import xarray as xr, numpy as np
from fastapi.templating import Jinja2Templates
from Functions import functions
from config import PROJECT_STATIC_ROOT, ROOT_DIR
from datetime import datetime, timezone

router = APIRouter()
templates = Jinja2Templates(directory="static/templates")


# Create a new project with necessary folders
@router.post("/setup_new_project")
async def setup_new_project(request: Request):
    body = await request.json()
    project_name = body.get('projectName')
    project_path = os.path.join(PROJECT_STATIC_ROOT, project_name)
    # Check if project already exists
    if os.path.exists(project_path):
        return JSONResponse({"status": 'ok', "message": f"Project '{project_name}' already exists."})
    try:
        # Create project directories
        os.makedirs(project_path, exist_ok=True)
        os.makedirs(os.path.join(project_path, "common_files"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "input"), exist_ok=True)
        status, message = 'ok', f"Project '{project_name}' created successfully!"
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Delete a project
@router.post("/delete_project")
async def delete_project(request: Request):
    body = await request.json()
    project_name = body.get('projectName')
    project_path = os.path.join(PROJECT_STATIC_ROOT, project_name)
    if not os.path.exists(project_path):
        status, message = 'error', f"Project '{project_name}' does not exist."
    else:
        # Remove read-only attribute if set
        def remove_readonly(func, path, _):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        try:
            shutil.rmtree(project_path, onexc=remove_readonly)
            status, message = 'ok', f"Project '{project_name}' was deleted successfully."
        except:
            if os.name == 'nt':
                try:
                    subprocess.run(['rmdir', '/s', '/q', project_path], shell=True, check=True)
                    return JSONResponse({"status": "ok", "message": f"Project '{project_name}' was deleted successfully."})
                except Exception as e2:
                    return JSONResponse({"status": "error", "message": f"Error: {str(e2)}"})
    return JSONResponse({"status": status, "message": message})

# Open a project
@router.post("/select_project")
async def select_project(request: Request):
    body = await request.json()
    project_name, key, folder_check = body.get('filename'), body.get('key'), body.get('folder_check')
    try:
        if key == 'getProjects': # List the projects that doesn't have a folder output
            project = [p.name for p in os.scandir(PROJECT_STATIC_ROOT) if p.is_dir()]
            # Check if folder ouput exists
            for p in project:
                if not os.path.exists(os.path.join(PROJECT_STATIC_ROOT, p, folder_check)):
                    project.remove(p)
            data = sorted(project)
        elif key == 'getFiles': # List the files
            project_path = os.path.join(PROJECT_STATIC_ROOT, project_name)
            data = [f for f in os.listdir(os.path.join(project_path, "output")) if f.endswith(".nc")]
        status, message = 'ok', 'JSON loaded successfully.'
    except Exception as e:
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

# Set up the database depending on the project
@router.post("/setup_database")
async def setup_database(request: Request):
    body = await request.json()
    project_name, files = body.get('projectName'), body.get('files')
    try:
        # Set BASE_DIR
        project_path = os.path.join(PROJECT_STATIC_ROOT, project_name)
        request.app.state.BASE_DIR = project_path
        request.app.state.project_selected = project_name
        # Templates
        templates_dir = os.path.join(project_path, "templates")
        request.app.state.templates = Jinja2Templates(directory=templates_dir)
        # Load NetCDF
        output_dir = os.path.join(project_path, "output")
        request.app.state.data_his = xr.open_dataset(os.path.join(output_dir, files[0])) if len(files[0]) > 0 else None
        request.app.state.data_map = xr.open_dataset(os.path.join(output_dir, files[1])) if len(files[1]) > 0 else None
        if request.app.state.data_map:
            # Grid / layers
            request.app.state.grid = functions.unstructuredGridCreator(request.app.state.data_map)
            request.app.state.n_layers = functions.velocityChecker(request.app.state.data_map)
            path = os.path.join(PROJECT_STATIC_ROOT, project_name, "common_files", "velocity_layers.json")
            with open(path, 'w') as f:
                json.dump(request.app.state.n_layers, f)
            request.app.state.layer_reverse = {v: k for k, v in request.app.state.n_layers.items()}
        request.app.state.data_wq_his = xr.open_dataset(os.path.join(output_dir, files[2])) if len(files[2]) > 0 else None
        request.app.state.data_wq_map = xr.open_dataset(os.path.join(output_dir, files[3])) if len(files[3]) > 0 else None
        data = project_name
        status, message = 'ok', 'JSON loaded successfully.'
    except Exception as e:
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

# Load popup menu
@router.get("/load_popupMenu", response_class=HTMLResponse)
async def load_popupMenu(request: Request, htmlFile: str):
    if htmlFile == 'project_menu.html':
        return templates.TemplateResponse(htmlFile, {"request": request})
    if not request.app.state.templates:
        return HTMLResponse("<p>No project selected</p>", status_code=400)
    template_path = os.path.join(ROOT_DIR, "static", "templates", htmlFile)
    if not os.path.exists(template_path):
        return HTMLResponse(f"<p>Popup menu template not found</p>", status_code=404)
    config_file = os.path.join(request.app.state.BASE_DIR, "common_files", "configuration.json")
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            configuration = json.load(f)
    else:
        configuration = {}
        NCfiles = [
            request.app.state.data_his, request.app.state.data_map, 
            request.app.state.data_wq_his, request.app.state.data_wq_map
        ]
        for file in NCfiles:
            if file: configuration.update(functions.getVariablesNames(file))
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(configuration, f)
    return templates.TemplateResponse(htmlFile, 
            {"request": request, 'configuration': configuration})

# Get list of files in a directory
@router.post("/get_files")
async def get_files():
    try:
        path = os.path.join(ROOT_DIR, 'static', 'samples', 'sources')
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
        path = os.path.join(ROOT_DIR, 'static', 'samples', 'sources')
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
    try:
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        with open(os.path.join(path, file_name), 'w') as f:
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
        status, message = 'ok', 'Observations saved successfully.'
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Save source to CSV file
@router.post("/save_source")
async def save_source(request: Request):
    body = await request.json()
    project_name, source_name, key = body.get('projectName'), body.get('nameSource'), body.get('key')
    ref_date, lat, lon, data = body.get('refDate'), body.get('lat'), body.get('lon'), body.get('data')
    seconds = int(ref_date)/1000.0
    t_ref = datetime.fromtimestamp(seconds, tz=timezone.utc)
    try:
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        if key == 'saveSource':
            update_content = 'QUANTITY=discharge_salinity_temperature_sorsin\n' + \
                f'FILENAME={source_name}.pli\n' + 'FILETYPE=9\n' + 'METHOD=1\n' + 'OPERAND=O\n' + 'AREA=1'
        # Write old format boundary file (*.ext)
        ext_path = os.path.join(path, "FlowFM.ext")
        if os.path.exists(ext_path):
            with open(ext_path, encoding="utf-8") as f:
                content = f.read()
            parts = re.split(r'\n\s*\n', content)
            parts = [p.strip() for p in parts if p.strip()]
            if (any(source_name in part for part in parts)): 
                index = parts.index([part for part in parts if source_name in part][0])
                parts[index] = update_content
            else: parts.append(update_content)
            with open(ext_path, 'w') as file:
                file.write(f"\n{'\n\n'.join(parts)}\n")
        else:
            with open(ext_path, 'w') as f:
                f.write(f"\n{update_content}\n")
        # Write .pli file
        with open(os.path.join(path, f"{source_name}.pli"), 'w') as f:
            f.write(f'{source_name}\n')
            f.write('    1    2\n')
            f.write(f"{lon}  {lat}")
        # Write .tim file
        with open(os.path.join(path, f"{source_name}.tim"), 'w') as f:
            for row in data:
                t = datetime.fromtimestamp(int(row[0])/1000.0, tz=timezone.utc)
                row[0] = int((t - t_ref).total_seconds()/60.0)
                temp = '  '.join([str(r) for r in row])
                f.write(f"{temp}\n")
        status, message = 'ok', f"Source '{source_name}' saved successfully."
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

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
            with open(path, 'w') as file:
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
    project_name, ref_time, data = body.get('projectName'), body.get('refDate'), body.get('data')
    content = 'QUANTITY=humidity_airtemperature_cloudiness_solarradiation\n' + \
            'FILENAME=FlowFM_meteo.tim\n' + 'FILETYPE=1\n' + 'METHOD=1\n' + 'OPERAND=O'
    # Time difference in minutes
    status, message = functions.contentWriter(project_name, "FlowFM_meteo.tim", data, content, ref_time, 'min')
    return JSONResponse({"status": status, "message": message})

# Save meteo data to project
@router.post("/save_weather")
async def save_weather(request: Request):
    body = await request.json()
    project_name, ref_time, data = body.get('projectName'), body.get('refDate'), body.get('data')
    content = 'QUANTITY=windxy\n' + 'FILENAME=windxy.tim\n' + 'FILETYPE=2\n' + 'METHOD=1\n' + 'OPERAND=+'
    # Time difference in minutes
    status, message = functions.contentWriter(project_name, "windxy.tim", data, content, ref_time, 'min')
    return JSONResponse({"status": status, "message": message})