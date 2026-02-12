import os, traceback, json, pickle
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from Functions import functions, gridFunctions
from config import PROJECT_STATIC_ROOT
import geopandas as gpd, numpy as np
from shapely.geometry import Point, Polygon
from meshkernel import MeshKernel, GeometryList


router = APIRouter()


@router.post("/init_lakes")
async def init_lakes(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        config_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "config")
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache:
            print("Project is not available in memory. Creating a new one...")
            project_cache_dict = getattr(request.app.state, "project_cache", None)
            request.app.state.project_cache = {}
            project_cache_dict = request.app.state.project_cache
            project_cache = project_cache_dict.setdefault(project_name, {})
            config_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "config")
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
            lake_data["geometry"] = lake_data.geometry.apply(lambda geo: gridFunctions.remove_holes(geo, 0))
            project_cache['lake'], project_cache['depth'] = lake_data, depth_data
        else: lake_data, depth_data = lake_db.copy(), None
        contents = {'lake': json.loads(lake_data.to_json()), 
            'depth': json.loads(depth_data.to_json()) if depth_data is not None else None}
        return JSONResponse({'content': contents, 'status': 'ok'})
    except Exception as e:
        print('/load_lakes:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/search_lakes")
async def search_lakes(request: Request, user=Depends(functions.basic_auth)):
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
    result = [x for x in data if body.get('name').lower() in x.lower()]
    return JSONResponse({'content': result})

@router.post("/vertex_generator")
async def vertex_generator(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"})
        lake_db = project_cache.get('lake')
        project_cache['lake'], coords, polygon = lake_db, [], lake_db["geometry"].iloc[0]
        if polygon.geom_type == "Polygon": coords = list(polygon.exterior.coords)
        elif polygon.geom_type == "MultiPolygon":
            for poly in polygon.geoms:
                coords.extend(list(poly.exterior.coords))
        vertices_with_id = [{"id": i, "coord": Point((coord[0], coord[1]))} for i, coord in enumerate(coords)]
        point = gpd.GeoDataFrame(vertices_with_id, geometry="coord", crs=lake_db.crs)
        return JSONResponse({'status': 'ok', 'content': json.loads(point.to_json())})
    except Exception as e:
        print('/vertex_generator:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/vertex_refiner")
async def vertex_refiner(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        project_cache = request.app.state.project_cache.setdefault(project_name)
        if not project_cache: return JSONResponse({"status": "error", "message": "Project is not available in memory"})
        distance, lake_db  = body.get('distance'), project_cache.get('lake')
        lake_db = lake_db.to_crs(lake_db.estimate_utm_crs())
        boundary = lake_db["geometry"].iloc[0].exterior
        distances = np.arange(0, boundary.length, distance)
        points = [boundary.interpolate(d) for d in distances]
        vertices_with_id = [{"id": i, "coord": Point((coord.x, coord.y))} for i, coord in enumerate(points)]
        point = gpd.GeoDataFrame(vertices_with_id, geometry="coord", crs=lake_db.crs).to_crs("EPSG:4326")
        poly = Polygon([(p.x, p.y) for p in points])
        gdf = gpd.GeoDataFrame(geometry=[poly], crs=lake_db.crs).to_crs("EPSG:4326")
        return JSONResponse({'status': 'ok', 'content': {"polygon": json.loads(gdf.to_json()), "point": json.loads(point.to_json())}})
    except Exception as e:
        print('/vertex_refiner:\n==============')
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

@router.post("/grid_orthos")
async def grid_orthos(request: Request, user=Depends(functions.basic_auth)):
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
        print('/grid_orthos:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

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
