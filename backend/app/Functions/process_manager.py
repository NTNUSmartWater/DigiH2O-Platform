import os, json, re, requests, math, asyncio, traceback, subprocess
from fastapi import APIRouter, Request, File, UploadFile, Form
from Functions import functions
from shapely.geometry import mapping
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, STATIC_DIR_BACKEND, GRID_PATH, WINDOWS_AGENT_URL
import xarray as xr, pandas as pd, numpy as np, geopandas as gpd

router = APIRouter()

# Process data
def process_internal(request: Request, query: str, key: str):
    # Internal function to process data
    message = ''
    if key == 'summary':
        dia_path = os.path.join(request.app.state.PROJECT_DIR, "output", "HYD", "FlowFM.dia")
        data_his = [request.app.state.hyd_his, request.app.state.waq_his]
        data = functions.getSummary(dia_path, data_his)
    elif key == 'hyd_station':
        temp, message = functions.hydCreator(request.app.state.hyd_his)
        data = json.loads(temp.to_json())
    elif key in ['wq_obs', 'wq_loads']:
        data = json.loads(functions.obsCreator(request.app.state.obs[key]).to_json())
    elif key == 'sources':
        data = json.loads(functions.sourceCreator(request.app.state.hyd_his).to_json())
    elif key == 'crosssections':
        temp, message = functions.crosssectionCreator(request.app.state.hyd_his)
        data = json.loads(temp.to_json())
    elif key == '_in-situ':
        temp = query.split('*')
        name, stationId, type = temp[0], temp[1], temp[2]
        temp = functions.selectInsitu(request.app.state.hyd_his, request.app.state.hyd_map, name, stationId, type)
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
    elif key == 'static':
        # Create static data for map
        grid = request.app.state.grid.copy()
        x = request.app.state.hyd_map['mesh2d_node_x'].data.compute()
        y = request.app.state.hyd_map['mesh2d_node_y'].data.compute()
        z = request.app.state.hyd_map['mesh2d_node_z'].data.compute()
        if 'depth' in query: values = functions.interpolation_Z(grid, x, y, z)
        # Convert GeoDataFrame to expected format
        features = [{ "type": "Feature", "properties": {"index": idx}, "geometry": mapping(row["geometry"])
            } for idx, row in grid.iterrows()]
        data = { 'meshes': { 'type': 'FeatureCollection', 'features': features }}
        fnm = functions.numberFormatter
        data['values'], data['min_max'] = values, [fnm(np.nanmin(values)), fnm(np.nanmax(values))]
    elif key == 'substance_check':
        substance = request.app.state.config[query]
        if len(substance) > 0:
            data, message = sorted(substance), functions.valueToKeyConverter(substance)
        else: data, message = None, f"No substance defined."
    elif key == 'substance':
        temp = functions.timeseriesCreator(request.app.state.waq_his, query.split(' ')[0], timeColumn='nTimesDlwq')
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
    else:
        # Create time series data
        temp = functions.timeseriesCreator(request.app.state.hyd_his, key)
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
    return message, data

@router.post("/process_data")
async def process_data(request: Request):
    # Get body data
    body = await request.json()
    query, key = body.get('query'), body.get('key')
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: process_internal(request, query, key))
        if result[1] is None: return JSONResponse({'status': 'error', 'message': result[0]})
        status, message, data = 'ok', result[0], result[1]
    except Exception as e:
        print('/process_data:\n==============')
        traceback.print_exc()
        status, message, data = 'error', f"Error: {e}", None
    return JSONResponse({'content': data, 'status': status, 'message': message})

# Load general dynamic data
@router.post("/load_general_dynamic")
async def load_general_dynamic(request: Request):
    # Get body data
    body = await request.json()
    query, key = body.get('query'), body.get('key')
    try:
        temp = query.split('|')
        is_hyd = temp[0] == '' # hydrodynamic or waq
        data_ = request.app.state.hyd_map if is_hyd else request.app.state.waq_map
        time_column = 'time' if is_hyd else 'nTimesDlwq'
        name = functions.variablesNames.get(key, key) if is_hyd else temp[0]
        values = data_[name].values
        # Setup cache
        dynamic_cache = getattr(request.app.state, 'dynamic_cache', {})
        group = 'hyd' if is_hyd else 'waq'
        if group not in dynamic_cache: 
            dynamic_cache[group] = {
                "layer_reverse": getattr(request.app.state, f'layer_reverse_{group}'), "layers": {}
            }
        group_cache = dynamic_cache[group]
        setattr(request.app.state, 'dynamic_cache', dynamic_cache)
        if 'single' in key: arr = values
        else:
            layer_reverse = group_cache['layer_reverse']
            value_type = layer_reverse[temp[1]]
            if value_type in group_cache['layers']: arr = group_cache['layers'][value_type]
            else:
                n_layers = len(layer_reverse)
                row_idx = n_layers - int(temp[1]) - 2
                if value_type == 'Average':
                    if is_hyd: temp_values = np.nanmean(values, axis=2)
                    else:
                        temp_name = name.split('_')
                        temp_values = data_[f"{temp_name[0]}_2d_{temp_name[1]}"].values
                else: temp_values = values[:, :, row_idx-1] if is_hyd else values[:, row_idx-1, :]
                group_cache['layers'][value_type] = temp_values
                arr = temp_values
        fmt = functions.numberFormatter 
        if temp[2] == 'load': # Initiate skeleton polygon for the first load
            if not hasattr(request.app.state, 'grid_features'):
                request.app.state.grid_features = [{
                    'type': 'Feature', 'properties': {"index": idx},
                    'geometry': mapping(row['geometry'])
                } for idx, row in request.app.state.grid.iterrows()]
            data = { 'meshes': { 'type': 'FeatureCollection', 'features': request.app.state.grid_features },
               'values': list(fmt(arr[-1, :])), 'min_max': [fmt(np.nanmin(values)), fmt(np.nanmax(values))],
               'timestamps': [pd.to_datetime(t).strftime('%Y-%m-%d %H:%M:%S') for t in data_[time_column].data]
            }
        else: # Update value of polygons
            data = {'values': list(fmt(arr[int(temp[2]),:]))}
        status, message = 'ok', ''
    except Exception as e:
        print('/load_general_dynamic:\n==============')
        traceback.print_exc()
        status, message, data = 'error', f"Error: {e}", None
    return JSONResponse({'content': data, 'status': status, 'message': message})

# Load vector dynamic data
@router.post("/load_vector_dynamic")
async def load_vector_dynamic(request: Request):
    body = await request.json()
    query, key = body.get('query'), body.get('key')
    try:
        layer_reverse = request.app.state.layer_reverse_hyd
        value_type, row_idx = layer_reverse[key], len(layer_reverse) - int(key) - 2
        data_ = request.app.state.hyd_map
        fnm = functions.numberFormatter
        if query == 'load': # Initiate skeleton polygon for the first load
            data = functions.vectorComputer(data_, value_type, row_idx)
            # Get global vmin and vmax
            if value_type == 'Average':
                vmin = fnm(np.nanmin(data_['mesh2d_ucmaga']))
                vmax = fnm(np.nanmax(data_['mesh2d_ucmaga']))
            else:
                vmin = fnm(np.nanmin(data_['mesh2d_ucmag']))
                vmax = fnm(np.nanmax(data_['mesh2d_ucmag']))
            data['timestamps'] = [pd.to_datetime(t).strftime('%Y-%m-%d %H:%M:%S')
                                  for t in data_['time'].values]
            data['min_max'] = [vmin, vmax]
        else:
            data = functions.vectorComputer(data_, value_type, row_idx, int(query))
        status, message = 'ok', ''
    except Exception as e:
        print('/load_vector_dynamic:\n==============')
        traceback.print_exc()
        status, message, data = 'error', f"Error: {e}", None
    return JSONResponse({'content': data, 'status': status, 'message': message})

# Select meshes based on ids
@router.post("/select_meshes")
async def select_meshes(request: Request):    
    body = await request.json()
    key, query, idx, points = body.get('key'), body.get('query'), body.get('idx'), body.get('points')
    try:
        if '_waq_multi_dynamic' in query: query = 'mesh2d_' + query[:-len('_waq_multi_dynamic')]
        is_hyd = key == 'hyd'
        data_ = request.app.state.hyd_map if is_hyd else request.app.state.waq_map
        name, status, message = functions.variablesNames.get(query, query), 'ok', ''
        fnm = functions.numberFormatter
        # Cache data
        if not hasattr(request.app.state, 'mesh_cache'):
            layers_values = np.array([float(v.split(' ')[1]) for k, v in request.app.state.layer_reverse_hyd.items() if int(k) >= 0])
            max_layer = float(max(layers_values, key=abs))
            n_rows = abs(math.ceil(max_layer/10)*10) if max_layer > 0 else abs(math.floor(max_layer/10)*10) + 1
            depth_idx = np.array([round(abs(d)) for d in layers_values])
            # Using mapping to increase performance
            index_map = {int(v): depth_idx.shape[0] - i - 1 for i, v in enumerate(depth_idx)}
            request.app.state.mesh_cache = { "layers_values": layers_values, "n_rows": n_rows,
                "depth_idx": depth_idx, "index_map": index_map, "max_layer": max_layer}
        if idx == 'load': # Initiate data for the first load
            cache = getattr(request.app.state, "mesh_cache", None)
            time_column = 'time' if is_hyd else 'nTimesDlwq'
            time_stamps = pd.to_datetime(data_[time_column]).strftime('%Y-%m-%d %H:%M:%S').tolist()
            points_arr, arr = np.array(points), data_[name].values[0,:,:]
            x_coords, y_coords = points_arr[:, 2], points_arr[:, 1]
            gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(x_coords, y_coords), crs=request.app.state.grid.crs)
            gdf['depth'] = functions.interpolation_Z(gdf, request.app.state.hyd_map['mesh2d_node_x'].values, 
                request.app.state.hyd_map['mesh2d_node_y'].values, request.app.state.hyd_map['mesh2d_node_z'].values
            )
            cache["df"] = gdf.drop(columns=['geometry'])
            frame = functions.meshProcess(is_hyd, arr, cache)
            global_vmin, global_vmax = fnm(np.nanmin(arr)), fnm(np.nanmax(arr))
            vmin, vmax = fnm(np.nanmin(frame)), fnm(np.nanmax(frame))
            data = {"timestamps": time_stamps, "distance": np.round(points_arr[:, 0], 0).tolist(), "values": fnm(frame), 
                    "depths": np.arange(0, frame.shape[0]) if cache["max_layer"] > 0 else np.arange(0, -frame.shape[0], -1).tolist(),
                    "global_minmax": [global_vmin, global_vmax], "local_minmax": [vmin, vmax]}
        else: # Load next frame
            cache = getattr(request.app.state, "mesh_cache", None)
            if cache is None: return JSONResponse({"status": 'error', "message": "Mesh cache is not initialized."})
            arr = data_[name].values[int(idx),:,:]
            frame = functions.meshProcess(is_hyd, arr, cache)
            vmin, vmax = fnm(np.nanmin(frame)), fnm(np.nanmax(frame))
            data = {"values": fnm(frame), "local_minmax": [vmin, vmax]}
    except Exception as e:
        print('/select_meshes:\n==============')
        traceback.print_exc()
        data, status, message = None, 'error', f"Error: {e}"
    return JSONResponse({'content': data, 'status': status, 'message': message}, headers={'Access-Control-Allow-Origin': '*'})

# Working with thermocline plots
@router.post("/select_thermocline")
async def select_thermocline(request: Request):
    body = await request.json()
    key, query, type_, idx = body.get('key'), body.get('query'), body.get('type'), body.get('idx')
    try:
        status, message = 'ok', ""
        is_hyd = key == 'thermocline_hyd'
        data_ = request.app.state.hyd_map if is_hyd else request.app.state.waq_map
        col_idx = 2 if is_hyd else 1
        name = functions.variablesNames.get(query, query)
        # Create cache for thermocline data
        if not hasattr(request.app.state, 'thermocline_cache'):
            request.app.state.thermocline_cache = {}
        # Initiate data for the first load
        if type_ == 'thermocline_grid':
            temp_grid, arr = request.app.state.grid, data_[name].values
            mask_all_nan = np.isnan(arr).all(axis=(0, col_idx))               
            removed_indices = np.where(mask_all_nan)[0]
            grid = temp_grid.drop(index=removed_indices).reset_index()
            data = json.loads(grid.to_json())
        elif type_ == 'thermocline_init':
            time_column = 'time' if is_hyd else 'nTimesDlwq'
            time_stamps = pd.to_datetime(data_[time_column]).strftime('%Y-%m-%d %H:%M:%S').tolist()
            layer_reverse = request.app.state.layer_reverse_hyd if is_hyd else request.app.state.layer_reverse_waq
            layers_values = [float(v.split(' ')[1]) for k, v in layer_reverse.items() if int(k) >= 0]
            max_values = int(abs(np.min(layers_values)))
            new_depth = [x + max_values for x in layers_values]
            arr, idx = data_[name].values, int(idx)
            # Remove polygons having Nan in all layers
            mask_all_nan = np.isnan(arr).all(axis=(0, col_idx))
            arr_filtered = arr[:, ~mask_all_nan, :] if is_hyd else arr[:, :, ~mask_all_nan]
            data_selected = arr_filtered[:, idx, :] if is_hyd else arr_filtered[:, :, idx]
            request.app.state.thermocline_cache = {"data": data_selected}
            values = [None if np.isnan(x) else functions.numberFormatter(x) for x in data_selected[0,:]]
            # Get the first frame for the first timestamp
            data = { "timestamps": time_stamps, "depths": new_depth, "values": values }
        elif type_ == 'thermocline_update':
            data_selected = request.app.state.thermocline_cache["data"]
            data = [None if np.isnan(x) else functions.numberFormatter(x) for x in data_selected[int(idx),:]]
    except Exception as e:
        print('/select_thermocline:\n==============')
        traceback.print_exc()
        data, status, message = None, 'error', f"Error: {e}"
    return JSONResponse({"status": status, "message": message, "content": data})

# Read grid
@router.post("/open_grid")
async def open_grid(request: Request):
    # Get body data
    body = await request.json()
    project_name, grid_name = body.get('projectName'), body.get('gridName')
    path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input", grid_name)
    def load_grid(path):
        temp_grid = xr.open_dataset(path, chunks={})
        return functions.unstructuredGridCreator(temp_grid).dissolve()
    try:
        loop = asyncio.get_event_loop()
        grid = await loop.run_in_executor(None, lambda: load_grid(path))
        data = json.loads(grid.to_json())
        status, message = 'ok', ""
    except FileNotFoundError:
        status, message, data = 'error', '- No grid file found.\n- Grid is not created yet.', None
    except Exception as e:
        print('/open_grid:\n==============')
        traceback.print_exc()
        status, message, data = 'error', f"Error: {str(e)}", None
    return JSONResponse({"status": status, "message": message, "content": data})

@router.post("/initiate_options")
async def initiate_options(request: Request):
    body = await request.json()
    key = body.get('key')
    try:
        status, message, data = 'ok', '', []
        if key == 'vector': data = functions.getVectorNames()
        elif key == 'layer_hyd' and request.app.state.layer_reverse_hyd is not None:
            data = [(idx, value) for idx, value in request.app.state.layer_reverse_hyd.items()]
        elif key == 'sigma_waq' and request.app.state.layer_reverse_waq is not None:
            data = [(idx, value) for idx, value in request.app.state.layer_reverse_waq.items()]
        elif key == 'thermocline_waq':
            item = [x for x in request.app.state.config.keys() 
                    if x.startswith('waq_map_') and x.endswith('_selector')]
            if len(item) > 0: data = request.app.state.config[item[0]]
    except Exception as e:
        print('/initiate_options:\n==============')
        traceback.print_exc()
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
        print('/upload_data:\n==============')
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)})
    finally: await file.close()
    
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
    temp_file = os.path.join(STATIC_DIR_BACKEND, 'samples', 'BC.bc')
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
            with open(ext_path, 'w', encoding="utf-8") as file:
                joined_parts = '\n\n'.join(parts)
                file.write(f"\n{joined_parts}\n")
                file.flush()
                os.fsync(file.fileno())
        else:   
            with open(ext_path, 'w', encoding="utf-8") as file:
                file.write(f"\n{file_content}\n")
                file.flush()
                os.fsync(file.fileno())
        # Write boundary file (*.pli)
        boundary_file = os.path.join(path, f"{boundary_name}.pli")
        bc.append(f'    {len(data_boundary)}    2')
        for row in data_boundary:
            temp = f'{row[2]}    {row[1]}    {row[0]}'
            bc.append(temp)
        with open(boundary_file, 'w', encoding="utf-8") as file:
            file.write('\n'.join(bc))
            file.flush()
            os.fsync(file.fileno())
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
            with open(file_path, 'w', encoding="utf-8") as file:
                joined_parts = '\n\n'.join(parts)
                file.write(f"\n{joined_parts}\n")
                file.flush()
                os.fsync(file.fileno())
        else:
            file_content = functions.fileWriter(temp_file, config)
            with open(file_path, 'w', encoding="utf-8") as file:
                file.write(file_content + '\n')
                file.flush()
                os.fsync(file.fileno())
        status, message = 'ok', f"Saved successfully: 'Sub-boundary: {subBoundaryName} - Type: {boundary_type}'."
    except Exception as e:
        print('/update_boundary:\n==============')
        traceback.print_exc()
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
        print('/view_boundary:\n==============')
        traceback.print_exc()
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
        print('/delete_boundary:\n==============')
        traceback.print_exc()
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
        status, message = 'ok', f"Project '{project_name}' created successfully!"
        project_name = params['project_name']
        # Create MDU file
        project_path = os.path.join(PROJECT_STATIC_ROOT, project_name, 'input')
        mdu_path = os.path.join(STATIC_DIR_BACKEND, 'samples', 'MDUFile.mdu')
        file_content = functions.fileWriter(mdu_path, params)
        # Write file
        with open(os.path.join(project_path, 'FlowFM.mdu'), 'w') as file:
            file.write(file_content)
    except Exception as e:
        print('/generate_mdu:\n==============')
        traceback.print_exc()
        status, message = 'error', f"Error: {str(e)}"
    return JSONResponse({"status": status, "message": message})

# Open Delft3D Grid Tool
@router.post("/open_gridTool")
async def open_gridTool(request: Request):
    await request.json()
    if not os.path.exists(GRID_PATH): return JSONResponse({"status": "error", "message": "Grid Tool not found."})
    if request.app.state.env == 'development': subprocess.Popen(GRID_PATH, shell=True)
    else:
        payload = {"action": "run_grid_tool", "path": GRID_PATH}
        try:
            res = requests.post(WINDOWS_AGENT_URL, json=payload, timeout=10)
            res.raise_for_status()
            return JSONResponse({"status": "ok", "message": ""})
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"Exception: {str(e)}"})