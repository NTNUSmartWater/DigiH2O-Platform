import os, traceback, json, pickle
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from Functions import functions, gridFunctions
from config import PROJECT_STATIC_ROOT
import geopandas as gpd, numpy as np
from shapely.geometry import Point, Polygon
from meshkernel import MeshKernel, GeometryList

router, processes = APIRouter(), {}

@router.post("/init_lakes")
async def init_lakes(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        config_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "config")
        project_cache = request.app.state.project_cache.setdefault(project_name, {})
        if not project_cache or 'lake_db' not in project_cache:
            print("Project is not available in memory. Creating a new one...")
            lake_path = os.path.normpath(os.path.join(config_dir, 'lakes.pkl'))
            depth_path = os.path.normpath(os.path.join(config_dir, 'depth.pkl'))
            if not os.path.exists(lake_path): gridFunctions.loadLakes(lake_path=lake_path)
            if not os.path.exists(depth_path): gridFunctions.loadLakes(depth_path=depth_path)
            with open(lake_path, 'rb') as f: lake_db = pickle.load(f)
            with open(depth_path, 'rb') as f: depth_db = pickle.load(f)
            project_cache['lake_db'], project_cache['depth_db'] = lake_db, depth_db
        else: lake_db = project_cache.get('lake_db')
        lake_path = os.path.normpath(os.path.join(config_dir, 'lakes.json'))
        if not os.path.exists(lake_path):
            result = lake_db.groupby("Region")["Name"].apply(list).to_dict()
            # Save the processed lake data
            json.dump(result, open(lake_path, "w", encoding=functions.encoding_detect(lake_path)))
        else: result = json.loads(open(lake_path, "r", encoding=functions.encoding_detect(lake_path)).read())
        return JSONResponse({'content': result, 'status': 'ok'})
    except Exception as e:
        print('/init_lakes:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/load_lakes")
async def load_lakes(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        lake = body.get('lakeName')
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"}) 
        lake_db, depth_db = project_cache.get('lake_db', None), project_cache.get('depth_db', None)
        if lake_db is None or depth_db is None:
            print("Lake data is not available in memory. Loading a new one...")
            config_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "config")
            lake_path = os.path.normpath(os.path.join(config_dir, 'lakes.pkl'))
            depth_path = os.path.normpath(os.path.join(config_dir, 'depth.pkl'))
            if not os.path.exists(lake_path): gridFunctions.loadLakes(lake_path=lake_path)
            if not os.path.exists(depth_path): gridFunctions.loadLakes(depth_path=depth_path)
            with open(lake_path, 'rb') as f: lake_db = pickle.load(f)
            with open(depth_path, 'rb') as f: depth_db = pickle.load(f)
            project_cache['lake_db'], project_cache['depth_db'] = lake_db, depth_db
        if lake != 'all':
            lake_data = lake_db[lake_db['Name'] == lake].copy()
            if lake_data.empty: return JSONResponse({'status': 'error', 'message': 'Lake not found'})
            lake_id = lake_data['id'].iloc[0]
            depth_data = depth_db.loc[lake_id].copy()
            lake_data['min'] = round(depth_data['depth'].min(), 2)
            lake_data['max'] = round(depth_data['depth'].max(), 2)
            lake_data['avg'] = round(depth_data['depth'].mean(), 2)
        else: lake_data, depth_data = lake_db.copy(), None
        lake_data["geometry"] = lake_data.geometry.apply(lambda geo: gridFunctions.remove_holes(geo, None))
        temp = lake_data.copy().to_crs(lake_data.estimate_utm_crs())
        lake_data['perimeter'] = round(temp.geometry.apply(lambda g: g.exterior.length), 2)
        project_cache['lake'], project_cache['depth'] = lake_data, depth_data
        contents = {'lake': json.loads(lake_data.to_json()), 
            'depth': json.loads(depth_data.to_json()) if depth_data is not None else None}
        return JSONResponse({'content': contents, 'status': 'ok'})
    except Exception as e:
        print('/load_lakes:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/search_lake")
async def search_lake(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, _ = functions.project_definer(body.get('projectName'), user)
    project_cache = request.app.state.project_cache.setdefault(project_name)
    if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"})
    config_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "config")
    lake_path = os.path.normpath(os.path.join(config_dir, 'lakes_name.json'))
    if not os.path.exists(lake_path):
        lake_db = project_cache.get('lake_db')
        data = np.unique(lake_db['Name'].values).tolist()
        # Save the processed lake data
        json.dump(data, open(lake_path, "w", encoding=functions.encoding_detect(lake_path)))
    else: data = json.loads(open(lake_path, "r", encoding=functions.encoding_detect(lake_path)).read())
    name = body.get('name')
    result = data if name == '' else [x for x in data if name.lower() in x.lower()]
    return JSONResponse({'content': result})

@router.post("/vertex_generator")
async def vertex_generator(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"})
        lake_db = project_cache.get('lake')
        project_cache['polygon'], coords, polygon = lake_db, [], lake_db["geometry"].iloc[0]
        if polygon.geom_type == "Polygon": coords = list(polygon.exterior.coords)
        elif polygon.geom_type == "MultiPolygon":
            for poly in polygon.geoms:
                coords.extend(list(poly.exterior.coords))
        vertices = [{"id": i, "coord": Point((coord[0], coord[1]))} for i, coord in enumerate(coords)]
        point = gpd.GeoDataFrame(vertices, geometry="coord", crs=lake_db.crs)
        return JSONResponse({'status': 'ok', 'content': json.loads(point.to_json())})
    except Exception as e:
        print('/vertex_generator:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/polygon_generator")
async def polygon_generator(request: Request):
    try:
        body = await request.json()
        points = body.get('points', None)
        vertices = [{"id": i, "geometry": Point((coord[1], coord[0]))} for i, coord in enumerate(points)]
        point = gpd.GeoDataFrame(vertices, geometry="geometry", crs="EPSG:4326")
        coords = [(lon, lat) for lat, lon in points]
        data = { "Name": ["Unknown"], "Region": ["Unknown"], "max": ["Unknown"],
            "min": ["Unknown"], "avg": ["Unknown"]}
        gdf = gpd.GeoDataFrame(data=data, geometry=[Polygon(coords)], crs="EPSG:4326")
        temp_gdf = gdf.to_crs(gdf.estimate_utm_crs())
        gdf['perimeter'] = round(temp_gdf['geometry'].iloc[0].length, 2)
        gdf['area'] = round(temp_gdf['geometry'].iloc[0].area, 2)
        result = {"polygon": json.loads(gdf.to_json()), "point": json.loads(point.to_json())}
        return JSONResponse({'status': 'ok', 'content': result})
    except Exception as e:
        print('/polygon_generator:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/vertex_refiner")
async def vertex_refiner(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"})
        start_point, end_point = int(body.get('startPoint')), int(body.get('endPoint'))
        polygon, distance = body.get('polygon', None), body.get('distance')
        if not polygon or len(polygon) < 3:
            return JSONResponse({"status": "error", "message": "Invalid polygon"})
        poly = Polygon([(p[1], p[0]) for p in polygon])
        polygon_wgs84 = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")        
        crs = polygon_wgs84.estimate_utm_crs()
        polygon_xy = polygon_wgs84.to_crs(crs)        
        boundary = polygon_xy["geometry"].iloc[0].exterior        
        boundary_coords = list(boundary.coords)
        n = len(boundary_coords) - 1
        if not (0 <= start_point < n and 0 <= end_point < n):
            return JSONResponse({"status": "error", "message": "Invalid start or end index"})
        if start_point == end_point:
            return JSONResponse({"status": "error", "message": "Start and end point must be different"})
        start_dis = boundary.project(Point(boundary_coords[start_point]))
        end_dis = boundary.project(Point(boundary_coords[end_point]))
        total_length = boundary.length
        if end_dis < start_dis:
            distances = np.concatenate([
                np.arange(start_dis, total_length, distance),
                np.arange(0, end_dis, distance)
            ])
        else: distances = np.arange(start_dis, end_dis, distance)
        if len(distances) == 0:
            return JSONResponse({"status": "error", "message": "Distance too large for selected segment"})
        # Interpolate points
        points = [boundary.interpolate(d) for d in distances]
        new_point_xy = [Point((p.x, p.y)) for p in points]
        temp = gpd.GeoDataFrame(geometry=new_point_xy, crs=crs).to_crs("EPSG:4326")
        new_point_wgs84 = [[p.y, p.x] for p in temp['geometry'].values]
        # Insert the new point at the specified index
        if start_point < end_point: polygon_new = (polygon[:start_point] + new_point_wgs84 + polygon[end_point:])
        else: polygon_new = (new_point_wgs84 + polygon[end_point:start_point])
        if polygon_new[0] != polygon_new[-1]: polygon_new.append(polygon_new[0])
        vertices = [{"id": i, "geometry": Point((coord[1], coord[0]))} for i, coord in enumerate(polygon_new)]
        point = gpd.GeoDataFrame(vertices, geometry="geometry", crs="EPSG:4326")
        poly_new = Polygon([(p.x, p.y) for p in point['geometry'].values])
        gdf = gpd.GeoDataFrame(geometry=[poly_new], crs="EPSG:4326")
        return JSONResponse({'status': 'ok', 'content': {"polygon": json.loads(gdf.to_json()), "point": json.loads(point.to_json())}})
    except Exception as e:
        print('/vertex_refiner:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/vertex_remover")
async def vertex_remover(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"})
        start_point, end_point = int(body.get('startPoint')), int(body.get('endPoint'))
        polygon = body.get('polygon', None)
        polygon_new = polygon[:start_point] + polygon[end_point+1:]
        vertices = [{"id": i, "geometry": Point((coord[1], coord[0]))} for i, coord in enumerate(polygon_new)]
        point = gpd.GeoDataFrame(vertices, geometry="geometry", crs="EPSG:4326")
        poly_new = Polygon([(p.x, p.y) for p in point['geometry'].values])
        gdf = gpd.GeoDataFrame(geometry=[poly_new], crs="EPSG:4326")
        return JSONResponse({'status': 'ok', 'content': {"polygon": json.loads(gdf.to_json()), "point": json.loads(point.to_json())}})
    except Exception as e:
        print('/vertex_remover:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/grid_creator")
async def grid_creator(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"})
        points, level = np.array(body.get('pointCollection')), body.get('levelValue')
        gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(points[:, 1], points[:, 0]), crs="EPSG:4326")
        mk, depth_db = MeshKernel(), project_cache.get('depth')
        crs = depth_db.estimate_utm_crs()
        depth_db, gdf = depth_db.to_crs(crs), gdf.to_crs(crs)
        polygon = GeometryList(gdf.geometry.x, gdf.geometry.y)
        if level == '': mk.mesh2d_make_triangular_mesh_from_polygon(polygon)
        else: mk.mesh2d_make_triangular_mesh_from_polygon(polygon, scale_factor=float(level))
        grid_uds = gridFunctions.netCDF_creator(mk, depth_db)
        project_cache['grid_uds'], project_cache['mk'] = grid_uds, mk
        grid = functions.unstructuredGridCreator(grid_uds)
        return JSONResponse({'status': 'ok', 'content': json.loads(grid.to_json())})
    except Exception as e:
        print('/grid_creator:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/grid_ortho")
async def grid_ortho(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"}) 
        mk, lake_db = project_cache.get('mk', None), project_cache.get('lake')
        if mk is None: return JSONResponse({"status": "error", "message": "Unstructured grid is not available in memory"})
        mesh, crs = mk.mesh2d_get(), lake_db.estimate_utm_crs()
        gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(mesh.edge_x, mesh.edge_y), crs=crs).to_crs("EPSG:4326")
        gdf['orth'] = np.round(mk.mesh2d_get_orthogonality().values, 4)
        gdf = gdf[gdf.orth != -999]
        values = gdf['orth'].values
        min, max = np.min(values), np.max(values)
        return JSONResponse({'status': 'ok', 'content': {"min": min, "max": max, "data": json.loads(gdf.to_json())}})
    except Exception as e:
        print('/grid_ortho:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/check_grid_optimization")
async def check_grid_optimization(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, _ = functions.project_definer(body.get('projectName'), user)
    info = processes.get(project_name)
    if not info: 
        return JSONResponse({"status": "not_started", "progress": 0, "message": 'No optimization running'})
    if info["status"] in ("finished", "failed", "error"): processes.pop(project_name, None)
    if info["status"] == "finished":
        return JSONResponse({"status": "finished", "progress": 100,
            "message": info.get("message", 'Optimization completed successfully')})
    if info["status"] == "failed":
        return JSONResponse({"status": "failed", "progress": info["progress"],
            "message": info.get("message", 'Optimization failed')})
    if info["status"] == "reorganizing":
        return JSONResponse({"status": "reorganizing", "progress": 100, "message": 'Reorganizing outputs. Please wait...'})
    complete = f'Iteration completed: {info["progress"]}% ({info["iteration"]}/{info["iterations"]}) - Detailed level: {info["level"]}'
    return JSONResponse({"status": info["status"], "progress": info["progress"], "message": complete})

# Start a optimization
@router.post("/start_grid_optimization")
async def start_grid_optimization(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, project_id = functions.project_definer(body.get('projectName'), user)
        redis = request.app.state.redis
        lock = redis.lock(f"{project_id}:grid_optimization", timeout=1000, blocking_timeout=10)
        async with lock:
            # Check if optimization already running
            if project_name in processes and processes[project_name]["status"] == "running":
                info = processes[project_name]
                complete = f'Iteration completed: {info["progress"]}% ({info["iteration"]}/{info["iterations"]}) - Detailed level: {info["level"]}'
                return JSONResponse({"status": "running", "progress": info["progress"], "message": complete})
            
            iterations = int(body.get('iterations'))
            level_from, level_to = float(body.get('levelFrom')), float(body.get('levelTo'))


    #         path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
    #         mdu_path = os.path.normpath(os.path.join(path, "FlowFM.mdu"))
    #         bat_path = os.path.normpath(os.path.join(DELFT_PATH, "dflowfm/scripts/run_dflowfm.bat"))
    #         # Check if file exists
    #         if not os.path.exists(mdu_path): 
    #             return JSONResponse({"status": "error", "progress": 0.0, "message": "MDU file not found"})
    #         if not os.path.exists(bat_path): 
    #             return JSONResponse({"status": "error", "progress": 0.0, "message": "Executable file not found"})
    #         # Remove old log
    #         log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "log_hyd.txt"))
    #         if os.path.exists(log_path): os.remove(log_path)
    #         percent_re = re.compile(r'(?P<percent>\d{1,3}(?:\.\d+)?)\s*%')
    #         time_re = re.compile(r'(?P<tt>\d+d\s+\d{1,2}:\d{2}:\d{2})')
    #         # Run the process
    #         command = ["cmd.exe", "/c", bat_path, "--autostartstop", mdu_path]
    #         process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    #             encoding="utf-8", errors="replace", bufsize=1, cwd=path)
    #         processes[project_name] = {"process": process, "progress": 0.0, "status": "running", 
    #             "message": 'Preparing data for simulation...', "time_used": "N/A", "time_left": "N/A"}
    #         # Stream logs
    #         def stream_logs():
    #             try:
    #                 for line in process.stdout:
    #                     proc_info = processes.get(project_name)
    #                     if not proc_info: return
    #                     line = line.strip()
    #                     if not line: continue
    #                     append_log(log_path, line)
    #                     # Catch error messages
    #                     if "forrtl:" in line.lower() or "error" in line.lower():
    #                         processes[project_name]["status"] = "error"
    #                         processes[project_name]["message"] = line
    #                         append_log(log_path, line)
    #                         res = functions.kill_process(process)
    #                         append_log(log_path, res["message"])
    #                         return
    #                     # Check for progress
    #                     match_pct = percent_re.search(line)
    #                     if match_pct: processes[project_name]["progress"] = float(match_pct.group("percent"))
    #                     # Extract run time
    #                     times = time_re.findall(line)
    #                     if len(times) >= 4:
    #                         processes[project_name]["time_used"] = times[2]
    #                         processes[project_name]["time_left"] = times[3]
    #                     elif len(times) == 3:
    #                         processes[project_name]["time_used"] = times[1]
    #                         processes[project_name]["time_left"] = times[2]
    #             except Exception as e:
    #                 proc_info = processes.get(project_name)
    #                 if proc_info:
    #                     processes[project_name]["status"] = "failed"
    #                     processes[project_name]["message"] = f"Internal error: {e}"
    #                 append_log(log_path, f"[INTERNAL ERROR] {e}")
    #             finally:
    #                 process.wait()
    #                 proc_info = processes.get(project_name)
    #                 if not proc_info or proc_info["status"] == "error": return
    #                 processes[project_name]["status"] = "reorganizing"
    #                 processes[project_name]["message"] = "Reorganizing outputs. Please wait..."
    #                 processes[project_name]["progress"] = 100.0
    #                 try:
    #                     post_result = functions.postProcess(path)
    #                     if post_result["status"] != "ok":
    #                         processes[project_name]["status"] = "error"
    #                         processes[project_name]["message"] = post_result["message"]
    #                     else:
    #                         processes[project_name]["status"] = "finished"
    #                         processes[project_name]["message"] = "Simulation completed successfully"
    #                 except Exception as e:
    #                     processes[project_name]["status"] = "failed"
    #                     processes[project_name]["message"] = f"Simulation failed: {e}"
    #         threading.Thread(target=stream_logs, daemon=True).start()
        return JSONResponse({"status": "ok", "message": f"Optimization for {project_name} started"})
    except Exception as e:
        print('/start_grid_optimization:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.get("/optimization_log_full/{project_name}")
async def optimization_log_full(project_name: str, log_file: str = Query(""), user=Depends(functions.basic_auth)):
    project_name, _ = functions.project_definer(project_name, user)
    log_path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, log_file))
    if not os.path.exists(log_path): return {"content": ""}
    with open(log_path, "r", encoding=functions.encoding_detect(log_path), errors="replace") as f:
        content = f.read()
    return {"content": content, "offset": os.path.getsize(log_path)}

@router.get("/optimization_log_tail/{project_name}")
async def optimization_log_tail(project_name: str, offset: int = Query(0), log_file: str = Query(""), user=Depends(functions.basic_auth)):
    project_name, _ = functions.project_definer(project_name, user)
    log_path, lines = os.path.join(PROJECT_STATIC_ROOT, project_name, log_file), []
    if not os.path.exists(log_path): return {"lines": lines, "offset": offset}
    with open(log_path, "r", encoding=functions.encoding_detect(log_path), errors="replace") as f:
        f.seek(offset)
        for line in f:
            lines.append(line.rstrip())
    return {"lines": lines, "offset": os.path.getsize(log_path)}  

@router.post("/grid_checker")
async def grid_checker(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    project_name, _ = functions.project_definer(body.get('projectName'), user)
    grid_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "grids")
    if not os.path.exists(grid_dir): os.makedirs(grid_dir)
    grid_path = os.path.normpath(os.path.join(grid_dir, body.get('gridName')))
    if not os.path.exists(grid_path): return JSONResponse({'status': 'ok'})
    else: return JSONResponse({'status': 'error'})

@router.post("/grid_saver")
async def grid_saver(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"}) 
        grid_uds = project_cache.get('grid_uds')
        grid_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "grids")
        grid_path = os.path.normpath(os.path.join(grid_dir, body.get('gridName')))
        grid_uds.to_netcdf(grid_path)
        return JSONResponse({'status': 'ok', 'message': f'Grid saved successfully: {grid_path.replace(PROJECT_STATIC_ROOT, "...")}'})
    except Exception as e:
        print('/grid_saver:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})
