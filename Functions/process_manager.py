import os, json, re, subprocess
from fastapi import APIRouter, Request, File, UploadFile, Form
from Functions import functions
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, ROOT_DIR
import xarray as xr

router = APIRouter()

# Process data
@router.post("/process_data")
async def process_data(request: Request):
    # Get body data
    body = await request.json()
    query, key = body.get('query'), body.get('key')
    # Get project state
    try:
        if key == 'summary':
            dia_path = os.path.join(request.app.state.PROJECT_DIR, "output", "FlowFM.dia")
            data_his = [request.app.state.hyd_his, request.app.state.waq_his]
            data = functions.getSummary(dia_path, data_his)
        elif key == 'hyd_station':
            data = json.loads(functions.stationCreator(request.app.state.hyd_his).to_json())
        elif key == 'wq_obs' or key == 'wq_loads':
            data = json.loads(functions.obsCreator(request.app.state.obs[key]).to_json())
        elif key == 'sources':
            data = json.loads(functions.sourceCreator(request.app.state.hyd_his).to_json())
        elif key == 'crosssections':
            data = json.loads(functions.crosssectionCreator(request.app.state.hyd_his).to_json())
        elif key == '_in-situ':
            temp = query.split('*')
            name, stationId, type = temp[0], temp[1], temp[2]
            temp = functions.selectInsitu(request.app.state.hyd_his, request.app.state.hyd_map, name, stationId, type)
            data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
        elif key == 'thermocline':
            temp = functions.thermoclineComputer(request.app.state.hyd_map)
            data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
        elif '_dynamic' in key:
            if query == '': data_, time_column = request.app.state.hyd_map, 'time' # For hydrodynamic data
            else: data_, time_column, key = request.app.state.waq_map, 'nTimesDlwq', query
            temp_mesh = functions.assignValuesToMeshes(request.app.state.grid, data_, key, time_column)
            data = json.loads(temp_mesh.to_json())
        elif '_static' in key:
            # Create static data for map
            temp = request.app.state.grid.copy()
            if 'depth' in key:
                x = request.app.state.hyd_map['mesh2d_node_x'].values
                y = request.app.state.hyd_map['mesh2d_node_y'].values
                z = request.app.state.hyd_map['mesh2d_node_z'].values
                values = functions.interpolation_Z(temp, x, y, z)
            temp['value'] = values
            data = json.loads(temp.to_json())
        elif key == 'velocity':
            value_type = query.replace('_velocity', '')
            layer_reverse = {v: k for k, v in request.app.state.n_layers.items()}
            data = functions.velocityComputer(request.app.state.hyd_map, value_type, layer_reverse)
        elif key == 'substance_check':
            substance = request.app.state.config[query]
            if len(substance) > 0: data, status, message = sorted(substance), 'ok', ''
            else: data, status, message = None, 'error', f"No substance defined."
            return JSONResponse({'content': data, 'status': status, 'message': message})
        elif key == 'substance':
            substance = query.split(' ')[0]
            temp = functions.timeseriesCreator(request.app.state.waq_his, substance, timeColumn='nTimesDlwq')
            data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
        else:
            # Create time series data
            temp = functions.timeseriesCreator(request.app.state.hyd_his, key)
            data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
        status, message = 'ok', ''
    except Exception as e:
        data, status, message = None, 'error', f"Error: {e}"
    return JSONResponse({'content': data, 'status': status, 'message': message})

# Read grid
@router.post("/open_grid")
async def open_grid(request: Request):
    # Get body data
    body = await request.json()
    project_name, grid_name = body.get('projectName'), body.get('gridName')
    try:
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input", grid_name)
        temp_grid = xr.open_dataset(path, chunks={})
        grid = functions.unstructuredGridCreator(temp_grid).dissolve()      
        data = json.loads(grid.to_json())       
        status, message = 'ok', ""
    except Exception as e:
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

@router.post("/select_polygon")
async def select_polygon(request: Request):
    body = await request.json()
    key, idx = body.get('key'), int(body.get('id'))
    try:
        data_, time_column, column_layer = request.app.state.hyd_map, 'time', 'mesh2d_layer_z'
        if '_multi_dynamic' in key:
            key = f"mesh2d_{key.replace('_multi_dynamic', '')}"
            data_, time_column, column_layer = request.app.state.waq_map, 'nTimesDlwq', 'mesh2d_layer_dlwq'
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
    try:
        if key == 'vector': data = functions.getVectorNames()
        elif key == 'velocity': data = [value for _, value in request.app.state.n_layers.items()]
        status, message = 'ok', ''
    except Exception as e:
        data, status, message = None, 'error', f"Error: {e}"
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
    boundary_type, data_sub = body.get('boundaryType'), body.get('subBoundaryData')
    if boundary_type == 'Contaminant': unit = '-'; quantity = 'tracerbndContaminant'
    else: unit = 'm'; quantity = 'waterlevelbnd'
    # Parse date
    config = {'sub_boundary': subBoundaryName, 'boundary_type': quantity, 'unit': unit}
    temp_file = os.path.join(ROOT_DIR, 'static', 'samples', 'BC.bc')
    try:
        temp, bc = [], [boundary_name]
        for row in data_sub:
            row[0] = int(row[0]/1000.0); temp.append(row)
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

# Open Delft3D Grid Tool
@router.post("/open_gridTool")
async def open_gridTool(request: Request):
    await request.json()
    try:
        path = r"C:\Program Files\Deltares\Delft3D FM Suite 2023.02 HMWQ\plugins\DeltaShell.Plugins.FMSuite.Common.Gui\plugins-qt\x64\rgfgrid.cmd"
        subprocess.Popen(path, shell=True)
        status, message = 'ok', ""
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})