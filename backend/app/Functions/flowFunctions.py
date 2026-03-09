import tempfile, shapely, rasterio
from rasterio.shutil import copy as rio_copy
from rasterio.features import shapes
from pysheds.grid import Grid
from Functions import functions
import geopandas as gpd
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union

soil_type = {
    "Rocks and boulders": 1,
    "Gravel": 2,
    "Coarse sand": 3,
    "Fine sand": 4,
    "Coarse sand with clay": 5,
    "Fine sand with clay": 6,
    "Coarse clay with sand": 7,
    "Fine clay with sand": 8,
    "Clay": 9,
    "Fine clay": 10,
    "Very fine clay": 11,
    "Silt": 12,
    "Gyttja/peat": 13,
    "Bedrock": 14,
    "Glacier": 15,
    "Water": 16
}
soil_codes = {
    1: "Rocks and boulders", 2: "Gravel", 3: "Coarse sand",
    4: "Fine sand", 5: "Coarse sand with clay",
    6: "Fine sand with clay", 7: "Coarse clay with sand",
    8: "Fine clay with sand", 9: "Clay", 10: "Fine clay",
    11: "Very fine clay", 12: "Silt", 13: "Gyttja/peat",
    14: "Bedrock", 15: "Glacier", 16: "Water"
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
