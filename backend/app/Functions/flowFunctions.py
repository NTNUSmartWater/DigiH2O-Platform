import os, rasterio, shapely, tempfile
from rasterio.shutil import copy as rio_copy
import geopandas as gpd
from pysheds.grid import Grid
from Functions import functions


def fill_sink(dtm_path:str, out_path:str):
    # Load DTM
    grid = Grid.from_raster(dtm_path, nodata=-9999)
    dtm = grid.read_raster(dtm_path)
    # Fill depressions
    filled = grid.fill_depressions(dtm)
    # Resolve flats
    inflated = grid.resolve_flats(filled)
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
        temp_file = tmp_file.name
    grid.to_raster(data=inflated, file_name=temp_file)
    copy_options = dict(
        driver="COG", compress="LZW", tiled=True,
        blocksize=256, overview_resampling="average"
    )
    rio_copy(temp_file, out_path, **copy_options)
    functions.safe_remove(temp_file)

def flow_direction(fill_path:str, out_path:str):
    grid = Grid.from_raster(fill_path, nodata=-9999)
    fill = grid.read_raster(fill_path)
    flow = grid.flowdir(dem=fill, routing='d8')
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp_file:
        temp_file = tmp_file.name
    grid.to_raster(data=flow, file_name=temp_file)
    copy_options = dict(
        driver="COG", compress="LZW", tiled=True,
        blocksize=256, overview_resampling="average"
    )
    rio_copy(temp_file, out_path, **copy_options)
    functions.safe_remove(temp_file)




