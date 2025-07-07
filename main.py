import uvicorn, json, functions
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateNotFound
from pathlib import Path


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
dia_file = f'{nc_folder}/FlowFM.dia'


# Route for the home page
@app.get("/")
async def show_home():
    return FileResponse("index.html")

# Route for the template page
@app.get("/temp_delft3d", response_class=HTMLResponse)
async def temp_delft3d(request: Request):
    try:
        return templates.TemplateResponse("temp_Delft3D.html", {"request": request})
    except TemplateNotFound:
        return HTMLResponse("<h1>Data not found</h1>", status_code=404)




## ================================================================
## Old method (using GET method)
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

@app.get("/get_temp_html")
async def get_temp_html(filename: str):
    # Check if the file exists
    path = [f for f in temp_files if f.name == filename]
    if path:
        status, message = 'ok', 'HTML file loaded successfully.'
    else:
        path, status, message = [None], 'error', 'File not found.'
    result = {'content': str(path[0]), 'status': status, 'message': message}
    return JSONResponse(content=result)

## ================================================================

## New method (using POST method for JSON, GeoJSON and HTML)
@app.post("/process_data")
async def process_data(request: Request):
    # Get body data
    body = await request.json()
    data_filename, key = body.get('data_filename'), body.get('key')
    # Check if the file exists
    filename = [f for f in temp_files if f.name == data_filename]
    if filename:
        # print('File exists')
        # File exists
        with open(filename[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        status, message = 'ok', 'JSON loaded successfully.'
    else:
        # File not found, need to read the NetCDF file
        try:
            # print('File not found')
            delft3d = functions.Delft3D(his_file, map_file, dia_file)
            if key == 'stations':
                gdf = getattr(delft3d, key)[['name', 'geometry']]
                data = functions.convert_to_geojson(gdf)
            elif key == 'default_map':
                temperature_mesh = functions.assign_values_to_meshes(delft3d.unstructured_grid, 
                                    delft3d.map_timestamps, delft3d.mesh2d_tem1[:, :, -1])
                temp = temperature_mesh[['geometry', delft3d.map_timestamps[-1]]]
                temp = temp.rename(columns={delft3d.map_timestamps[-1]: 'value'}).reset_index()
                temp['value'] = temp['value'].apply(lambda x: round(x, 2))
                data = functions.convert_to_geojson(temp)
            elif key == 'bed_shear_stress':
                # df_x = delft3d.tausx.rename(columns={key: f'{key}_x' for key in delft3d.tausx.columns})
                # df_y = delft3d.tausy.rename(columns={key: f'{key}_y' for key in delft3d.tausy.columns})
                # df_bss = pd.concat([df_x, df_y], axis=1)
                pass
            else:
                temp = getattr(delft3d, key).reset_index()
                temp = temp.to_json(orient='split', date_format='iso', indent=3)
                data = json.loads(temp)
            status, message = 'ok', 'Data loaded successfully.'
        except: 
            data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)
    
    



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)