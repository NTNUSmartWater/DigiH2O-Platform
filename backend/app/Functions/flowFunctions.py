import rasterio, shapely
import geopandas as gpd




def terrain_reader(path: str):
    polygons, values = [], []
    with rasterio.open(path) as src:
        band = src.read(1)
        transform = src.transform
        rows, cols = band.shape
        for row in range(rows):
            for col in range(cols):
                value = band[row, col]
                if value == src.nodata: continue
                x1, y1 = rasterio.transform.xy(transform, row, col, offset='ul')
                x2, y2 = rasterio.transform.xy(transform, row, col, offset='lr')
                poly = shapely.geometry.box(x1, y2, x2, y1)
                polygons.append(poly)
                values.append(value)
    gdf = gpd.GeoDataFrame( {"value": values}, geometry=polygons, crs=src.crs)
    if (src.crs != 'epsg:4326'): gdf = gdf.to_crs('epsg:4326')
    return gdf