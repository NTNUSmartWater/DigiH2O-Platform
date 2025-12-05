import os, json, re, requests, math, asyncio, traceback, subprocess, msgpack
from fastapi import APIRouter, Request, File, UploadFile, Form, Depends
from Functions import functions
from shapely.geometry import mapping
from fastapi.responses import JSONResponse
from config import PROJECT_STATIC_ROOT, STATIC_DIR_BACKEND
from config import GRID_PATH, WINDOWS_AGENT_URL
import xarray as xr, pandas as pd, numpy as np, geopandas as gpd

router = APIRouter()

# Process data
async def process_internal(query: str, key: str, redis, project_cache, project_name: str):
    # Internal function to process data
    message = ''
    if key == 'summary':
        dia_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "HYD", "FlowFM.dia"))
        hyd_his, waq_his = project_cache.get("hyd_his"), project_cache.get("waq_his")
        data = functions.getSummary(dia_path, [hyd_his, waq_his])
    elif key == 'hyd_station':
        temp, message = functions.hydCreator(project_cache.get("hyd_his"))
        data = json.loads(temp.to_json())
    elif key in ['wq_obs', 'wq_loads']:
        waq_obs_raw = await redis.hget(project_name, "waq_obs")
        waq_obs = msgpack.unpackb(waq_obs_raw, raw=False)
        data = json.loads(functions.obsCreator(waq_obs[key]).to_json())
    elif key == 'sources':
        data = json.loads(functions.sourceCreator(project_cache.get("hyd_his")).to_json())
    elif key == 'crosssections':
        temp, message = functions.crosssectionCreator(project_cache.get("hyd_his"))
        data = json.loads(temp.to_json())
    elif key == '_in-situ':
        name, station_id, typ = query.split('*')
        temp = functions.selectInsitu(project_cache.get("hyd_his"), project_cache.get("hyd_map"), name, station_id, typ)
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
    elif key == 'substance_check':
        substance_raw = await redis.hget(project_name, 'config')
        substance = msgpack.unpackb(substance_raw, raw=False)[query]
        if len(substance) > 0:
            data, message = sorted(substance), functions.valueToKeyConverter(substance)
        else: data, message = None, f"No substance defined."
    elif key == 'substance':
        temp = functions.timeseriesCreator(project_cache.get("waq_his"), query.split(' ')[0], timeColumn='nTimesDlwq')
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
    elif key == 'static':
        # Create static data for map
        grid, hyd_map = project_cache.get("grid"), project_cache.get("hyd_map")
        x = hyd_map['mesh2d_node_x'].data.compute()
        y = hyd_map['mesh2d_node_y'].data.compute()
        z = hyd_map['mesh2d_node_z'].data.compute()
        if 'depth' in query: values = functions.interpolation_Z(grid, x, y, z)
        # Convert GeoDataFrame to expected format
        fnm = functions.numberFormatter
        features = [{ "type": "Feature", "properties": {"index": idx}, "geometry": mapping(row['geometry'])} 
                    for idx, row in grid.iterrows()]
        data = { 'meshes': { 'type': 'FeatureCollection', 'features': features },
            'values': values.tolist(), 'min_max': [fnm(np.nanmin(values)).tolist(), fnm(np.nanmax(values)).tolist()]
        }
    else:
        # Create time series data
        temp = functions.timeseriesCreator(project_cache.get("hyd_his"), key)
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
    return message, data

@router.post("/process_data")
async def process_data(request: Request, user=Depends(functions.basic_auth)):
    # Get body data
    body = await request.json()
    query, key = body.get('query'), body.get('key')
    project_name = functions.project_definer(body.get('projectName'), user)
    redis = request.app.state.redis
    project_cache = request.app.state.project_cache.setdefault(project_name)
    lock = redis.lock(f"{project_name}:{key}", timeout=10)
    try:
        async with lock:
            message, data = await process_internal(query, key, redis, project_cache, project_name)
            if data is None: return JSONResponse({'status': 'error', 'message': message})
            return JSONResponse({'content': data, 'status': 'ok', 'message': message})
    except Exception as e:
        print('/process_data:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

# Load general dynamic data
@router.post("/load_general_dynamic")
async def load_general_dynamic(request: Request, user=Depends(functions.basic_auth)):
    # Get body data
    body = await request.json()
    query, key, project_name = body.get('query'), body.get('key'), functions.project_definer(body.get('projectName'), user)
    redis, dynamic_cache_key = request.app.state.redis, f"{project_name}:general_cache"    
    # if user == 'admin': 
    #     params = ['FlowFM_his.zarr', 'FlowFM_map.zarr', 'Cadmium_his.zarr', 'Cadmium_map.zarr']
    #     status, message = await functions.database_definer(request, project_name, params, redis)
    #     if status != 'ok': return JSONResponse({"status": status, "message":message})
    project_cache = request.app.state.project_cache.setdefault(project_name)
    if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory."})
    hyd_his, hyd_map = project_cache.get("hyd_his"), project_cache.get("hyd_map")
    waq_his, waq_map = project_cache.get("waq_his"), project_cache.get("waq_map")
    if not any([hyd_his, hyd_map, waq_his, waq_map]): return JSONResponse({"status": "error", "message": "Project not initialized."})
    try:
        temp = query.split('|')
        is_hyd = temp[0] == '' # hydrodynamic or waq
        data_ds = hyd_map if is_hyd else waq_map
        time_column = 'time' if is_hyd else 'nTimesDlwq'
        name = functions.variablesNames.get(key, key) if is_hyd else temp[0]
        values = data_ds[name].values
        # Load dynamic cache from Redis
        raw_cache = await redis.get(dynamic_cache_key)
        if raw_cache:
            dynamic_cache = msgpack.unpackb(raw_cache, raw=False)
        else:
            layer_reverse_key = "layer_reverse_hyd" if is_hyd else "layer_reverse_waq"
            layer_reverse_raw = await redis.hget(project_name, layer_reverse_key)
            layer_reverse = msgpack.unpackb(layer_reverse_raw, raw=False)
            dynamic_cache = {"layer_reverse": layer_reverse, "layers": {}}
        layer_reverse = dynamic_cache["layer_reverse"]
        # Process data
        if 'single' in key: arr = values
        else:
            value_type = layer_reverse[temp[1]]
            lock = redis.lock(f"{project_name}:{value_type}", timeout=10)
            async with lock:
                layer_info = dynamic_cache['layers'].get(value_type)
                if layer_info:
                    arr = functions.decode_array(layer_info["data"], layer_info["shape"])
                else:
                    n_layers = len(layer_reverse)
                    row_idx = n_layers - int(temp[1]) - 2
                    if value_type == 'Average':
                        arr = np.nanmean(values, axis=2) if is_hyd else data_ds[f"{name.split('_')[0]}_2d_{name.split('_')[1]}"].values
                    else: arr = values[:, :, row_idx-1] if is_hyd else values[:, row_idx-1, :]
                    # Save layer atomic to Redis hash
                    dynamic_cache['layers'][value_type] = {'data': functions.encode_array(arr), 'shape': arr.shape}
                    await redis.set(dynamic_cache_key, msgpack.packb(dynamic_cache, use_bin_type=True))
        if temp[2] == 'load': # Initiate skeleton polygon for the first load
            grid = project_cache.get("grid")
            if grid is None:
                return JSONResponse({"status": "error", "message": "Grid data not found in cache."})
            # Construct GeoJSON features
            features = [{"type": "Feature", "properties": {"index": idx}, "geometry": mapping(row['geometry'])}
                        for idx, row in grid.iterrows()]
            arr_np, fmt = np.array(arr), functions.numberFormatter
            new_arr = arr_np[-1, :] if arr_np.ndim == 2 else arr_np
            data = { 'meshes':  {'type': 'FeatureCollection', 'features': features},
            'values': functions.encode_array(fmt(new_arr)), 'min_max': [fmt(np.nanmin(values)).tolist(), fmt(np.nanmax(values)).tolist()],
            'timestamps': [pd.to_datetime(t).strftime('%Y-%m-%d %H:%M:%S') for t in data_ds[time_column].data]
            }
        else: # Update value of polygons
            arr_np, fmt = np.array(arr), functions.numberFormatter
            new_arr = arr_np[int(temp[2]), :] if arr_np.ndim == 2 else arr_np
            data = {'values': functions.encode_array(fmt(new_arr))}
        return JSONResponse({'status': 'ok', 'content': data})
    except Exception as e:
        print('/load_general_dynamic:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

# Load vector dynamic data
@router.post("/load_vector_dynamic")
async def load_vector_dynamic(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    query, key, project_name = body.get('query'), body.get('key'), functions.project_definer(body.get('projectName'), user)
    redis, vector_cache_key = request.app.state.redis, f"{project_name}:vector_cache"
    project_cache = request.app.state.project_cache.setdefault(project_name)
    if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory."})
    try:
        layer_reverse_raw = await redis.hget(project_name, "layer_reverse_hyd")
        layer_reverse = msgpack.unpackb(layer_reverse_raw, raw=False)
        value_type, row_idx = layer_reverse[key], len(layer_reverse) - int(key) - 2
        data_ds, fnm = project_cache.get("hyd_map"), functions.numberFormatter
        raw_cache = await redis.get(vector_cache_key)
        if raw_cache: vector_cache = msgpack.unpackb(raw_cache, raw=False)
        else: vector_cache = {"layers": {}}
        if value_type in vector_cache['layers']:
            layer_dict = vector_cache['layers'][value_type]
        else:
            layer_dict = functions.vectorComputer(data_ds, value_type, row_idx)
            lock = redis.lock(f"{project_name}:vector:{value_type}", timeout=10)
            async with lock:
                vector_cache['layers'][value_type] = layer_dict
                await redis.set(vector_cache_key, msgpack.packb(vector_cache, use_bin_type=True))
        if query == 'load': # Initiate skeleton polygon for the first load
            # Get global vmin and vmax
            data = layer_dict
            if value_type == 'Average':
                vmin = fnm(np.nanmin(data_ds['mesh2d_ucmaga'])).tolist()
                vmax = fnm(np.nanmax(data_ds['mesh2d_ucmaga'])).tolist()
            else:
                vmin = fnm(np.nanmin(data_ds['mesh2d_ucmag'])).tolist()
                vmax = fnm(np.nanmax(data_ds['mesh2d_ucmag'])).tolist()
            data['timestamps'] = [pd.to_datetime(t).strftime('%Y-%m-%d %H:%M:%S') for t in data_ds['time'].data]
            data['min_max'] = [vmin, vmax]
        else: data = functions.vectorComputer(data_ds, value_type, row_idx, int(query))
        return JSONResponse({'content': data, 'status': 'ok'})
    except Exception as e:
        print('/load_vector_dynamic:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

# Select meshes based on ids
@router.post("/select_meshes")
async def select_meshes(request: Request, user=Depends(functions.basic_auth)):    
    body = await request.json()
    key, query, idx = body.get('key'), body.get('query'), body.get('idx')
    project_name, points = functions.project_definer(body.get('projectName'), user), body.get('points')
    redis, mesh_cache_key = request.app.state.redis, f"{project_name}:mesh_cache"
    project_cache = request.app.state.project_cache.setdefault(project_name)
    if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory."})
    hyd_map, waq_map = project_cache.get("hyd_map"), project_cache.get("waq_map")
    extend_task, lock = None, redis.lock(f"{project_name}:select_meshes", timeout=20)
    try:
        async with lock:
            extend_task = asyncio.create_task(functions.auto_extend(lock))
            if '_waq_multi_dynamic' in query: query = 'mesh2d_' + query[:-len('_waq_multi_dynamic')]
            is_hyd = key == 'hyd'
            data_ds = hyd_map if is_hyd else waq_map
            name = functions.variablesNames.get(query, query)
            values, fnm = data_ds[name].values, functions.numberFormatter
            # Initiate data for the first load
            if idx == 'load':
                # Initialize mesh cache in Redis if not exists
                await redis.delete(mesh_cache_key)
                layer_reverse_raw = await redis.hget(project_name, "layer_reverse_hyd")
                layer_reverse = msgpack.unpackb(layer_reverse_raw, raw=False)
                depth_values = [float(v.split(' ')[1]) for k, v in layer_reverse.items() if int(k) >= 0]
                max_layer = float(max(np.array(depth_values), key=abs))
                n_rows = math.ceil(abs(max_layer)/10)*10 + 1 if max_layer < 0 else -(math.ceil(abs(max_layer)/10)*10 + 1)
                mesh_cache = { "depth_values": depth_values, "n_rows": n_rows, "df": None}
                await redis.set(mesh_cache_key, msgpack.packb(mesh_cache, use_bin_type=True))
                time_column = 'time' if is_hyd else 'nTimesDlwq'
                time_stamps = pd.to_datetime(data_ds[time_column]).strftime('%Y-%m-%d %H:%M:%S').tolist()
                points_arr, arr = np.array(points), values[0,:,:]
                # Create GeoDataFrame for interpolation
                grid = project_cache.get("grid")
                x_coords, y_coords = points_arr[:, 2], points_arr[:, 1]
                gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(x_coords, y_coords), crs=grid.crs)
                gdf['depth'] = functions.interpolation_Z(gdf, hyd_map['mesh2d_node_x'].values, 
                    hyd_map['mesh2d_node_y'].values, hyd_map['mesh2d_node_z'].values)
                # Find polygons that the points are in
                gdf_filtered = gpd.sjoin(gdf, grid, how="left", predicate="intersects")
                gdf_filtered.set_index('index_right', inplace=True)
                df_serialized = gdf_filtered.drop(columns=['geometry'])
                mesh_cache["df"] = df_serialized.to_dict(orient='list')
                # Compute frame in thread to avoid blocking
                frame = await asyncio.to_thread(functions.meshProcess, is_hyd, arr, mesh_cache)
                global_vmin, global_vmax = fnm(np.nanmin(arr)).tolist(), fnm(np.nanmax(arr)).tolist()
                vmin, vmax = fnm(np.nanmin(frame)).tolist(), fnm(np.nanmax(frame)).tolist()
                depths_idx = np.arange(0, frame.shape[0]) if mesh_cache["n_rows"] > 0 else np.arange(0, -frame.shape[0], -1)
                data = {"timestamps": time_stamps, "distance": np.round(points_arr[:, 0], 0).tolist(), "values": fnm(frame).tolist(), 
                        "depths": depths_idx.tolist(), "global_minmax": [global_vmin, global_vmax], "local_minmax": [vmin, vmax]}
                await redis.set(mesh_cache_key, msgpack.packb(mesh_cache, use_bin_type=True))
            else: # Load next frame
                raw_cache = await redis.get(mesh_cache_key)
                if raw_cache is None: return JSONResponse({"status": 'error', "message": "Mesh cache is not initialized."})
                mesh_cache, arr = msgpack.unpackb(raw_cache, raw=False), values[int(idx),:,:]
                frame = await asyncio.to_thread(functions.meshProcess, is_hyd, arr, mesh_cache)
                vmin, vmax = fnm(np.nanmin(frame)).tolist(), fnm(np.nanmax(frame)).tolist()
                data = {"values": fnm(frame).tolist(), "local_minmax": [vmin, vmax]}
        return JSONResponse({'content': data, 'status': 'ok'})
    except Exception as e:
        print('/select_meshes:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})
    finally:
        if extend_task:
            extend_task.cancel()
            try: await extend_task
            except asyncio.CancelledError: pass

# Working with thermocline plots
@router.post("/select_thermocline")
async def select_thermocline(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    key, query, typ = body.get('key'), body.get('query'), body.get('type')
    project_name, idx = functions.project_definer(body.get('projectName'), user), body.get('idx')
    redis, thermo_cache_key = request.app.state.redis, f"{project_name}:thermocline_cache"
    project_cache = request.app.state.project_cache.setdefault(project_name)
    hyd_map, waq_map = project_cache.get("hyd_map"), project_cache.get("waq_map")
    lock = redis.lock(f"{project_name}:{typ}", timeout=10)
    try:
        async with lock:
            is_hyd = key == 'thermocline_hyd'
            data_ds = hyd_map if is_hyd else waq_map
            col_idx = 2 if is_hyd else 1
            name = functions.variablesNames.get(query, query)
            # Initiate data for the first load
            if typ == 'thermocline_grid':
                temp_grid, arr = project_cache.get("grid"), data_ds[name].values
                # Remove polygons having all NaN in all layers
                mask_all_nan = np.isnan(arr).all(axis=(0, col_idx))               
                removed_indices = np.where(mask_all_nan)[0]
                grid = temp_grid.drop(index=removed_indices).reset_index()
                data = json.loads(grid.to_json())
            elif typ == 'thermocline_init':
                time_column = 'time' if is_hyd else 'nTimesDlwq'
                time_stamps = pd.to_datetime(data_ds[time_column]).strftime('%Y-%m-%d %H:%M:%S').tolist()
                # Load layer reverse from Redis
                layer_key = "layer_reverse_hyd" if is_hyd else "layer_reverse_waq"
                layer_reverse_raw = await redis.hget(project_name, layer_key)
                layer_reverse = msgpack.unpackb(layer_reverse_raw, raw=False)
                layers_values = [float(v.split(' ')[1]) for k, v in layer_reverse.items() if int(k) >= 0]
                max_values = int(abs(np.min(layers_values)))
                new_depth = [x + max_values for x in layers_values]
                arr, idx = data_ds[name].values, int(idx)
                # Remove polygons having Nan in all layers
                mask_all_nan = np.isnan(arr).all(axis=(0, col_idx))
                arr_filtered = arr[:, ~mask_all_nan, :] if is_hyd else arr[:, :, ~mask_all_nan]
                data_selected = arr_filtered[:, idx, :] if is_hyd else arr_filtered[:, :, idx]
                # Save filtered 3D → cache
                await redis.set(thermo_cache_key, json.dumps(data_selected.tolist()))
                values = [None if np.isnan(x) else functions.numberFormatter(x).tolist() for x in data_selected[0,:]]
                # Get the first frame for the first timestamp
                data = { "timestamps": time_stamps, "depths": new_depth, "values": values }
            elif typ == 'thermocline_update':
                raw_cache = await redis.get(thermo_cache_key)
                if not raw_cache:
                    return JSONResponse({"status": "error", "message": "Thermocline cache not initialized."})
                data_selected = np.array(json.loads(raw_cache))
                data = [None if np.isnan(x) else functions.numberFormatter(x).tolist() for x in data_selected[int(idx),:]]
            return JSONResponse({"status": 'ok', "content": data})
    except Exception as e:
        print('/select_thermocline:\n==============')
        traceback.print_exc()
        return JSONResponse({"status": 'error', "message": f"Error: {e}"})

# Read grid
@router.post("/open_grid")
async def open_grid(request: Request, user=Depends(functions.basic_auth)):
    # Get body data
    body = await request.json()
    project_name, grid_name = functions.project_definer(body.get('projectName'), user), body.get('gridName')
    path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input", grid_name))
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
async def initiate_options(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    key, project_name = body.get('key'), functions.project_definer(body.get('projectName'), user)
    redis = request.app.state.redis
    lock = redis.lock(f"{project_name}:initiate_options", timeout=10)
    try:
        async with lock:
            data = []
            if key == 'vector': data = functions.getVectorNames()
            elif key == 'layer_hyd':
                layer_reverse_raw = await redis.hget(project_name, "layer_reverse_hyd")
                layer_reverse = msgpack.unpackb(layer_reverse_raw, raw=False)
                if layer_reverse: data = [(idx, value) for idx, value in layer_reverse.items()]
            elif key == 'sigma_waq':
                layer_reverse_raw = await redis.hget(project_name, "layer_reverse_waq")
                layer_reverse = msgpack.unpackb(layer_reverse_raw, raw=False)
                if layer_reverse: data = [(idx, value) for idx, value in layer_reverse.items()]
            elif key == 'thermocline_waq':
                config_raw = await redis.hget(project_name, "config")
                config = msgpack.unpackb(config_raw, raw=False)
                item = [x for x in config.keys() if x.startswith('waq_map_') and x.endswith('_selector')]
                if len(item) > 0: data = config[item[0]]
            return JSONResponse({"status": 'ok', "content": data})
    except Exception as e:
        print('/initiate_options:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

# Upload file from local computer to server
@router.post("/upload_data")
async def upload_data(file: UploadFile = File(...), projectName: str = Form(...),
                      gridName: str = Form(...), user=Depends(functions.basic_auth)):
    try:
        project_name = functions.project_definer(projectName, user)
        file_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input", gridName))
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
async def update_boundary(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, subBoundaryName = functions.project_definer(body.get('projectName'), user), body.get('subBoundaryName')
    boundary_name, data_boundary = body.get('boundaryName'), body.get('boundaryData')
    boundary_type, data_sub = body.get('boundaryType'), body.get('subBoundaryData')
    if boundary_type == 'Contaminant': unit = '-'; quantity = 'tracerbndContaminant'
    else: unit = 'm'; quantity = 'waterlevelbnd'
    ref_date = '1970-01-01 00:00:00'
    # Parse date
    config = {'sub_boundary': subBoundaryName, 'boundary_type': quantity, 'unit': unit, 'ref_date': ref_date}
    temp_file = os.path.normpath(os.path.join(STATIC_DIR_BACKEND, 'samples', 'BC.bc'))
    try:
        temp, bc = [], [boundary_name]
        for row in data_sub:
            row[0] = int(row[0]/1000.0); temp.append(row)
        lines = [f"{int(x)}  {y}" for x, y in temp]
        config['data'] = '\n'.join(lines)
        path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
        # Write new format boundary file (*_bnd.ext)
        ext_path = os.path.normpath(os.path.join(path, "FlowFM_bnd.ext"))
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
        boundary_file = os.path.normpath(os.path.join(path, f"{boundary_name}.pli"))
        bc.append(f'    {len(data_boundary)}    2')
        for row in data_boundary:
            temp = f'{row[2]}    {row[1]}    {row[0]}'
            bc.append(temp)
        with open(boundary_file, 'w', encoding="utf-8") as file:
            file.write('\n'.join(bc))
            file.flush()
            os.fsync(file.fileno())
        # Write boundary conditions file
        file_path = os.path.normpath(os.path.join(path, f"{boundary_type}.bc"))
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
                file.write(joined_parts)
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
async def view_boundary(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, boundary_type = functions.project_definer(body.get('projectName'), user), body.get('boundaryType')
    try:
        path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
        # Read file
        with open(os.path.normpath(os.path.join(path, f"{boundary_type}.bc")), 'r') as f:
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
async def delete_boundary(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, boundary_name = functions.project_definer(body.get('projectName'), user), body.get('boundaryName')
    try:
        path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
        water_lelvel_path = os.path.normpath(os.path.join(path, "WaterLevel.bc"))
        contaminant_path = os.path.normpath(os.path.join(path, "Contaminant.bc"))
        boundary_path = os.path.normpath(os.path.join(path, f"{boundary_name}.pli"))
        ext_path = os.path.normpath(os.path.join(path, "FlowFM_bnd.ext"))
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
async def check_condition(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, force_name = functions.project_definer(body.get('projectName'), user), body.get('forceName')
    path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
    status, ext_path = 'error', os.path.normpath(os.path.join(path, force_name))
    if os.path.exists(ext_path): status = 'ok'
    return JSONResponse({"status": status})

# Create MDU file
@router.post("/generate_mdu")
async def generate_mdu(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    params = dict(body.get('params'))
    try:
        project_name = functions.project_definer(params['project_name'], user)
        status, message = 'ok', f"Project '{project_name}' created successfully!"
        # Create MDU file
        project_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, 'input'))
        mdu_path = os.path.normpath(os.path.join(STATIC_DIR_BACKEND, 'samples', 'MDUFile.mdu'))
        file_content = functions.fileWriter(mdu_path, params)
        # Write file
        with open(os.path.normpath(os.path.join(project_path, 'FlowFM.mdu')), 'w') as file:
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