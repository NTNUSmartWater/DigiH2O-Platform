import uvicorn, json, functions
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates
from pathlib import Path
import xarray as xr


app = FastAPI()
# Automatically gzip if file size is greater than 10KB
app.add_middleware(GZipMiddleware, minimum_size=10000)
# Mobirise
app.mount("/assets/images", StaticFiles(directory="static/assets/images"), name="mobirise_images")
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
# My images
app.mount("/images", StaticFiles(directory="static/images"), name="my_images")
# Mount static (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add the template folder
templates = Jinja2Templates(directory="templates")

# Initialize the paths for the NetCDF files
temp_folder, temp_files = 'temp_delft3d', []
nc_folder = 'output'
his_file = f'{nc_folder}/FlowFM_his.nc'
map_file = f'{nc_folder}/FlowFM_map.nc'
dia_file = f'{nc_folder}/FlowFM.dia'
wq_his = f'{nc_folder}/deltashell_his.nc'
wq_map = f'{nc_folder}/deltashell_map.nc'

# Check if the temp_delft3d folder exists
if Path(temp_folder).is_dir():
    app.mount(f"/{temp_folder}", StaticFiles(directory=temp_folder), name=temp_folder)
    # Data storage
    temp_files = [f for f in Path(temp_folder).rglob('*') if f.is_file()]


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
    return FileResponse("static/images/Logo.png")

# Route for the home page
@app.get("/", response_class=HTMLResponse)
async def show_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Route for the template page
@app.get("/temp_delft3d", response_class=HTMLResponse)
def temp_delft3d(request: Request):
    return templates.TemplateResponse("temp_Delft3D.html", {"request": request})

@app.get("/load_popupMenu", response_class=HTMLResponse)
async def load_popupMenu(request: Request, htmlFile: str):
    template_path = Path("templates")/htmlFile
    if not template_path.exists():
        return HTMLResponse(f"<p>Popup menu template not found</p>", status_code=404)
    config_file = Path(temp_folder)/"configuration.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            configuration = json.load(f)
    else:
        configuration = {}
        NCfiles = [data_his, data_map, data_wq_his, data_wq_map]
        for file in NCfiles:
            configuration.update(functions.getVariablesNames(file))
    return templates.TemplateResponse(htmlFile, {"request": request, 'configuration': configuration})
    
# New method (using POST method for JSON, GeoJSON and HTML)
@app.post("/process_data")
async def process_data(request: Request):
    # Get body data
    body = await request.json()
    data_filename, key = body.get('data_filename'), body.get('key')
    # Check if the file exists
    filename = [f for f in temp_files if f.name == data_filename]
    if filename:
        # Load the JSON/GeoJSON file that exists
        with open(filename[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        status, message = 'ok', 'JSON loaded successfully.'
    else:
        # File not found, need to read the NetCDF file
        try:
            if key == 'summary':
                data = functions.getSummary(dia_file, data_his, data_wq_map)
            elif key == 'stations':
                data = json.loads(functions.stationCreator(data_his).to_json())
            elif key == '_in-situ':
                temp = data_filename.split('*')
                name, stationId = temp[0], temp[1]
                temp = functions.selectInsitu(data_his, data_map, name, stationId)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            elif key == 'thermocline':
                temp = functions.thermoclineComputer(data_map)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            elif '_dynamic' in key:
                # Create dynamic data
                data_, time_column = data_map, 'time'
                if '_wq' in data_filename:
                    data_, time_column = data_wq_map, 'nTimesDlwq'
                temp_mesh = functions.assignValuesToMeshes(grid, data_, key, time_column)
                data = json.loads(temp_mesh.to_json())
            elif '_static' in key:
                # Create static data for map
                temp = grid.copy()
                if 'depth' in key:
                    x = data_map['mesh2d_node_x'].values
                    y = data_map['mesh2d_node_y'].values
                    z = data_map['mesh2d_node_z'].values
                    values = functions.interpolation_Z(temp, x, y, z)
                temp['value'] = values
                data = json.loads(temp.to_json())
            elif key == 'velocity':
                value_type = data_filename.replace('_velocity', '')
                idx = len(data_map['mesh2d_layer_z'].values) - int(layer_reverse[value_type]) - 1
                data = functions.velocityComputer(data_map, value_type, idx)
            # elif key == 'bed_shear_stress':
                # df_x = delft3d.tausx.rename(columns={key: f'{key}_x' for key in delft3d.tausx.columns})
                # df_y = delft3d.tausy.rename(columns={key: f'{key}_y' for key in delft3d.tausy.columns})
                # df_bss = pd.concat([df_x, df_y], axis=1)
            else:
                # Create time series data
                data_ = data_wq_his if '_wq' in key else data_his
                temp = functions.timeseriesCreator(data_, key)
                data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
            status, message = 'ok', 'Data loaded successfully.'
        except Exception as e:
            data, status, message = None, 'error', f"Error processing data: {e}"
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)
    
@app.post("/select_polygon")
async def select_polygon(request: Request):
    body = await request.json()
    key, idx = body.get('key'), int(body.get('id'))
    try:
        data_, time_column, column_layer = data_map, 'time', 'mesh2d_layer_z'
        if '_wq' in key:
            time_column, data_, column_layer = 'nTimesDlwq', data_wq_map, 'mesh2d_layer_dlwq'
        temp = functions.selectPolygon(data_, idx, key, time_column, column_layer)
        data = json.loads(temp.to_json(orient='split', date_format='iso', indent=3))
        status, message = 'ok', 'Data loaded successfully.'
    except:
        data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)

@app.post("/initiate_options")
async def initiate_options(request: Request):
    body = await request.json()
    key = body.get('key')
    try:
        if key == 'vector': data = functions.getVectorNames()
        elif key == 'velocity':
            # Try to file velocity checker file
            filename = [f for f in temp_files if f.name == 'velocity_layers.json']
            if filename:
                with open(filename[0], 'r', encoding='utf-8') as f:
                    temp = json.load(f)
            else:
                temp = functions.velocityChecker(data_map)
            data = [value for _, value in temp.items()]
        status, message = 'ok', 'Data loaded successfully.'
    except:
        data, status, message = None, 'error', 'File not found.'
    result = {'content': data, 'status': status, 'message': message}
    return JSONResponse(content=result)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)