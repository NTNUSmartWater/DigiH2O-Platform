import os, json, re
from fastapi import APIRouter, Request, File, UploadFile, Form
from Functions import functions
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, ROOT_DIR
from Functions import project_manager
from datetime import datetime, timezone


router = APIRouter()

# Process data
@router.post("/process_data")
async def process_data(request: Request):
    # Get body data
    body = await request.json()
    data_filename, key = body.get('data_filename'), body.get('key')
    # Get project state
    BASE_DIR = request.app.state.BASE_DIR
    data_his = request.app.state.data_his
    data_map = request.app.state.data_map
    data_wq_his = request.app.state.data_wq_his
    data_wq_map = request.app.state.data_wq_map
    grid = request.app.state.grid
    layer_reverse = request.app.state.layer_reverse
    # Prepare temp files
    temp_folder = os.path.join(BASE_DIR, "common_files")
    temp_files = [f for f in os.listdir(temp_folder) 
        if os.path.isfile(os.path.join(temp_folder, f))] if os.path.exists(temp_folder) else []
    # Check if the file exists
    filename = [f for f in temp_files if f == data_filename]
    if filename:
        # Load the JSON/GeoJSON file that exists
        with open(filename[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        status, message = 'ok', 'JSON loaded successfully.'
    else:
        # File not found, need to read the NetCDF file
        project = ''
        try:
            if key == 'summary':
                dia_file = os.path.join(BASE_DIR, "output", "FlowFM.dia")
                data = functions.getSummary(dia_file, data_his, data_wq_map)
            elif key == 'stations':
                data = json.loads(functions.stationCreator(data_his).to_json())
                project = request.app.state.project_selected
            elif key == '_in-situ':
                temp = data_filename.split('*')
                name, stationId = temp[0], temp[1]
                temp = functions.selectInsitu(data_his, data_map, name, stationId)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            elif key == 'thermocline':
                temp = functions.thermoclineComputer(data_map)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            elif '_dynamic' in key:
                # Create dynamic data
                data_, time_column = data_map, 'time'
                if '_wq' in data_filename:
                    data_, time_column = data_wq_map, 'nTimesDlwq'
                temp_mesh = functions.assignValuesToMeshes(grid, data_, key, time_column)
                data = json.loads(temp_mesh.to_json())
            elif '_static' in key:
                # Create static data for map
                temp = grid.copy()
                if 'depth' in key:
                    x = data_map['mesh2d_node_x'].values
                    y = data_map['mesh2d_node_y'].values
                    z = data_map['mesh2d_node_z'].values
                    values = functions.interpolation_Z(temp, x, y, z)
                temp['value'] = values
                data = json.loads(temp.to_json())
            elif key == 'velocity':
                value_type = data_filename.replace('_velocity', '')
                idx = len(data_map['mesh2d_layer_z'].values) - int(layer_reverse[value_type]) - 1
                data = functions.velocityComputer(data_map, value_type, idx)
            else:
                # Create time series data
                data_ = data_wq_his if '_wq' in key else data_his
                temp = functions.timeseriesCreator(data_, key)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            status, message, project = 'ok', 'Data loaded successfully.', project
        except Exception as e:
            data, status, message, project = None, 'error', f"Error processing data: {e}", ''
    result = {'content': data, 'status': status, 'message': message, 'project': project}
    return JSONResponse(content=result)
    
@router.post("/select_polygon")
async def select_polygon(request: Request):
    body = await request.json()
    key, idx = body.get('key'), int(body.get('id'))
    data_map = request.app.state.data_map
    data_wq_map = request.app.state.data_wq_map
    try:
        data_, time_column, column_layer = data_map, 'time', 'mesh2d_layer_z'
        if '_wq' in key:
            time_column, data_, column_layer = 'nTimesDlwq', data_wq_map, 'mesh2d_layer_dlwq'
        temp = functions.selectPolygon(data_, idx, key, time_column, column_layer)
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
        status, message = 'ok', 'Data loaded successfully.'
    except:
        data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)

@router.post("/initiate_options")
async def initiate_options(request: Request):
    body = await request.json()
    key = body.get('key')
    BASE_DIR = request.app.state.BASE_DIR
    data_map = request.app.state.data_map
    try:
        if key == 'vector': data = functions.getVectorNames()
        elif key == 'velocity':
            # Try to file velocity checker file
            temp_folder = os.path.join(BASE_DIR, "common_files")
            temp_files = [f for f in os.listdir(temp_folder) 
                    if os.path.isfile(os.path.join(temp_folder, f))] if os.path.exists(temp_folder) else []
            filename = [f for f in temp_files if f == 'velocity_layers.json']
            if filename:
                with open(os.path.join(temp_folder, filename[0]), 'r', encoding='utf-8') as f:
                    temp = json.load(f)
            else:
                temp = functions.velocityChecker(data_map)
            data = [value for _, value in temp.items()]
        status, message = 'ok', 'Data loaded successfully.'
    except:
        data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)

# Upload file from local computer to server
@router.post("/upload_data")
async def upload_data(file: UploadFile = File(...), 
        projectName: str = Form(...), gridName: str = Form(...)):
    try:
        file_path = os.path.join(PROJECT_STATIC_ROOT, projectName, "input", gridName)
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk: break
                f.write(chunk)
        return JSONResponse({"status": "ok", 
            "message": f"File {file.filename} uploaded successfully."})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})
    
# Update boundary conditions
@router.post("/update_boundary")
async def update_boundary(request: Request):
    body = await request.json()
    project_name, subBoundaryName = body.get('projectName'), body.get('subBoundaryName')
    boundary_name, data_boundary = body.get('boundaryName'), body.get('boundaryData')
    boundary_type, data_sub, ref_date = body.get('boundaryType'), body.get('subBoundaryData'), body.get('refDate')
    if boundary_type == 'Contaminant': unit = '-'; quantity = 'tracerbndContaminant'
    else: unit = 'm'; quantity = 'waterlevelbnd'
    # Parse date
    ref_utc = datetime.strptime(ref_date, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    date_local = datetime.fromisoformat(ref_date).astimezone()
    temp_date = date_local.strftime('%Y-%m-%d %H:%M:%S')
    config = {'sub_boundary': subBoundaryName, 'ref_date': temp_date, 'boundary_type': quantity, 'unit': unit}
    temp_file = os.path.join(ROOT_DIR, 'static', 'samples', 'BC.bc')
    try:
        temp, bc = [], [boundary_name]
        for row in data_sub:
            t_utc = datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            row[0] = int((t_utc - ref_utc).total_seconds()); temp.append(row)
        lines = [f"{int(x)}  {y}" for x, y in temp]
        config['data'] = '\n'.join(lines)
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        # Write new format boundary file (*_bnd.ext)
        ext_path = os.path.join(path, "FlowFM_bnd.ext")
        file_content = '[boundary]\n' + f'quantity={quantity}\n' + f'locationFile={boundary_name}.pli\n' + \
            f'forcingFile={boundary_type}.bc\n' + 'returnTime=0.0000000e+000'
        if os.path.exists(ext_path):
            with open(ext_path, encoding="utf-8") as f:
                content = f.read()
            parts = re.split(r'(?=\[boundary\])', content)
            parts = [p.strip() for p in parts if p.strip()]
            if (any(boundary_type in part for part in parts)): 
                index = parts.index([part for part in parts if boundary_type in part][0])
                parts[index] = file_content
            else: parts.append(file_content)
            with open(ext_path, 'w') as file:
                file.write(f"\n{'\n\n'.join(parts)}\n")
        else:   
            with open(ext_path, 'w') as file:
                file.write(f"\n{file_content}\n")
        # Write boundary file (*.pli)
        boundary_file = os.path.join(path, f"{boundary_name}.pli")
        bc.append(f'    {len(data_boundary)}    2')
        for row in data_boundary:
            temp = f'{row[2]}    {row[1]}    {row[0]}'
            bc.append(temp)
        with open(boundary_file, 'w') as file:
            file.write('\n'.join(bc))
        # Write boundary conditions file
        file_path = os.path.join(path, f"{boundary_type}.bc")
        update_content = functions.fileWriter(temp_file, config)
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            parts = re.split(r'(?=\[forcing\])', content)  # Split the file content
            parts = [p.strip() for p in parts if p.strip()]  # Remove empty parts
            if (any(subBoundaryName in part for part in parts)): 
                index = parts.index([part for part in parts if subBoundaryName in part][0])
                parts[index] = update_content
            else: parts.append(update_content)                
            with open(file_path, 'w') as file:
                file.write('\n\n'.join(parts))
        else:
            file_content = functions.fileWriter(temp_file, config)
            with open(file_path, 'w') as file:
                file.write(file_content + '\n')
        status, message = 'ok', f"Saved successfully: 'Sub-boundary: {subBoundaryName} - Type: {boundary_type}'."
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# View boundary conditions
@router.post("/view_boundary")
async def view_boundary(request: Request):
    body = await request.json()
    project_name, boundary_type = body.get('projectName'), body.get('boundaryType')
    try:
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        # Read file
        with open(os.path.join(path, f"{boundary_type}.bc"), 'r') as f:
            data = ''.join(f.readlines())
        status, message = 'ok', ""
    except FileNotFoundError:
        status, message, data = 'error', '- No boundary condition found.\n- Boundary is not created yet.', None
    except Exception as e:
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

# Delete boundary conditions
@router.post("/delete_boundary")
async def delete_boundary(request: Request):
    body = await request.json()
    project_name, boundary_name = body.get('projectName'), body.get('boundaryName')
    try:
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        water_lelvel_path = os.path.join(path, "WaterLevel.bc")
        contaminant_path = os.path.join(path, "Contaminant.bc")
        boundary_path = os.path.join(path, f"{boundary_name}.pli")
        ext_path = os.path.join(path, "FlowFM_bnd.ext")
        # Delete file
        status, message = 'ok', ""
        if os.path.exists(boundary_path):
            os.remove(boundary_path)
            message += f"- Delete successfully: {boundary_name}'.pli.\n"
        if os.path.exists(ext_path):
            os.remove(ext_path)
            message += "- Delete successfully: FlowFM_bnd.ext.\n"
        if os.path.exists(water_lelvel_path):
            os.remove(water_lelvel_path)
            message += "- Delete successfully: WaterLevel.bc.\n"
        if os.path.exists(contaminant_path):
            os.remove(contaminant_path)
            message += "- Delete successfully: Contaminant.bc."     
    except Exception as e:
        status, message = 'error', f'Error: {str(e)}'
    return JSONResponse({"status": status, "message": message})

# Check boundary conditions
@router.post("/check_condition")
async def check_condition(request: Request):
    body = await request.json()
    project_name, force_name = body.get('projectName'), body.get('forceName')
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
    status, ext_path = 'error', os.path.join(path, force_name)
    if os.path.exists(ext_path): status = 'ok'
    return JSONResponse({"status": status})

# Create MDU file
@router.post("/generate_mdu")
async def generate_mdu(request: Request):
    body = await request.json()
    params = dict(body.get('params'))
    try:
        project_name = params['project_name']
        # Create MDU file
        project_path = os.path.join(PROJECT_STATIC_ROOT, project_name, 'input')
        mdu_path = os.path.join(ROOT_DIR, 'static', 'samples', 'MDUFile.mdu')
        file_content = functions.fileWriter(mdu_path, params)
        # Write file
        with open(os.path.join(project_path, 'FlowFM.mdu'), 'w') as file:
            file.write(file_content)
        status, message = 'ok', f"Project '{project_name}' created successfully!"
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})