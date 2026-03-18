import tempfile, shapely, rasterio, dotenv, os, requests
from rasterio.shutil import copy as rio_copy
from rasterio.features import shapes
from pysheds.grid import Grid
from Functions import functions
import geopandas as gpd, pandas as pd
from shapely.geometry import shape, Polygon, MultiPolygon, Point
from shapely.ops import unary_union
from datetime import datetime
from requests.auth import HTTPBasicAuth
dotenv.load_dotenv()
MET_url = os.getenv('MET_ProstAPI_URL')
MET_client_id = os.getenv('MET_ProstAPI_CLIENT_ID')

soil_codes = {
    1: "Rocks and boulders", 2: "Gravel", 3: "Coarse sand",
    4: "Fine sand", 5: "Coarse sand with clay",
    6: "Fine sand with clay", 7: "Coarse clay with sand",
    8: "Fine clay with sand", 9: "Clay", 10: "Fine clay",
    11: "Very fine clay", 12: "Silt", 13: "Gyttja/peat",
    14: "Bedrock", 15: "Glacier", 16: "Water"
}
soil_types = {
    "Rocks and boulders": [0.10, 0.01, 5000, 200, 0.03, 2],
    "Gravel": [0.25, 0.02, 3000, 500, 0.03, 3],
    "Coarse sand": [0.38, 0.03, 2000, 1000, 0.025, 3],
    "Fine sand": [0.41, 0.04, 1200, 1200, 0.020, 3],
    "Coarse sand with clay": [0.42, 0.05, 600, 1500, 0.018, 4],
    "Fine sand with clay": [0.43, 0.05, 400, 1500, 0.017, 4],
    "Coarse clay with sand": [0.45, 0.06, 200, 1800, 0.015, 5],
    "Fine clay with sand": [0.46, 0.07, 120, 1800, 0.014, 6],
    "Clay": [0.48, 0.08, 60, 2000, 0.012, 7],
    "Fine clay": [0.50, 0.09, 40, 2000, 0.011, 8],
    "Very fine clay": [0.52, 0.10, 20, 2000, 0.010, 9],
    "Silt": [0.46, 0.07, 150, 1800, 0.014, 6],
    "Gyttja/peat": [0.80, 0.20, 50, 2500, 0.008, 4],
    "Bedrock": [0.05, 0.01, 100, 100, 0.040, 1],
    "Glacier": [0.30, 0.02, 500, 500, 0.020, 2],
    "Water": [1.00, 1.00, 10000, 0, 0, 0]
}

land_codes = {
    1: "Bare soil", # 1-Bare land, 15-Bare rock, 17-Unclassified
    3: "Impervious/Urban", # 3-Other paved, 9-Paved road, 10-Unpaved road, 12-Railroad, 16-Building
    2: "Water", 4: "Snow/Ice", 5: "Field", 6: "Shallow vegetation", 7: "Dense vegetation",
}
land_types = {
    "Bare soil": [0.1, 0.1, 0.2, 0.02, 0.25, 0.2],
    "Water": [0, 0, 0, 0.03, 0.07, 1.05],
    "Field": [3.0, 0.8, 1.5, 0.20, 0.20, 1.0],
    "Shallow vegetation": [2.0, 0.5, 1.0, 0.15, 0.23, 0.9],
    "Dense vegetation": [5.0, 1.5, 3.0, 0.40, 0.13, 1.1],
    "Impervious/Urban": [0.5, 0.1, 0.5, 0.05, 0.15, 0.3],
    "Snow/Ice": [0, 0, 0, 0.03, 0.80, 0.1]
}





def remove_holes(geom):
    if isinstance(geom, Polygon): return Polygon(geom.exterior)
    elif isinstance(geom, MultiPolygon):
        return MultiPolygon([Polygon(p.exterior) for p in geom.geoms])
    else: return geom
    
def file_writer(grid:Grid, data, out_path:str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
        temp_file = tmp_file.name
    grid.to_raster(data, temp_file)
    copy_options = dict(
        driver="COG", compress="LZW", tiled=True,
        blocksize=256, overview_resampling="average"
    )
    rio_copy(temp_file, out_path, **copy_options)
    functions.safe_remove(temp_file)

def fill_sink(dtm_path:str, fill_path:str) -> None:
    # Load DTM
    grid = Grid.from_raster(data=dtm_path, nodata=-9999)
    dtm = grid.read_raster(data=dtm_path)
    # Fill depressions
    filled = grid.fill_depressions(dem=dtm).astype('float32')
    # Resolve flats
    inflated = grid.resolve_flats(dem=filled).astype('float32')
    file_writer(grid, inflated, fill_path)

def flow_direction(fill_path:str, flow_path:str) -> None:
    grid = Grid.from_raster(data=fill_path, nodata=-9999)
    fill = grid.read_raster(data=fill_path)
    flow = grid.flowdir(dem=fill, routing='d8').astype('int16')
    file_writer(grid, flow, flow_path)

def flow_accumulation(flow_path:str, acc_path:str) -> None:
    grid = Grid.from_raster(data=flow_path, nodata=-9999)
    flow_dir = grid.read_raster(data=flow_path)
    acc = grid.accumulation(fdir=flow_dir, routing='d8').astype('float32')
    file_writer(grid, acc, acc_path)

def watershed(flowdir_path:str, flowacc_path:str, lat:float, lon:float, 
    threshold:float=50, snap_distance:float=10) -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame(geometry=[shapely.geometry.Point(lon, lat)], crs="EPSG:4326")
    with rasterio.open(flowdir_path) as src:
        transform, crs = src.transform, src.crs
    grid = Grid.from_raster(data=flowdir_path, nodata=-9999)
    gdf_crs = gdf.to_crs(grid.crs)
    x, y = float(gdf_crs.geometry.x.iloc[0]), float(gdf_crs.geometry.y.iloc[0])
    flow_dir = grid.read_raster(data=flowdir_path)
    flow_acc = grid.read_raster(data=flowacc_path)
    mask = flow_acc > threshold
    snap_x, snap_y = grid.snap_to_mask(mask=mask, xy=(x, y), search_distance=snap_distance)
    catchment = grid.catchment(x=snap_x, y=snap_y, fdir=flow_dir, 
        routing='d8', xytype='coordinate').astype('int16')
    poly_mask = catchment == 1
    results = [shape(geom) for geom, val in shapes(catchment, mask=poly_mask, transform=transform) if val == 1]
    gdf = gpd.GeoDataFrame(geometry=results, crs=crs)
    if gdf.crs != "EPSG:4326": gdf = gdf.to_crs("EPSG:4326")
    merged_geom = unary_union(gdf.geometry)
    merged_geom_no_holes = remove_holes(merged_geom)
    polygon = gpd.GeoDataFrame(geometry=[merged_geom_no_holes], crs="EPSG:4326")
    return polygon

def weather_init(id:str) -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame()
    if id == 'ntnu':
        content = []




    elif id == 'eklima':
        url = f'{MET_url}/sources/v0.jsonld'
        headers = {'Accept': 'application/json'}
        response = requests.request("GET", url, 
            headers=headers, auth=HTTPBasicAuth(MET_client_id, ''))
        data = response.json()['data']
        df = pd.DataFrame(data)[['@type', 'id', 'name', 'shortName', 'validFrom', 'county', 'municipality', 'stationHolders', 'geometry']]
        df.rename(columns={'@type': 'type'}, inplace=True)
        df['geometry'] = df['geometry'].apply(lambda x: Point(*x['coordinates']) if isinstance(x, dict) else None)
        df.dropna(subset=['geometry'], inplace=True)
        gdf = gpd.GeoDataFrame(df, crs="EPSG:4326")
    elif id == 'nve':
        content = []





    return gdf


def weather_downloader(source:str, stationId:str, start:str, end:str) -> list:
    content, checker = [], 0
    if source == 'ntnu':
        content = []




    elif source == 'eklima':
        # Reference: https://frost.met.no/elementtable
        url = f'{MET_url}/observations/v0.jsonld'
        headers = {'Accept': 'application/json'}
        params = {
            "sources": stationId, "referencetime": f"{start}/{end}",
            "elements": ",".join([
                "precipitation_amount", "air_temperature",
                
                "wind_speed", "relative_humidity", 'air_pressure'
            ]),
        }
        response = requests.request("GET", url, params=params,
            headers=headers, auth=HTTPBasicAuth(MET_client_id, ''))
        data, checker = pd.DataFrame(response.json()["data"]), 1
        data['timestamp'] = pd.to_datetime(data['referenceTime']).dt.strftime('%Y-%m-%d %H:%M:%S')
        data.drop(columns=['sourceId', 'referenceTime'], inplace=True)

        
        print(data)





        







    elif source == 'nve':
        content = []



    return content, checker





