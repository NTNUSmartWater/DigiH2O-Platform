import os, traceback, json, pickle
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from Functions import functions
from Functions.dataFunctions import Regnbyge as regnbyge
from config import PROJECT_STATIC_ROOT
import geopandas as gpd
from datetime import datetime


router = APIRouter()

@router.post("/init_station")
async def init_station(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        key = body.get('key')
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        config_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "config")
        project_cache = request.app.state.project_cache.setdefault(project_name, {})
        if not project_cache or key not in project_cache:
            print("Project is not available in memory. Creating a new one...")
            token = regnbyge().get_Token()
            if token is None:
                return JSONResponse({'status': 'error', 'message': f"Error: Could not get token."})
            path = os.path.normpath(os.path.join(config_dir, f'{key}.pkl'))
            if os.path.exists(path):
                print("Loading data from cache...")
                with open(path, 'rb') as f: station = pickle.load(f)
            else:
                print("Loading data from Regnbyge...")
                station = regnbyge().get_Station(key)
                if not station.empty:
                    with open(path, 'wb') as f: pickle.dump(station, f)
            request.app.state.project_cache = {}
            project_cache_dict = request.app.state.project_cache
            project_cache = project_cache_dict.setdefault(project_name, {})
            project_cache[key] = station
        else: station = project_cache.get(key)
        if station.empty: return JSONResponse({'status': 'error', 'message': f"No {key} data available."})
        geometry = gpd.points_from_xy(station['x'], station['y'])
        point = gpd.GeoDataFrame(station, geometry=geometry, crs='EPSG:32633')
        point = point.drop(columns=['x', 'y'])
        if 'geoX' in point.columns: point = point.drop(columns=['geoX'])
        if 'geoY' in point.columns: point = point.drop(columns=['geoY'])
        point = point.to_crs('EPSG:4326')
        name = point[['name', 'type']].values.tolist()
        content = {'name': name, 'point': json.loads(point.to_json())}
        return JSONResponse({'status': 'ok', 'content': content})
    except Exception as e:
        print('/init_station:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/plot_station")
async def plot_station(request: Request):
    try:
        body = await request.json()
        id, mode, name = body.get('id'), body.get('mode'), body.get('name')
        start, end = body.get('startTime'), body.get('endTime')
        start_time = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
        if start_time >= end_time:
            return JSONResponse({'status': 'error', 'message': "Error: Start time is later than end time."})
        df = regnbyge().get_Values(mode, id, fromDate=start_time, toDate=end_time)
        if df.empty: 
            return JSONResponse({'status': 'error', 'message': f"No '{mode}' data for station '{name}' between '{start}' and '{end}'."})
        content = json.loads(df.to_json(orient='split', date_format='iso', indent=3))
        return JSONResponse({'status': 'ok', 'content': content})
    except Exception as e:
        print('/plot_station:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/download_station")
async def download_station(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        download_type, download_interval = body.get('downloadType'), body.get('downloadInterval')
        start, end, stations = body.get('startTime'), body.get('endTime'), body.get('stations')
        start_time = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
        if start_time >= end_time:
            return JSONResponse({'message': "Error: Start time is later than end time."})
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        config_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "output", "config")
        project_cache = request.app.state.project_cache.setdefault(project_name, {})
        # if not project_cache or key not in project_cache:
        #     print("Project is not available in memory. Creating a new one...")
        #     token = regnbyge().get_Token()
        #     if token is None:
        #         return JSONResponse({'status': 'error', 'message': f"Error: Could not get token."})
        #     path = os.path.normpath(os.path.join(config_dir, f'{key}.pkl'))
        #     if os.path.exists(path):
        #         print("Loading data from cache...")
        #         with open(path, 'rb') as f: station = pickle.load(f)
        #     else:
        #         print("Loading data from Regnbyge...")
        #         station = regnbyge().get_Station(key)
        #         if not station.empty:
        #             with open(path, 'wb') as f: pickle.dump(station, f)
        #     request.app.state.project_cache = {}
        #     project_cache_dict = request.app.state.project_cache
        #     project_cache = project_cache_dict.setdefault(project_name, {})
        #     project_cache[key] = station
        # else: station = project_cache.get(key)

        data_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "regnbyge")
        if not os.path.exists(data_dir): os.makedirs(data_dir)
        for station in stations:
            name, id, mode = station[0], station[1], station[2]
            
            
            
            df = regnbyge().get_Values(mode, id, fromDate=start_time, toDate=end_time)
            if df.empty: return JSONResponse({'message': "Download failed."})

            
            file_name = f'{id}_{download_type.replace(" ", "_")}.csv'
            file_path = os.path.normpath(os.path.join(data_dir, file_name))
            df.to_csv(file_path, index=False)
        

            

        
        return JSONResponse({'message': f'Download successfully: {data_dir.replace(PROJECT_STATIC_ROOT, "...")}.'})
    except Exception as e:
        print('/download_station:\n==============')
        traceback.print_exc()
        return JSONResponse({'message': f"Error: {e}"})
