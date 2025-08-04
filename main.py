import uvicorn, json, functions
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateNotFound
from pathlib import Path
import xarray as xr, pandas as pd


app = FastAPI()
# Automatically gzip if file size is greater than 10KB
app.add_middleware(GZipMiddleware, minimum_size=10000)
# Mount the functions
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/temp_delft3d", StaticFiles(directory="temp_delft3d"), name="temp_delft3d")

# Add the template folder
templates = Jinja2Templates(directory="static")

# Data storage
temp_folder = 'temp_delft3d'
temp_files = [f for f in Path(temp_folder).rglob('*') if f.is_file()]

# Read data
nc_folder = 'output'
his_file = f'{nc_folder}/FlowFM_his.nc'
map_file = f'{nc_folder}/FlowFM_map.nc'
# dia_file = f'{nc_folder}/FlowFM.dia'
wq_his = f'{nc_folder}/deltashell_his.nc'
wq_map = f'{nc_folder}/deltashell_map.nc'
# Check if the files exist
if not (Path(his_file).is_file() or Path(map_file).is_file()):
    raise Exception(f'Files: {his_file} or {map_file} not found.')
data_his, data_map = xr.open_dataset(his_file), xr.open_dataset(map_file)
grid = functions.unstructuredGridCreator(data_map)
n_layers = functions.velocityChecker(data_map)
layer_reverse = {v: k for k, v in n_layers.items()}
if not (Path(wq_his).is_file() or Path(wq_map).is_file()):
    raise Exception(f'Files: {wq_his} or {wq_map} not found.')
data_wq_map, data_wq_his = xr.open_dataset(wq_map), xr.open_dataset(wq_his)




@app.get("/favicon.ico")
def favicon():
    return FileResponse("/images/Logo.png")

# Route for the home page
@app.get("/")
async def show_home():
    return FileResponse("index.html")

@app.get("/get_json")
async def get_json(data_filename: str, station: str = 'None'):
    # Check if the file exists
    filename = [f for f in temp_files if f.name == data_filename]
    if filename:
        # Read the JSON file
        with open(filename[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Check station is available
        if station != 'None':
            # Convert data to DataFrame
            df = pd.DataFrame(data)
            columns = [i for i in df.columns if station in i]
            data = df[['index'] + columns].to_json(orient='records', date_format='iso', indent=3)
        status, message = 'ok', 'JSON loaded successfully.'
    else:
        data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)

# Route for the template page
@app.get("/temp_delft3d", response_class=HTMLResponse)
async def temp_delft3d(request: Request):
    try:
        configuration, NCfiles = {}, [data_his, data_map, data_wq_his, data_wq_map]
        for file in NCfiles:
            configuration.update(functions.getVariablesNames(file))
        print(configuration, '\n')
        return templates.TemplateResponse("temp_Delft3D.html", {"request": request, 'configuration': configuration})
    except TemplateNotFound:
        return HTMLResponse("<h1>Data not found</h1>", status_code=404)

## New method (using POST method for JSON, GeoJSON and HTML)
@app.post("/process_data")
async def process_data(request: Request):
    # Get body data
    body = await request.json()
    data_filename, key = body.get('data_filename'), body.get('key')
    station = body.get('station')
    # Check if the file exists
    filename = [f for f in temp_files if f.name == data_filename]
    if filename:
        # print('File exists')
        # Load the JSON/GeoJSON file that exists
        with open(filename[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        status, message = 'ok', 'JSON loaded successfully.'
    else:
        # print('File not found')
        # File not found, need to read the NetCDF file
        try:
            if key == 'stations':
                # Create station data
                data = json.loads(functions.stationCreator(data_his).to_json())
            elif key == 'thermocline':
                temp = functions.thermoclineComputer(data_map)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            elif 'static' in data_filename:
                # Create static data
                temp = grid.copy()
                temp['value'] = functions.interpolation_Z(temp, data_map['mesh2d_node_x'].values, data_map['mesh2d_node_y'].values, data_map['mesh2d_node_z'].values)
                temp['value'] = temp['value'].apply(lambda x: round(x, 2))
                data = json.loads(temp.to_json())
            elif 'dynamic' in data_filename or 'multilayers' in data_filename:
                # Create dynamic data
                data_, time_column = data_map, 'time'
                if 'water_quality' in key:
                    data_, time_column = data_wq_map, 'nTimesDlwq'
                temp_mesh = functions.assignValuesToMeshes(grid, data_, key, time_column)
                data = json.loads(temp_mesh.to_json())
            elif 'in-situ' in data_filename:
                temp = functions.selectInsitu(data_his, data_map, key, station)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            elif 'velocity' in data_filename:
                value_type = data_filename.replace('_velocity', '')
                key = len(data_map['mesh2d_layer_z'].values) - int(layer_reverse[value_type]) - 1
                data = functions.velocityComputer(data_map, value_type, key)
                # print(data)
            # elif key == 'bed_shear_stress':
                # df_x = delft3d.tausx.rename(columns={key: f'{key}_x' for key in delft3d.tausx.columns})
                # df_y = delft3d.tausy.rename(columns={key: f'{key}_y' for key in delft3d.tausy.columns})
                # df_bss = pd.concat([df_x, df_y], axis=1)
            else:
                # Create time series data
                temp = functions.timeseriesCreator(data_his, key)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            status, message = 'ok', 'Data loaded successfully.'
        except: 
            data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)
    
@app.post("/select_polygon")
async def select_polygon(request: Request):
    body = await request.json()
    filename, id = body.get('filename'), int(body.get('id'))
    try:
        key, data_ = filename.split('.')[0], data_map
        time_column, data_, column_layer = 'time', data_map, 'mesh2d_layer_z'
        if 'water_quality' in key:
            time_column, data_, column_layer = 'nTimesDlwq', data_wq_map, 'mesh2d_layer_dlwq'
        temp = functions.selectPolygon(data_, id, key, time_column, column_layer)
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
        status, message = 'ok', 'Data loaded successfully.'
    except:
        data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)

@app.post("/process_velocity")
async def process_velocity(request: Request):
    await request.json()
    try:
        data = [value for _, value in n_layers.items()]
        status, message = 'ok', 'Data loaded successfully.'
    except:
        data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)

@app.post("/process_layer")
async def process_layer(request: Request):
    body = await request.json()
    key = body.get('key')
    try:
        data, result = {}, {'Temperature':'temperature_multilayers', 'Salinity':'salinity_multilayers',
            'Contaminant':'contaminant_multilayers', 'Water Surface Level':'water_surface_dynamic',
            'Depth Water Level':'water_depth_dynamic'}
        if key == 'init_layers':
            data['below'] = [value for value in list(result.keys())]
            data['above'] = [value for value in list(n_layers.values())[:2]]
        elif key == 'process_layers':
            below_layer, above_layer = body.get('below_layer'), body.get('above_layer')
            key_below = result[below_layer]
            temp_mesh = functions.assignValuesToMeshes(grid, data_map, key_below)
            data['below'] = json.loads(temp_mesh.to_json())
            key_above = len(data_map['mesh2d_layer_z'].values) - int(layer_reverse[above_layer]) - 1
            data['above'] = functions.velocityComputer(data_map, above_layer, key_above)
        status, message = 'ok', 'Data loaded successfully.'
    except:
        data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)






# ## ================================================================
# ## Old method (using GET method)
# @app.get("/get_json")
# async def get_json(data_filename: str, station: str = 'None'):
#     # Check if the file exists
#     filename = [f for f in temp_files if f.name == data_filename]
#     if filename:
#         # Read the JSON file
#         with open(filename[0], 'r', encoding='utf-8') as f:
#             data = json.load(f)
#         # Check station is available
#         if station != 'None':
#             # Convert data to DataFrame
#             df = pd.DataFrame(data)
#             columns = [i for i in df.columns if station in i]
#             data = df[['index'] + columns].to_json(orient='records', date_format='iso', indent=3)
#         status, message = 'ok', 'JSON loaded successfully.'
#     else:
#         data, status, message = None, 'error', 'File not found.'
#     result = {'content': data, 'status': status, 'message': message}
#     return JSONResponse(content=result)    

# @app.get("/get_temp_html")
# async def get_temp_html(filename: str):
#     # Check if the file exists
#     path = [f for f in temp_files if f.name == filename]
#     if path:
#         status, message = 'ok', 'HTML file loaded successfully.'
#     else:
#         path, status, message = [None], 'error', 'File not found.'
#     result = {'content': str(path[0]), 'status': status, 'message': message}
#     return JSONResponse(content=result)

# ## ================================================================