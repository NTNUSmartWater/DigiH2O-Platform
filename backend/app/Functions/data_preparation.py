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
        path = os.path.normpath(os.path.join(config_dir, f'{key}.pkl'))
        if not os.path.exists(path):
            print("Loading data from Regnbyge.no ...")
            token = regnbyge().get_Token()
            if token is None: return JSONResponse({'status': 'error', 'message': f"Error: Could not get token."})
            df = regnbyge().get_Station(key)
            if not df.empty:
                geometry = gpd.points_from_xy(df['x'], df['y'])
                station = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:32633')
                station = station.drop(columns=['x', 'y'])
                station['mode'] = key
                if 'geoX' in station.columns: station = station.drop(columns=['geoX'])
                if 'geoY' in station.columns: station = station.drop(columns=['geoY'])
                station = station.to_crs('EPSG:4326')
                with open(path, 'wb') as f: pickle.dump(station, f)
        else:
            with open(path, 'rb') as f: station = pickle.load(f)
        if station.empty: return JSONResponse({'status': 'error', 'message': f"No '{key}' data available."})
        name = station[['name', 'type']].values.tolist()
        content = {'name': name, 'point': json.loads(station.to_json())}
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
        start, end, interval = body.get('startTime'), body.get('endTime'), body.get('interval')
        start_time = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
        if start_time >= end_time:
            return JSONResponse({'status': 'error', 'message': "Error: 'Start time' must be earlier than 'End time'."})
        df = regnbyge().get_Values(mode, id, interval, start_time, end_time)
        if df.empty: 
            return JSONResponse({'status': 'error', 'message': f"No data available for station '{name}' between '{start}' and '{end}'."})
        if 'id' in df.columns: df = df.drop(columns=['id'])
        content = json.loads(df.to_json(orient='split', date_format='iso', indent=3))
        return JSONResponse({'status': 'ok', 'content': content})
    except Exception as e:
        print('/plot_station:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/download_station")
async def download_station(request: Request):
    try:
        body = await request.json()
        mode, download_interval = body.get('mode'), body.get('downloadInterval')
        start, end, id = body.get('startTime'), body.get('endTime'), body.get('id')
        start_time = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
        if start_time >= end_time:
            return JSONResponse({'status': 'error', 'message': "Error: Start time is later than end time."})
        df = regnbyge().get_Values(mode, id, download_interval, start_time, end_time)
        if df.empty: 
            return JSONResponse({'status': 'error', 'message': f"No data available between '{start_time}' and '{end_time}'."})
        if 'id' in df.columns: df = df.drop(columns=['id'])
        df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        csv_string = df.to_csv(index=False)
        return JSONResponse({'status': 'ok', 'content': csv_string})
    except Exception as e:
        print('/download_station:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})
