import os, json, re, subprocess, math, asyncio, traceback
from fastapi import APIRouter, Request, File, UploadFile, Form
from Functions import functions
from shapely import wkt
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, STATIC_DIR_BACKEND, GRID_PATH
import xarray as xr, pandas as pd, numpy as np

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
    elif 'dynamic' in key:
        temp = query.split('|')
        if temp[0] == '': data_, time_column = request.app.state.hyd_map, 'time' # For hydrodynamic data
        else: data_, time_column = request.app.state.waq_map, 'nTimesDlwq' # For water quality
        name = functions.variablesNames.get(key, key) if time_column == 'time' else temp[0]
        # Detech layer and get values at the last timestamp
        if 'single' in key: arr = data_[name].values
        elif 'multi' in key:
            # Initiate cache for the first load
            if not hasattr(request.app.state, 'dynamic_cache'):
                layer_reverse = request.app.state.layer_reverse_waq if 'waq' in key else request.app.state.layer_reverse_hyd
                value_type = layer_reverse[temp[1]]
                request.app.state.dynamic_cache = {"layer_reverse": layer_reverse}
                if value_type == 'Average': 
                    if temp[0] == '': temp_values = np.nanmean(data_[name].values, axis=2)
                    else:
                        temp_name = name.split('_')
                        new_name = f"{temp_name[0]}_2d_{temp_name[1]}"
                        temp_values = data_[new_name].values
                else:
                    row_idx = len(layer_reverse) - int(temp[1]) - 2
                    if temp[0] == '': temp_values = data_[name].values[:, :, row_idx-1]
                    else: temp_values = data_[name].values[:, row_idx-1, :]
                if value_type not in request.app.state.dynamic_cache:
                    request.app.state.dynamic_cache[value_type] = temp_values
                arr = temp_values
            else:
                cache = request.app.state.dynamic_cache
                arr = cache[cache['layer_reverse'][temp[1]]]
        if temp[2] == 'load': # Initiate skeleton polygon for the first load
            # Get values at the last timestamp
            features = [
                {"type": "Feature", "properties": {"index": idx},
                    "geometry": {
                        "type": wkt.loads(row['geometry'].wkt).geom_type,
                        "coordinates": [list(row['geometry'].exterior.coords)]
                    }
                } for idx, row in request.app.state.grid.iterrows()
            ]
            vmin = functions.numberFormatter(np.nanmin(data_[name].values))
            vmax = functions.numberFormatter(np.nanmax(data_[name].values))
            data = {
                'meshes': { 'type': 'FeatureCollection', 'features': features },
                'values': list(functions.numberFormatter(arr[-1,:])), 'min_max': [vmin, vmax],
                'timestamps': [pd.to_datetime(t).strftime('%Y-%m-%d %H:%M:%S') for t in data_[time_column].data],
            }
        else: # Update value of polygons
            data = {'values': list(functions.numberFormatter(arr[int(temp[2]),:]))}
    elif key == 'static':
        # Create static data for map
        grid = request.app.state.grid.copy()
        x = request.app.state.hyd_map['mesh2d_node_x'].data.compute()
        y = request.app.state.hyd_map['mesh2d_node_y'].data.compute()
        z = request.app.state.hyd_map['mesh2d_node_z'].data.compute()
        if 'depth' in query:
            values = functions.interpolation_Z(grid, x, y, z)
        # Convert GeoDataFrame to expected format
        features = [
            {"type": "Feature", "id": idx,
                "properties": {"index": idx},   # index để tra values
                "geometry": {
                    "type": wkt.loads(row['geometry'].wkt).geom_type,
                    "coordinates": [list(row['geometry'].exterior.coords)]
                }
            } for idx, row in grid.iterrows()
        ]
        data = { 'meshes': { 'type': 'FeatureCollection', 'features': features }}
        data['values'], data['min_max'] = values, [float(np.nanmin(values)), float(np.nanmax(values))]
        data = functions.clean_nans(data)
    elif key == 'vector':
        temp = query.split('|')
        layer_reverse = request.app.state.layer_reverse_hyd
        value_type, row_idx = layer_reverse[temp[0]], len(layer_reverse) - int(temp[0]) - 2
        if temp[1] == 'load': # Initiate skeleton polygon for the first load
            data = functions.vectorComputer(request.app.state.hyd_map, value_type, row_idx)
            # Get global vmin and vmax
            if value_type == 'Average':
                vmin = float(np.nanmin(request.app.state.hyd_map['mesh2d_ucmaga']))
                vmax = float(np.nanmax(request.app.state.hyd_map['mesh2d_ucmaga']))
            else:
                vmin = float(np.nanmin(request.app.state.hyd_map['mesh2d_ucmag']))
                vmax = float(np.nanmax(request.app.state.hyd_map['mesh2d_ucmag']))
            data['timestamps'] = [pd.to_datetime(t).strftime('%Y-%m-%d %H:%M:%S')
                                  for t in request.app.state.hyd_map['time'].values]
            data['min_max'] = [vmin, vmax]
        else:
            data = functions.vectorComputer(request.app.state.hyd_map, value_type, row_idx, int(temp[1]))
        data = functions.clean_nans(data)
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

# Select meshes based on ids
@router.post("/select_meshes")
async def select_meshes(request: Request):    
    body = await request.json()
    key, query, ids, type = body.get('key'), body.get('query'), body.get('ids'), body.get('type')
    try:
        if key == 'hyd': data_, time_column = request.app.state.hyd_map, 'time'
        else:
            data_, time_column = request.app.state.waq_map, 'nTimesDlwq' # For water quality
            if '_waq_multi_dynamic' in query: query = f'mesh2d_{query.replace('_waq_multi_dynamic', '')}'
        name, status, message = functions.variablesNames.get(query, query), 'ok', ''
        # Cache data
        if not hasattr(request.app.state, 'mesh_cache'):
            temp_grid = request.app.state.grid
            temp_grid['depth'] = functions.interpolation_Z(temp_grid,
                request.app.state.hyd_map['mesh2d_node_x'].values, 
                request.app.state.hyd_map['mesh2d_node_y'].values,
                request.app.state.hyd_map['mesh2d_node_z'].values
            )
            filtered = temp_grid.loc[ids]  # Filter by ids
            n_layers_values = [float(v.split(' ')[1]) for k, v in request.app.state.layer_reverse_hyd.items() if int(k) >= 0]
            max_layer = max(n_layers_values, key=abs)
            n_rows, n_cols = len(ids), math.ceil(max_layer/10)*10 if max_layer > 0 else math.floor(max_layer/10)*10
            request.app.state.mesh_cache = {
                "depths": n_layers_values, "filled_grid": filtered.drop(columns=['geometry']), 
                "n_rows": n_rows, "n_cols": n_cols, "ids": ids
            }
        if type == 'load': # Initiate data for the first load
            time_stamps = pd.to_datetime(data_[time_column]).strftime('%Y-%m-%d %H:%M:%S').tolist()
            # Get the first frame
            frame_data = functions.meshProcess(key, data_, name, 0, ids, request.app.state.mesh_cache)
            data = {"timestamps": time_stamps, "ids": ids, "depths": frame_data[0], "values": frame_data[1]}
            global_arr, local_arr = data_[name].values[:, ids, :], np.array(frame_data[1], dtype=float)
            global_vmin = functions.numberFormatter(np.nanmin(global_arr))
            global_vmax = functions.numberFormatter(np.nanmax(global_arr))
            vmin = functions.numberFormatter(np.nanmin(local_arr))
            vmax = functions.numberFormatter(np.nanmax(local_arr))
            data["global_minmax"], data["local_minmax"] = [global_vmin, global_vmax], [vmin, vmax]
        else:
            cache = getattr(request.app.state, "mesh_cache", None)
            if cache is None: return JSONResponse({"status": 'error', "message": "Mesh cache is not initialized."})
            frame_data = functions.meshProcess(key, data_, name, int(type), cache["ids"], cache)
            local_arr = np.array(frame_data[1], dtype=float)
            vmin = functions.numberFormatter(np.nanmin(local_arr))
            vmax = functions.numberFormatter(np.nanmax(local_arr))
            data = {"values": frame_data[1], "local_minmax": [vmin, vmax]}
        data = functions.clean_nans(data)
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
        status, message, temp_grid = 'ok', "", request.app.state.grid
        name = functions.variablesNames.get(query, query)
        # Cache data
        if not hasattr(request.app.state, 'thermocline_cache'):
            # Select columns that are Nan in all layers
            if key == 'thermocline_hyd': 
                data_, col_idx, time_column = request.app.state.hyd_map, 2, 'time'
            else: 
                data_, col_idx, time_column = request.app.state.waq_map, 1, 'nTimesDlwq'
            layers_values = [float(v.split(' ')[1]) for k, v in request.app.state.layer_reverse_hyd.items() if int(k) >= 0]
            arr = data_[name].values
            mask_all_nan = np.isnan(arr).all(axis=(0, col_idx))
            arr_filtered = arr[:, ~mask_all_nan, :] if key == 'thermocline_hyd' else arr[:, :, ~mask_all_nan]
            removed_indices = np.where(mask_all_nan)[0]
            # Get grid with polygons having data
            grid = temp_grid.drop(index=removed_indices)
            time_stamps = pd.to_datetime(data_[time_column]).strftime('%Y-%m-%d %H:%M:%S').tolist()
            request.app.state.thermocline_cache = {"grid": grid, "timestamps": time_stamps,
                "data": arr_filtered, "depths": layers_values}
        if type_ == 'thermocline_grid':
            temp = request.app.state.thermocline_cache['grid']
            temp['index'] = temp.index
            data = json.loads(temp.to_json())
        elif type_ == 'thermocline_init':
            idx = int(idx)
            cache = getattr(request.app.state, "thermocline_cache", None)
            if cache is None: return JSONResponse({"status": 'error', "message": "Thermocline cache is not initialized."})
            data_selected = cache["data"][:, idx, :] if key == 'thermocline_hyd' else cache["data"][:, :, idx]
            cache["idx"], values = data_selected, [None if np.isnan(x) else x for x in data_selected[0,:]]
            # Get the first frame for the first timestamp
            data = { "timestamps": cache["timestamps"], "depths": cache["depths"], "values": values }
        elif type_ == 'thermocline_update':
            cache = getattr(request.app.state, "thermocline_cache", None)
            if cache is None: return JSONResponse({"status": 'error', "message": "Thermocline cache is not initialized."})
            data = [None if np.isnan(x) else x for x in cache["idx"][idx,:]]
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
        if key == 'vector': data = functions.getVectorNames()
        elif key == 'layer_hyd' and request.app.state.layer_reverse_hyd is not None:
            data = [(idx, value) for idx, value in request.app.state.layer_reverse_hyd.items()]
        elif key == 'sigma_waq' and request.app.state.layer_reverse_waq is not None:
            data = [(idx, value) for idx, value in request.app.state.layer_reverse_waq.items()]
        else: data = []
        status, message = 'ok', ''
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
                file.write(f"\n{'\n\n'.join(parts)}\n")
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
                file.write('\n\n'.join(parts))
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
        project_name = params['project_name']
        # Create MDU file
        project_path = os.path.join(PROJECT_STATIC_ROOT, project_name, 'input')
        mdu_path = os.path.join(STATIC_DIR_BACKEND, 'samples', 'MDUFile.mdu')
        file_content = functions.fileWriter(mdu_path, params)
        # Write file
        with open(os.path.join(project_path, 'FlowFM.mdu'), 'w') as file:
            file.write(file_content)
        status, message = 'ok', f"Project '{project_name}' created successfully!"
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
    subprocess.Popen(GRID_PATH, shell=True)
    return JSONResponse({"status": "ok", "message": ""})