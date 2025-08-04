import shapely
import geopandas as gpd, pandas as pd
import numpy as np, xarray as xr
from scipy.spatial import cKDTree


variablesNames = {'total_heat_flux':'Qtot', 'air_temperature':'Tair', 'relative_humidity':'rhum', 'precipitation_rate':'rain',
    'solar_influx':'Qsun', 'sensible_heat_flux':'Qcon', 'wind_speed':'wind', 'free_convection_sensible_heat_flux':'Qfrcon',
    'long_wave_back_radiation':'Qlong', 'cloudiness':'clou', 'evaporative_heat_flux':'Qeva', 'free_convection_evaporative_heat_flux':'Qfreva',
    'water_level_dynamic':'mesh2d_s1', 'water_depth_dynamic':'mesh2d_waterdepth', 'temperature_multilayers':'mesh2d_tem1',
    'salinity_multilayers':'mesh2d_sa1', 'contaminant_multilayers':'mesh2d_contaminant',
    'adsorbed_ortho_phosphate_water_quality':'mesh2d_2d_AAP', 'adsorbed_ortho_phosphate_water_quality_multilayers':'mesh2d_AAP',
    'fdf_carbon_water_quality':'mesh2d_2d_DetC', 'fdf_carbon_water_quality_multilayers':'mesh2d_DetC',
    'fdf_nitrogen_water_quality':'mesh2d_2d_DetN', 'fdf_nitrogen_water_quality_multilayers':'mesh2d_DetN',
    'fdf_phosphate_water_quality':'mesh2d_2d_DetP', 'fdf_phosphate_water_quality_multilayers':'mesh2d_DetP',
    'green_algae_biomass_water_quality':'mesh2d_2d_GREEN', 'green_algae_biomass_water_quality_multilayers':'mesh2d_GREEN',
    'dissolved_ammonium_water_quality':'mesh2d_2d_NH4', 'dissolved_ammonium_water_quality_multilayers':'mesh2d_NH4',
    'dissolved_nitrate_water_quality':'mesh2d_2d_NO3', 'dissolved_nitrate_water_quality_multilayers':'mesh2d_NO3',
    'dissolved_phosphate_water_quality':'mesh2d_2d_PO4', 'dissolved_phosphate_water_quality_multilayers':'mesh2d_PO4',
    'dissolved_oxygen_water_quality':'mesh2d_2d_OXY', 'dissolved_oxygen_water_quality_multilayers':'mesh2d_OXY',
    'dissolved_chloride_water_quality':'mesh2d_2d_Cl', 'dissolved_chloride_water_quality_multilayers':'mesh2d_Cl',
    'inorganic_matter_water_quality':'mesh2d_2d_IM1', 'inorganic_matter_water_quality_multilayers':'mesh2d_IM1',
    'opal_si_water_quality':'mesh2d_2d_Opal', 'opal_si_water_quality_multilayers':'mesh2d_Opal',
    'sediment_oxygen_demand_water_quality':'mesh2d_2d_SOD', 'sediment_oxygen_demand_water_quality_multilayers':'mesh2d_SOD',
    'total_nitrogen_algae_water_quality':'mesh2d_2d_AlgN', 'total_nitrogen_algae_water_quality_multilayers':'mesh2d_AlgN',
    'total_phosphorus_algae_water_quality':'mesh2d_2d_AlgP', 'total_phosphorus_algae_water_quality_multilayers':'mesh2d_AlgP',
    'suspended_solids_water_quality':'mesh2d_2d_SS', 'suspended_solids_water_quality_multilayers':'mesh2d_SS',
    'total_nitrogen_water_quality':'mesh2d_2d_TotN', 'total_nitrogen_water_quality_multilayers':'mesh2d_TotN',
    'kjeldahl_nitrogen_water_quality':'mesh2d_2d_KjelN', 'kjeldahl_nitrogen_water_quality_multilayers':'mesh2d_KjelN',
    'total_phosphorus_water_quality':'mesh2d_2d_TotP', 'total_phosphorus_water_quality_multilayers':'mesh2d_TotP',
    'daylength_limitation_greens_water_quality':'mesh2d_2d_LimDLGreen', 'daylength_limitation_greens_water_quality_multilayers':'mesh2d_LimDLGreen',
    'nutrient_limitation_greens_water_quality':'mesh2d_2d_LimNutGree', 'nutrient_limitation_greens_water_quality_multilayers':'mesh2d_LimNutGree',
    'radiation_limitation_greens_water_quality':'mesh2d_2d_LimRadGree', 'radiation_limitation_greens_water_quality_multilayers':'mesh2d_LimRadGree',
    'chlorophyll_concentration_water_quality':'mesh2d_2d_Chlfa', 'chlorophyll_concentration_water_quality_multilayers':'mesh2d_Chlfa',
    'extinction_phytoplankton_water_quality':'mesh2d_2d_ExtVlPhyt', 'extinction_phytoplankton_water_quality_multilayers':'mesh2d_ExtVlPhyt',
    'volume_water_quality':'mesh2d_2d_volume', 'volume_water_quality_multilayers':'mesh2d_volume',



    
    }


def getVariablesNames(data: xr.Dataset) -> dict:
    """
    Get the names of the variables in the dataset received from *.nc file.

    Parameters:
    ----------
    data: xr.Dataset
        The .nc file.

    Returns:
    -------
    dict
        The dictionary containing the names of the variables.
    """
    result = {}
    # Check data type whether it is a map or history file
    if 'stations' in data.sizes:
        # This is a his file
        result['points'] = True if data_his.sizes['stations'] > 0 else False
        







    # for key in data.variables.keys():
    #     if key in variablesNames.keys():
    #         result[key] = variablesNames[key]
    #     else:
    #         result[key] = key
    




    return result


def stationCreator(data_his: xr.Dataset) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of stations.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his.nc file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of stations.
    """
    station_names = [name.decode('utf-8').strip() for name in data_his['station_name'].values]
    # Location of stations
    geometry = gpd.points_from_xy(data_his['station_x_coordinate'].values, data_his['station_y_coordinate'].values)
    stations = gpd.GeoDataFrame(data={'name': station_names, 'geometry': geometry}, crs=data_his['wgs84'].attrs['EPSG_code'])
    return stations

def timeseriesCreator(data_his: xr.Dataset, key: str, columns: list) -> pd.DataFrame:
    """
    Create a GeoDataFrame of timeseries.

    Parameters:
    ----------
    ds_his: xr.Dataset
        The dataset received from _his.nc file.
    key: str
        The key of the timeseries.
    columns: list
        The columns of the timeseries.

    Returns:
    -------
    pd.DataFrame
        The DataFrame of timeseries.
    """
    name = variablesNames[key] if key in variablesNames.keys() else key
    index = [pd.to_datetime(id).strftime('%Y-%m-%d %H:%M:%S') for id in data_his['time'].values]
    timeseries = pd.DataFrame(index=index, data=data_his[name].values, columns=columns).reset_index()
    return timeseries

def unstructuredGridCreator(data_map: xr.Dataset) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of unstructured grid.

    Parameters:
    ----------
    data_map: xr.Dataset
        The dataset received from _map.nc file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of unstructured grid.
    """
    coords = np.array([[x, y] for x, y in zip(data_map['mesh2d_node_x'].values, data_map['mesh2d_node_y'].values)])
    faces = xr.where(np.isnan(data_map['mesh2d_face_nodes']), 0, data_map['mesh2d_face_nodes']).values.astype(int)-1
    counts = np.sum(faces != -1, axis=1)
    polygons = []
    for face, count in zip(faces, counts):
        ids = face[:count]
        xy = coords[ids]
        polygons.append(shapely.geometry.Polygon(xy))
    # Create GeoDataFrame from polygons
    try:
        crs_code = data_map['wgs84'].attrs['EPSG_code']
    except: raise ValueError ("EPSG code not found.")
    grid = gpd.GeoDataFrame(geometry=polygons, crs=crs_code)
    return grid

def interpolation_Z(grid_net: gpd.GeoDataFrame, x_coords: np.ndarray, y_coords: np.ndarray,
        z_values: np.ndarray, n_neighbors: int=2) -> np.ndarray:
    """
    Interpolate or extrapolate z values for grid from known points
    using Inverse Distance Weighting (IDW) method.

    Parameters:
    ----------
    grid_net: gpd.GeoDataFrame
        The GeoDataFrame containing the grid.
    x_coords: np.ndarray
        The x coordinates of known points.
    y_coords: np.ndarray
        The y coordinates of known points.
    z_values: np.ndarray
        The z values of known points.
    n_neighbors: int
        The number of neighbors (stations) to consider.

    Returns:
    -------
    np.ndarray
        The interpolated z values.
    """
    gdf_points = grid_net.copy().to_crs(epsg=32632)
    gdf_points['geometry'] = gdf_points['geometry'].centroid
    gdf_points = gdf_points.to_crs(epsg=4326)
    tree = cKDTree(list(zip(x_coords, y_coords)))
    dists, idx = tree.query(list(zip(gdf_points['geometry'].x,
                                     gdf_points['geometry'].y)), k=n_neighbors)
    weight = 1 / (dists + 1e-10)**2
    weight_val = weight * z_values[idx]
    value = np.sum(weight_val, axis=1)/np.sum(weight, axis=1)
    return value

def assignValuesToMeshes(grid: gpd.GeoDataFrame, data_map: xr.Dataset, key: str, time_column: str='time') -> gpd.GeoDataFrame:
    """
    Interpolate or extrapolate z values for grid from known points
    using Inverse Distance Weighting (IDW) method.

    Parameters:
    ----------
    grid: gpd.GeoDataFrame
        The GeoDataFrame containing the meshes/unstructured grid.
    data_map: xr.Dataset
        The dataset received from _map.nc file.
    key: str
        The key of the array received from _map.nc file.
    time_column: str
        The name of the time column.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame with interpolated z values.
    """
    name = variablesNames[key] if key in variablesNames.keys() else key
    result, temp_grid = {}, grid.copy()
    time_stamps = [pd.to_datetime(id).strftime('%Y-%m-%d %H:%M:%S') for id in data_map[time_column].values]
    values = data_map[name].values
    if len(data_map[name].values.shape) == 3:
        values = data_map[name].values[:,:,-1]
    for i in range(len(time_stamps)):
        result[time_stamps[i]] = np.array(values[i,:]).flatten()
    result = pd.DataFrame(result).replace(-999.0, np.nan)
    result = temp_grid.join(result)
    result[time_stamps] = result[time_stamps].round(2)
    return result.reset_index()

def selectPolygon(data_map: xr.Dataset, idx: int, key:str, time_column: str='time', column_layer: str='mesh2d_layer_z') -> dict:
    """
    Get attributes of a selected polygon during the simulation.

    Parameters:
    ----------
    data_map: xr.Dataset
        The dataset received from _map.nc file.
    arr: np.ndarray (3D)
        The array containing the attributes of the selected polygons.
    idx: int
        The index of the selected polygon.
    key: str
        The key of the array received from _map.nc file.
    time_column: str
        The name of the time column.
    column_layer: str
        The name of the layer column.

    Returns:
    -------
    dict
        A dictionary containing the attributes of the selected polygon.
    """
    name = variablesNames[key] if key in variablesNames.keys() else key
    index = [pd.to_datetime(id).strftime('%Y-%m-%d %H:%M:%S') for id in data_map[time_column].values]
    z_layer = data_map[column_layer].values
    result = pd.DataFrame(index=index)
    if column_layer == 'mesh2d_layer_z':
        arr, kt = data_map[name].values[:, idx, :], 'm'
    elif column_layer == 'mesh2d_layer_dlwq':
        arr, kt = data_map[name].values[:, :, idx], ''
    for i in range(arr.shape[1]):
        i_rev = -(i+1)
        arr_rev = np.round(arr[:, i_rev], 2)
        result[f'Layer: {z_layer[i_rev]:.2f} {kt}'] = arr_rev
    result = result.replace(-999.0, np.nan).reset_index()
    return result

def selectInsitu(data_his: xr.Dataset, data_map: xr.Dataset, key: str, station: str) -> pd.DataFrame:
    """
    Get insitu data.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his.nc file.
    data_map: xr.Dataset
        The dataset received from _map.nc file.
    key: str
        The name of defined variable in _his.nc file.
    station: str
        The name of the station.

    Returns:
    -------
    pd.DataFrame
        A DataFrame containing the insitu data.
    """
    station_names = [name.decode('utf-8').strip() for name in data_his['station_name'].values]
    if station not in station_names: return pd.DataFrame()
    idx = station_names.index(station)
    index = [pd.to_datetime(id).strftime('%Y-%m-%d %H:%M:%S') for id in data_his['time'].values]
    result = pd.DataFrame(index=index)
    z_layer = np.round(data_map['mesh2d_layer_z'].values, 2)
    arr = data_his[key].values[:, idx, :]
    for i in range(arr.shape[1]):
        i_rev = -(i+1)
        arr_rev = np.round(arr[:, i_rev], 2)
        result[f'Depth: {z_layer[i_rev]} m'] = arr_rev
    result = result.reset_index()
    return result

def velocityChecker(data_map: xr.Dataset) -> dict:
    """
    Check how many velocity layers are available.

    Parameters:
    ----------
    data_map: xr.Dataset
        The dataset received from _map.nc file.

    Returns:
    -------
    dict
        A dictionary containing the index and value of velocity layers.
    """
    layers, z_layer = {}, np.round(data_map['mesh2d_layer_z'].values, 2)
    if ('mesh2d_ucxa' in data_map.variables.keys() and 'mesh2d_ucya' in data_map.variables.keys()):
        layers[-1] = 'Depth-average'
    for i in range(len(z_layer)-1, -1, -1):
        ucx = data_map['mesh2d_ucx'].values[:, :, i]
        ucy = data_map['mesh2d_ucy'].values[:, :, i]
        ucm = data_map['mesh2d_ucmag'].values[:, :, i]
        if (np.isnan(ucx).all() or np.isnan(ucy).all() or np.isnan(ucm).all()): continue
        layers[len(z_layer)-i-1] = f'Depth: {z_layer[i]} m'
    return layers

def velocityComputer(data_map: xr.Dataset, value_type: str, key: int) -> gpd.GeoDataFrame:
    """
    Compute velocity in each layer and average value (if possible)

    Parameters:  
    ----------
    data_map: xr.Dataset
        The dataset received from _map.nc file.
    value_type: str
        The type of velocity to compute.
    key: int
        The index of the selected layer.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame containing the vector map of the mesh.
    """
    result = {}
    if value_type == 'Depth-average':
        # Average velocity in each layer
        ucx = data_map['mesh2d_ucxa'].values
        ucy = data_map['mesh2d_ucya'].values
        ucm = data_map['mesh2d_ucmaga'].values
    else:
        # Velocity for specific layer
        ucx = data_map['mesh2d_ucx'].values[:, :, key]
        ucy = data_map['mesh2d_ucy'].values[:, :, key]
        ucm = data_map['mesh2d_ucmag'].values[:, :, key]
    # Get indices of non-nan values
    row_idx, col_idx = np.where(~np.isnan(ucx) & ~np.isnan(ucy) & ~np.isnan(ucm))
    result["time"] = pd.to_datetime(data_map['time'].values[np.unique(row_idx)]).strftime('%Y-%m-%d %H:%M:%S').tolist()
    x_coords = data_map['mesh2d_face_x'].values[np.unique(col_idx)].astype(np.float64)
    y_coords = data_map['mesh2d_face_y'].values[np.unique(col_idx)].astype(np.float64)
    result["coordinates"] = np.column_stack((x_coords, y_coords)).tolist()
    ucx = np.round(ucx.astype(np.float64), 5)
    ucy = np.round(ucy.astype(np.float64), 5)
    ucm = np.round(ucm.astype(np.float64), 2)
    ucx_flat = ucx[row_idx, col_idx]
    ucy_flat = ucy[row_idx, col_idx]
    ucm_flat = ucm[row_idx, col_idx]
    _, group_starts = np.unique(row_idx, return_index=True)
    big_array = np.stack([ucx_flat, ucy_flat, ucm_flat], axis=1)
    big_list = big_array.tolist()
    result["values"], result['min_max'] = [], [float(np.min(ucm_flat)), float(np.max(ucm_flat))]
    start_indices = list(group_starts) + [len(big_list)]
    for i in range(len(group_starts)):
        start = start_indices[i]
        end = start_indices[i+1]
        result["values"].append(big_list[start:end])
    return result

def thermoclineComputer(data_map: xr.Dataset) -> pd.DataFrame:
    """
    Compute thermocline in each time step.

    Parameters:
    ----------
    data_map: xr.Dataset
        The dataset received from _map.nc file.

    Returns:
    -------
    pd.DataFrame
        The DataFrame containing the thermocline in each time step.
    """
    index_ = list(data_map['mesh2d_layer_z'].values)
    times = data_map['time'].values
    columns, data_list = [], []
    for i in range(len(times)):
        col_name = pd.to_datetime(times[i]).strftime('%Y-%m-%d %H:%M:%S')
        value = np.nanmean(data_map['mesh2d_tem1'].values[i,:,:], axis=0)
        columns.append(col_name)
        data_list.append(value)
    df = pd.DataFrame(np.column_stack(data_list), index=index_, columns=columns).reset_index()
    return df
