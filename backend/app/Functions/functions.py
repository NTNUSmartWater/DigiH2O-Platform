import shapely, os, re, shutil, stat, math
import geopandas as gpd, pandas as pd
import numpy as np, xarray as xr, dask.array as da
from scipy.spatial import cKDTree
from config import PROJECT_STATIC_ROOT

def remove_readonly(func, path, excinfo):
    # Change the readonly bit, but not the file contents
    os.chmod(path, stat.S_IWRITE)
    func(path)

variablesNames = {
    # For In-situ options
    'temperature':'Temperature (°C)', 'salinity':'Salinity (ppt)', 'contaminant':'Contaminant (mg/m³)', # For hydrodynamic stations
    'velocity_magnitude':'Velocity (m/s)', 'discharge_magnitude':'Discharge (m³/s)', # For hydrodynamic stations
    'x_velocity':'X-Velocity (m/s)', 'y_velocity':'Y-Velocity (m/s)','z_velocity':'Z-Velocity (m/s)', # For hydrodynamic stations
    'pre_discharge_source':'source_sink_prescribed_discharge', 'pre_discharge_increment_source':'source_sink_prescribed_salinity_increment', # For sources
    'pre_temperature_increment_source':'source_sink_prescribed_temperature_increment', 'avg_discharge_source':'source_sink_discharge_average', # For sources
    'discharge_source':'source_sink_current_discharge', 'cumulative_volume_source':'source_sink_cumulative_volume',  # For sources
    'cross_section_velocity':'Velocity (m/s)', 'cross_section_area':'Area (m²)', 'cross_section_discharge':'Discharge (m³/s)', # For cross-sections
    'cross_section_cumulative_discharge': 'Cumulative Discharge (m³)', 'cross_section_temperature':'Temperature (°C)', # For cross-sections
    'cross_section_cumulative_temperature': 'Cumulative Temperature (°C)', 'cross_section_salt':'Salinity (ppt)', # For cross-sections
    'cross_section_cumulative_salt': 'Cumulative Salinity (ppt)', 'cross_section_Contaminant':'Contaminant (mg/m³)', # For cross-sections
    'cross_section_cumulative_Contaminant': 'Cumulative Contaminant (mg/m³)', # For cross-sections
    # For Hydrodynamics options
    'wl':'waterlevel', 'wd':'waterdepth',
    # For Water Balance options
    'wb_tv':'water_balance_total_volume', 'wb_s':'water_balance_storage', 'wb_bi':'water_balance_boundaries_in',
    'wb_bo':'water_balance_boundaries_out', 'wb_bt':'water_balance_boundaries_total',
    'wb_pt':'water_balance_precipitation_total', 'wb_e':'water_balance_evaporation', 'wb_ss':'water_balance_source_sink',
    'wb_gi':'water_balance_groundwater_in', 'wb_go':'water_balance_groundwater_out', 'wb_gt':'water_balance_groundwater_total',
    'wb_pg':'water_balance_precipitation_on_ground','wb_ve':'water_balance_volume_error',
    # For Meteorological options
    'thf':'Qtot', 'at':'Tair', 'rh':'rhum', 'pr':'rain', 'si':'Qsun', 'shf':'Qcon', 'ws':'wind', 'fcshf':'Qfrcon',
    'lwbr':'Qlong', 'cloudiness':'clou', 'ehf':'Qeva', 'fcehf':'Qfreva',
    # For Single Layer Dynamic map: Hydrodynamics
    'wl_single_dynamic':'mesh2d_s1', 'wd_single_dynamic':'mesh2d_waterdepth',
    # For Multi Layer Dynamic map: Physical options
    'temp_multi_dynamic':'mesh2d_tem1', 'sal_multi_dynamic':'mesh2d_sa1', 'cont_multi_dynamic':'mesh2d_Contaminant',
}

units = {
    # Physical
    'cTR1': 'Conservative Tracer Source 1 (g/m³)', 'cTR2': 'Conservative Tracer Source 2 (g/m³)', 'IM2S1': 'IM2S1 (g/m³)',
    'cTR3': 'Conservative Tracer Source 3 (g/m³)', 'dTR1': 'Decayable Tracer Source 1 (g/m³)', 'IM3S1': 'IM3S1 (g/m³)',
    'dTR2': 'Decayable Tracer Source 2 (g/m³)', 'dTR3': 'Decayable Tracer Source 3 (g/m³)', 
    'IM1': 'Inorganic Matter (g/m³)', 'IM2': 'IM2 (g/m³)', 'IM3': 'IM3 (g/m³)', 'IM1S1': 'Inorganic Matter in layer S1 (g/m²)',
    # Chemical
    'NH4': 'Ammonium (g/m³)', 'CBOD5': 'Carbonaceous BOD (first pool) at 5 days (g/m³)', 'OXY': 'Dissolved Oxygen (g/m³)', 'SOD': 'Sediment Oxygen Demand (g/m²)',
    'DO': 'Dissolved Oxygen Concentration (g/m³)', 'SaturOXY': 'Saturation Concentration (g/m³)', 'SatPercOXY': 'Actual Saturation Percentage O2 (%)',
    'BOD5': 'BOD5 (g/m³)', 'Cd': 'Cadmium (g/m³)', 'CdS1': 'Cadmium in layer S1 (g/m²)', 'NO3': 'Nitrate (g/m³)', 'As': 'Arsenic (g/m³)',
    # Microbial
    'Salinity': 'Salinity (ppt)', 'EColi': 'E.Coli bacteria (MPN/m³)', 'volume': 'Volume (m³)'
}

def numberFormatter(arr: np.array, decimals: int=2) -> np.array:
    """
    Format the numbers in the array to a specified number of decimal places.

    Parameters:
    ----------
    arr: np.array
        The array containing the numbers to be formatted.
    decimals: int
        The number of decimal places to format the numbers to.

    Returns:
    -------
    np.array
        The array with formatted numbers.
    """
    try:
        arr = np.asarray(arr, dtype=float)
        result = np.empty(arr.shape, dtype=object)
        finite_mask = np.isfinite(arr)
        abs_arr = np.abs(arr)
        # Make a mask for large numbers
        large_mask = finite_mask & (abs_arr >= 1)
        result[large_mask] = np.round(arr[large_mask], decimals)
        # Make a mask for small numbers
        small_mask = finite_mask & (abs_arr < 1) & (arr != 0)
        fmt = f"%.{decimals}e"
        result[small_mask] = [float(fmt % v) for v in arr[small_mask]]
        # Make a mask for zero
        zero_mask = finite_mask & (arr == 0)
        result[zero_mask] = 0.0
        # NaN -> None
        nan_mask = ~finite_mask
        result[nan_mask] = None
        result = np.reshape(result, arr.shape).tolist()
        return result
    except:
        print("Input array contains non-numeric values")
        return arr

def getVectorNames() -> list:
    """
    Get the names of the vector variables.

    Returns:
    -------
    list
        The list containing the names of the vector variables.
    """
    result = ['Velocity']
    return result

def checkVariables(data: xr.Dataset, variablesNames: str) -> bool:
    """
    Check if all variables are available in the variablesNames dictionary.

    Returns:
    -------
    bool
        True if all variables are available, False otherwise.
    """
    if variablesNames not in data.variables: return False
    var = data[variablesNames]
    if var.size == 0: return False # Empty variable
    # Check if all values are NaN in a sample slice
    if np.isnan(var.data.compute()).all(): return False
    # Check if min and max are the same value
    vmin, vmax = var.min(skipna=True).compute(), var.max(skipna=True).compute()
    return bool(float(vmin) != float(vmax))

def getVariablesNames(Out_files: list, model_type: None) -> dict:
    """
    Get the names of the variables in the dataset received from *.nc file.

    Parameters:
    ----------
    Out_files: list
        The list of the *.zarr files (in xr.Dataset format).
    model_type: str
        The type of the model used.

    Returns:
    -------
    dict
        The dictionary containing the names of the variables.
    """
    result = {'hyd': False, 'waq': False}
    for data in Out_files:
        if data is None: continue
        result['single_layer'] = result['multi_layer'] = False
        # This is a hydrodynamic his file
        if 'time' in data.sizes and any(k in data.sizes for k in ['stations', 'cross_section', 'source_sink']):
            print(f"- Checking Hydrodynamics Simulation: His file ...")
            # Prepare data for hydrodynamic options
            result['hyd_obs'] = data.sizes['stations'] > 0 if ('stations' in data.sizes) else False
            result['cross_sections'], result['hyd'] = False, True
            if 'cross_section' in data.sizes and data.sizes['cross_section'] > 0:
                x = da.unique(data['cross_section_geom_node_coordx'].data).compute()
                y = da.unique(data['cross_section_geom_node_coordy'].data).compute()
                if (x.shape[0] > 1 and y.shape[0] > 1): result['cross_sections'] = True
            result['sources'] = data.sizes['source_sink'] > 0 if ('source_sink' in data.sizes) else False
            # Prepare data for measured locations
            # 1. Observation points
            # 1.1. Hydrodynamics
            result['hyd_waterlevel'] = checkVariables(data, 'waterlevel')
            result['hyd_waterdepth'] = checkVariables(data, 'waterdepth')
            # 1.2. Meteorology
            result['hyd_total_heat_flux'] = checkVariables(data, 'Qtot')
            result['hyd_precipitation_rate'] = checkVariables(data, 'rain')
            result['hyd_wind_speed'] = checkVariables(data, 'wind')
            result['hyd_air_temperature'] = checkVariables(data, 'Tair')
            result['hyd_relative_humidity'] = checkVariables(data, 'rhum')
            result['hyd_solar_influx'] = checkVariables(data, 'Qsun')
            result['hyd_evaporative_heat_flux'] = checkVariables(data, 'Qeva')
            result['hyd_free_convection_evaporative_heat_flux'] = checkVariables(data, 'Qfreva')
            result['hyd_sensible_heat_flux'] = checkVariables(data, 'Qcon')
            result['hyd_free_convection_sensible_heat_flux'] = checkVariables(data, 'Qfrcon')
            result['hyd_long_wave_back_radiation'] = checkVariables(data, 'Qlong')
            result['hyd_cloudiness'] = checkVariables(data, 'clou')
            result['hyd_meteorology'] = True if (result['hyd_total_heat_flux'] or
                result['hyd_precipitation_rate'] or result['hyd_wind_speed'] or
                result['hyd_air_temperature'] or result['hyd_relative_humidity'] or
                result['hyd_solar_influx'] or result['hyd_evaporative_heat_flux'] or
                result['hyd_free_convection_evaporative_heat_flux'] or
                result['hyd_sensible_heat_flux'] or result['hyd_free_convection_sensible_heat_flux'] or
                result['hyd_long_wave_back_radiation'] or result['hyd_cloudiness']) else False
            # 2. Sources/Sinks Points
            if result['sources']:
                result['source_prescribed_discharge'] = checkVariables(data, 'source_sink_prescribed_discharge')
                result['source_prescribed_salinity'] = checkVariables(data, 'source_sink_prescribed_salinity_increment')
                result['source_prescribed_temperature'] = checkVariables(data, 'source_sink_prescribed_temperature_increment')
                result['source_current_discharge'] = checkVariables(data, 'source_sink_current_discharge')
                result['source_cumulative_volume'] = checkVariables(data, 'source_sink_cumulative_volume')
                result['source_average_discharge'] = checkVariables(data, 'source_sink_discharge_average')
            # 3. Cross sections
            if result['cross_sections']:
                result['cross_sections_velocity'] = checkVariables(data, 'cross_section_velocity')
                result['cross_sections_area'] = checkVariables(data, 'cross_section_area')
                result['cross_sections_discharge'] = checkVariables(data, 'cross_section_discharge')
                result['cross_sections_cumulative_discharge'] = checkVariables(data, 'cross_section_cumulative_discharge')
                result['cross_section_salt'] = checkVariables(data, 'cross_section_salt')
                result['cross_sections_cumulative_salt'] = checkVariables(data, 'cross_section_cumulative_salt')
                result['cross_section_temperature'] = checkVariables(data, 'cross_section_temperature')
                result['cross_section_cumulative_temperature'] = checkVariables(data, 'cross_section_cumulative_temperature')
                result['cross_section_contaminant'] = checkVariables(data, 'cross_section_Contaminant')
                result['cross_section_cumulative_contaminant'] = checkVariables(data, 'cross_section_cumulative_Contaminant')
            # 4. Hydrodynamic Water balance
            result['hyd_wb_total_volume'] = checkVariables(data, 'water_balance_total_volume')
            result['hyd_wb_storage'] = checkVariables(data, 'water_balance_storage')
            result['hyd_wb_inflow_boundaries'] = checkVariables(data, 'water_balance_boundaries_in')
            result['hyd_wb_outflow_boundaries'] = checkVariables(data, 'water_balance_boundaries_out')
            result['hyd_wb_total_boundaries'] = checkVariables(data, 'water_balance_boundaries_total')
            result['hyd_wb_total_precipitation'] = checkVariables(data, 'water_balance_precipitation_total')
            result['hyd_wb_total_evaporation'] = checkVariables(data, 'water_balance_evaporation')
            result['hyd_wb_source_sink'] = checkVariables(data, 'water_balance_source_sink')
            result['hyd_wb_inflow_groundwater'] = checkVariables(data, 'water_balance_groundwater_in')
            result['hyd_wb_outflow_groundwater'] = checkVariables(data, 'water_balance_groundwater_out')
            result['hyd_wb_total_groundwater'] = checkVariables(data, 'water_balance_groundwater_total')
            result['hyd_wb_ground_precipitation'] = checkVariables(data, 'water_balance_precipitation_on_ground')
            result['hyd_wb_volume_error'] = checkVariables(data, 'water_balance_volume_error')
            result['hyd_water_balance'] = True if (result['hyd_wb_total_volume'] or
                result['hyd_wb_inflow_boundaries'] or result['hyd_wb_outflow_boundaries'] or
                result['hyd_wb_total_boundaries'] or result['hyd_wb_total_precipitation'] or
                result['hyd_wb_total_evaporation'] or result['hyd_wb_source_sink'] or
                result['hyd_wb_inflow_groundwater'] or result['hyd_wb_outflow_groundwater'] or
                result['hyd_wb_total_groundwater'] or result['hyd_wb_ground_precipitation'] or
                result['hyd_wb_storage'] or result['hyd_wb_volume_error']) else False
        # This is a hydrodynamic map file
        elif ('time' in data.sizes and any(k in data.sizes for k in ['mesh2d_nNodes', 'mesh2d_nEdges'])):
            result['hyd'] = True
            print(f"- Checking Hydrodynamics Simulation: Map file ...")
            result['z_layers'] = checkVariables(data, 'mesh2d_layer_z')
            # Prepare data for thermocline parameters
            # 1. Thermocline
            result['thermocline_temp'] = checkVariables(data, 'mesh2d_tem1')
            # 2. Spatial single layer hydrodynamic maps
            result['hyd_wl_dynamic'] = checkVariables(data, 'mesh2d_s1')
            result['hyd_wd_dynamic'] = checkVariables(data, 'mesh2d_waterdepth')
            result['single_layer'] = True if (result['hyd_wl_dynamic'] or result['hyd_wd_dynamic']) else False
            # 3. Spatial multi layer hydrodynamic maps
            result['spatial_salinity'] = checkVariables(data, 'mesh2d_sa1')
            result['spatial_contaminant'] = checkVariables(data, 'mesh2d_Contaminant')
            result['multi_layer'] = True if (result['thermocline_temp'] or
                result['spatial_salinity'] or result['spatial_contaminant']) else False
            # 4. Spatial static maps
            result['waterdepth_static'] = checkVariables(data, 'mesh2d_waterdepth')
            result['spatial_static'] = True if (result['waterdepth_static']) else False
        # This is a water quality his file
        elif ('nTimesDlwq' in data.sizes and not any(k in data.sizes for k in ['mesh2d_nNodes', 'mesh2d_nEdges'])):
            print(f"- Checking Water Quality Simulation: His file ...")
            variables = set(data.variables.keys()) - set(['nTimesDlwqBnd', 'station_name', 'station_x', 'station_y', 'station_z', 'nTimesDlwq'])
            result['waq_his'], result['waq'] = False, True
            # Prepare data for Physical option
            # 1. Conservative and Decaying Tracers
            if model_type == 'conservative-tracers':
                result['waq_his_conservative_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_conservative_selector'].append(units[item] if item in units.keys() else item)
                result['waq_his_conservative_decay'] = True if len(result['waq_his_conservative_selector']) > 0 else False
                result['waq_his'] = result['waq_his_conservative_decay']
            # 2. Suspended Sediment
            elif model_type == 'suspend-sediment':
                result['waq_his_suspended_sediment_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_suspended_sediment_selector'].append(units[item] if item in units.keys() else item)
                result['waq_his_suspended_sediment'] = True if len(result['waq_his_suspended_sediment_selector']) > 0 else False
                result['waq_his'] = result['waq_his_suspended_sediment']
            # Prepare data for Chemical option
            # 1. Simple Oxygen
            elif model_type == 'simple-oxygen':
                result['waq_his_simple_oxygen_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_simple_oxygen_selector'].append(units[item] if item in units.keys() else item)
                result['waq_his_simple_oxygen'] = True if len(result['waq_his_simple_oxygen_selector']) > 0 else False
                result['waq_his'] = result['waq_his_simple_oxygen']
            # 2. Oxygen and BOD (water phase only)
            elif model_type == 'oxygen-bod-water':
                result['waq_his_oxygen_bod_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_oxygen_bod_selector'].append(units[item] if item in units.keys() else item)            
                result['waq_his_oxygen_bod'] = True if (len(result['waq_his_oxygen_bod_selector'])) else False
                result['waq_his'] = result['waq_his_oxygen_bod']
            # 3. Cadmium
            elif model_type == 'cadmium':
                result['waq_his_cadmium_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_cadmium_selector'].append(units[item] if item in units.keys() else item)
                result['waq_his_cadmium'] = True if len(result['waq_his_cadmium_selector']) > 0 else False
                result['waq_his'] = result['waq_his_cadmium']
            # 4. Eutrophication
            elif model_type == 'eutrophication':
                result['waq_his_eutrophication_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_eutrophication_selector'].append(units[item] if item in units.keys() else item)
                result['waq_his_eutrophication'] = True if len(result['waq_his_eutrophication_selector']) > 0 else False
                result['waq_his'] = result['waq_his_eutrophication']
            # 5. Trace Metals
            elif model_type == 'tracer-metals':
                result['waq_his_trace_metals_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_trace_metals_selector'].append(units[item] if item in units.keys() else item)
                result['waq_his_trace_metals'] = True if len(result['waq_his_trace_metals_selector']) > 0 else False
                result['waq_his'] = result['waq_his_trace_metals']
            # Prepare data for Microbial option
            elif model_type == 'coliform':
                result['waq_his_coliform_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_coliform_selector'].append(units[item] if item in units.keys() else item)
                result['waq_his_coliform'] = True if len(result['waq_his_coliform_selector']) > 0 else False
                result['wq_his'] = result['waq_his_coliform']
        # This is a water quality map file      
        elif ('nTimesDlwq' in data.sizes and any(k in data.sizes for k in ['mesh2d_nNodes', 'mesh2d_nEdges'])):
            print(f'- Checking Water Quality Simulation: Map file ...')
            result['wq_map'], result['waq'] = False, True
            variables = set(data.variables.keys()) - set(['mesh2d', 'mesh2d_node_x', 'mesh2d_node_y', 'mesh2d_edge_x',
                'mesh2d_edge_y', 'mesh2d_face_x_bnd', 'mesh2d_face_y_bnd', 'mesh2d_edge_nodes', 'mesh2d_edge_faces',
                'mesh2d_face_nodes', 'mesh2d_layer_dlwq', 'nTimesDlwqBnd', 'mesh2d_face_x', 'mesh2d_face_y', 'nTimesDlwq'])
            # Prepare data for Physical option
            # 1. Conservative and Decaying Tracers
            if model_type == 'conservative-tracers':
                result['waq_map_conservative_selector'], result['waq_map_conservative_decay'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item): 
                        elements_check = {x[0] for x in result['waq_map_conservative_selector']}
                        if item1 not in elements_check:
                            result['waq_map_conservative_selector'].append((item1, units[item1] if item1 in units.keys() else item1))
                if len(result['waq_map_conservative_selector']) > 0:
                    result['wq_map'], result['waq_map_conservative_decay'] = True, True                
            # 2. Suspended Sediment
            elif model_type == 'suspend-sediment':
                result['waq_map_suspended_sediment_selector'], result['waq_map_suspended_sediment'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_suspended_sediment_selector']}
                        if item1 not in elements_check:
                            result['waq_map_suspended_sediment_selector'].append((item1, units[item1] if item1 in units.keys() else item1))
                if len(result['waq_map_suspended_sediment_selector']) > 0:
                    result['wq_map'], result['waq_map_suspended_sediment'] = True, True
            # Prepare data for Chemical option
            # 1. Simple Oxygen
            elif model_type == 'simple-oxygen':
                result['waq_map_simple_oxygen_selector'], result['waq_map_simple_oxygen'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_simple_oxygen_selector']}
                        if item1 not in elements_check:
                            result['waq_map_simple_oxygen_selector'].append((item1, units[item1] if item1 in units.keys() else item1))
                if len(result['waq_map_simple_oxygen_selector']) > 0:
                    result['wq_map'], result['waq_map_simple_oxygen'] = True, True
            # 2. Oxygen and BOD (water phase only)
            elif model_type == 'oxygen-bod-water':
                result['waq_map_oxygen_bod_selector'], result['waq_map_oxygen_bod'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_oxygen_bod_selector']}
                        if item1 not in elements_check:
                            result['waq_map_oxygen_bod_selector'].append((item1, units[item1] if item1 in units.keys() else item1))
                if len(result['waq_map_oxygen_bod_selector']) > 0:  
                    result['wq_map'], result['waq_map_oxygen_bod'] = True, True                
            # 3. Cadmium
            elif model_type == 'cadmium':
                result['waq_map_cadmium_selector'], result['waq_map_cadmium'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_cadmium_selector']}
                        if item1 not in elements_check:
                            result['waq_map_cadmium_selector'].append((item1, units[item1] if item1 in units.keys() else item1))
                if len(result['waq_map_cadmium_selector']) > 0:
                    result['wq_map'], result['waq_map_cadmium'] = True, True                
            # 4. Eutrophication
            elif model_type == 'eutrophication':
                result['waq_map_eutrophication_selector'], result['waq_map_eutrophication'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_eutrophication_selector']}
                        if item1 not in elements_check:
                            result['waq_map_eutrophication_selector'].append((item1, units[item1] if item1 in units.keys() else item1))
                if len(result['waq_map_eutrophication_selector']) > 0:
                    result['wq_map'], result['waq_map_eutrophication'] = True, True
            # 5. Trace Metals
            elif model_type == 'tracer-metals':
                result['waq_map_trace_metals_selector'], result['waq_map_trace_metals'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_trace_metals_selector']}
                        if item1 not in elements_check:
                            result['waq_map_trace_metals_selector'].append((item1, units[item1] if item1 in units.keys() else item1))
                if len(result['waq_map_trace_metals_selector']) > 0:
                    result['wq_map'], result['waq_map_trace_metals'] = True, True
            # Prepare data for Microbial option
            elif model_type == 'coliform':
                result['waq_map_coliform_selector'], result['waq_map_coliform'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x for x in result['waq_map_coliform_selector']}
                        if item1 not in elements_check:
                            result['waq_map_coliform_selector'].append((item1, units[item1] if item1 in units.keys() else item1))
                if len(result['waq_map_coliform_selector']) > 0:
                    result['wq_map'], result['waq_map_coliform'] = True, True
        result['hide_map'] = result['spatial_map'] = True if (result['single_layer'] or result['multi_layer']) else False
    return result

def valueToKeyConverter(values: list, dict: dict=units) -> list:
    """
    Convert a list of values to a list of keys.

    Parameters:
    ----------
    values: list
        The list of values.
    dict: dict
        The dictionary containing the keys and values.

    Returns:
    -------
    list
        The list of keys.
    """
    result = []
    for value in values:
        for key, val in dict.items():
            if value == val:
                result.append(key)
                break
    return result

def dialogReader(dialog_file: str) -> dict:
    """
    Read the dialog file and return the configuration.

    Parameters:
    ----------
    dialog_file: str
        The path of the dialog *.dia file.

    Returns:
    -------
    dict
        The dictionary containing the configuration.
    """
    # Check if the dialog file exists
    if not os.path.exists(dialog_file): return {}
    result = {}
    with open(f'{dialog_file}', 'r') as f:
        content = f.read()
    content = content.split('\n')
    for line in content:
        if "Computation started" in line:
            temp = pd.to_datetime(line.split(': ')[2], format='%H:%M:%S, %d-%m-%Y')
            result["computation_start"] = temp.strftime('%Y-%m-%d %H:%M:%S')
        if "Computation finished" in line:
            temp = pd.to_datetime(line.split(': ')[2], format='%H:%M:%S, %d-%m-%Y')
            result["computation_finish"] = temp.strftime('%Y-%m-%d %H:%M:%S')
        if "my model area" in line:
            temp = line.split(': ')[2]
            result["area"] = float(temp.strip())
        if "my model volume" in line:
            temp = line.split(': ')[2]
            result["volume"] = float(temp.strip())
    return result

def getSummary(dialog_path: str, Out_files: list) -> list:
    """
    Get the summary of the dataset received from *.nc file.

    Parameters:
    ----------
    dialog_path: str
        The path of the dialog *.dia file.
    Out_files: list
        List of _his.zarr files.

    Returns:
    -------
    list
        The list containing the summary of the dataset.
    """
    dialog, result = dialogReader(dialog_path), []
    # --- Dialog info ---
    if len(dialog) > 0:
        result.append({'parameter': 'Computation started', 'value': dialog['computation_start']})
        result.append({'parameter': 'Computation finished', 'value': dialog['computation_finish']})
        result.append({'parameter': 'Area (m2)', 'value': dialog['area']})
        result.append({'parameter': 'Volume (m3)', 'value': dialog['volume']})
    if len(Out_files) == 0: return result
    for data_his in Out_files:
        if data_his is None: continue
        sizes = data_his.sizes
        # --- Hydrodynamic ---
        if 'time' in sizes:
            time_var = data_his['time']
            start_hyd = pd.to_datetime(time_var.isel(time=0).values).strftime('%Y-%m-%d %H:%M:%S')
            end_hyd = pd.to_datetime(time_var.isel(time=-1).values).strftime('%Y-%m-%d %H:%M:%S')
            result.append({'parameter': 'Start Date (Hydrodynamic Simulation)', 'value': start_hyd})
            result.append({'parameter': 'Stop Date (Hydrodynamic Simulation)', 'value': end_hyd})
            result.append({'parameter': 'Number of Time Steps', 'value': sizes['time']})
        if ('laydim' in sizes): result.append({'parameter': 'Number of Layers', 'value': sizes['laydim']})
        if ('stations' in sizes and sizes['stations'] > 0): result.append({'parameter': 'Number of Observation Stations', 'value': sizes['stations']})
        if ('cross_section' in sizes and sizes['cross_section'] > 0): result.append({'parameter': 'Number of Cross Sections', 'value': sizes['cross_section']})
        if ('source_sink' in sizes and sizes['source_sink'] > 0): result.append({'parameter': 'Number of Sources/Sinks', 'value': sizes['source_sink']})
        # --- Water Quality ---
        if 'nTimesDlwq' in sizes:
            waq_time = data_his['nTimesDlwq']
            start_waq = pd.to_datetime(waq_time.isel(nTimesDlwq=0).values).strftime('%Y-%m-%d %H:%M:%S')
            end_waq = pd.to_datetime(waq_time.isel(nTimesDlwq=-1).values).strftime('%Y-%m-%d %H:%M:%S')
            result.append({'parameter': f'Start Date (Water Quality Simulation)', 'value': start_waq})
            result.append({'parameter': f'Stop Date (Water Quality Simulation)', 'value': end_waq})
            result.append({'parameter': f'Number of Time Steps (Water Quality Simulation)', 'value': sizes['nTimesDlwq']})
        if ('nStations' in sizes): result.append({'parameter': f'Number of Observation Stations (Water Quality Simulation)', 'value': sizes['nStations']})
    return result

def checkCoordinateReferenceSystem(name: str, geometry: gpd.GeoSeries, data_his: xr.Dataset) -> gpd.GeoDataFrame:
    """
    Convert GeoDataFrame to WGS84.

    Parameters:
    ----------
    name: str
        The column name.
    data: gpd.GeoDataFrame
        The GeoDataFrame to convert.
    data_his: xr.Dataset
        The dataset received from _his file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame converted to WGS84.
    """
    # Check coordinate reference system
    if 'wgs84' in data_his.variables:
        crs_code = data_his['wgs84'].attrs.get('EPSG_code', 4326)
        result = gpd.GeoDataFrame(data={'name': name, 'geometry': geometry}, crs=crs_code)
    else:
        crs_code = data_his['projected_coordinate_system'].get('EPSG_code', 4326)
        result = gpd.GeoDataFrame(data={'name': name, 'geometry': geometry}, crs=crs_code)
        result = result.to_crs(epsg=4326)  # Convert to WGS84 if not already
    return result

def hydCreator(data_his: xr.Dataset) -> tuple[gpd.GeoDataFrame, list]:
    """
    Create a GeoDataFrame for hydrodynamic observations.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of hydrodynamic observations.
    list_dict: list
        The list of dictionaries of components for each observation station.
    """
    target_dims = ('time', 'stations', 'laydim')
    names, listPoints = [name.decode('utf-8').strip() for name in data_his['station_name'].data.compute()], []
    x, y = data_his['station_x_coordinate'].data.compute(), data_his['station_y_coordinate'].data.compute()
    gdf = checkCoordinateReferenceSystem(names, gpd.points_from_xy(x, y), data_his)
    vars = [var for var in data_his.data_vars if data_his[var].dims == target_dims]
    for name in names:
        station_dict = {name: [{var: variablesNames.get(var, var)} for var in vars]}
        listPoints.append(station_dict)
    return gdf, listPoints

def obsCreator(points: list) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of observations for water quality observations.

    Parameters:
    ----------
    points: list
        The list of points, format: [[Name, latitude, longitude], ...]

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of observations.
    """
    df = pd.DataFrame(points, columns=['name', 'latitude', 'longitude'])
    geometry = gpd.points_from_xy(df['longitude'], df['latitude'])
    return gpd.GeoDataFrame({'name': df['name'], 'geometry': geometry}, crs="EPSG:4326")

def sourceCreator(data_his: xr.Dataset) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of sources/sinks.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of sources/sinks.
    """
    names = [name.decode('utf-8').strip() for name in data_his['source_sink_name'].data.compute()]
    x, y = data_his['source_sink_x_coordinate'].data.compute()[0], data_his['source_sink_y_coordinate'].data.compute()[0]
    geometry = gpd.points_from_xy(x, y)
    return checkCoordinateReferenceSystem(names, geometry, data_his)

def linearCreator(x_coords: np.ndarray, y_coords: np.ndarray) -> gpd.GeoDataFrame:
    """
    Create a linear line from x and y coordinates and clip it with the bounding box.

    Parameters:
    ----------
    x_coords: np.ndarray
        The x coordinates of the line.
    y_coords: np.ndarray
        The y coordinates of the line.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of linear.
    """
    if (len(x_coords) < 2 and len(y_coords) < 2):
        print('Not enough points to create a linear.')
        return None, None
    a, b = np.polyfit(x_coords, y_coords, 1)
    # Get bounding box
    x_min, x_max = x_coords.min(), x_coords.max()
    y_min, y_max = y_coords.min(), y_coords.max()
    # Intersect with bounding box
    candidates = []
    # Intersect with x = x_min, x = x_max
    y_left, y_right = a * x_min + b, a * x_max + b
    if y_min <= y_left <= y_max: candidates.append((float(x_min), float(y_left)))
    if y_min <= y_right <= y_max: candidates.append((float(x_max), float(y_right)))
    if len(candidates) == 0: candidates.append((x_coords[0], y_coords[0]))
    # Intersect with y = y_min, y = y_max
    if abs(a) > 1e-12:  # avoid division by zero
        x_bottom, x_top = (y_min - b) / a, (y_max - b) / a
        if x_min <= x_bottom <= x_max: candidates.append((float(x_bottom), float(y_min)))
        if x_min <= x_top <= x_max: candidates.append((float(x_top), float(y_max)))
    if len(candidates) == 1: candidates.append((x_coords[-1], y_coords[-1]))
    return candidates[0], candidates[1]

def crosssectionCreator(data_his: xr.Dataset) -> tuple[gpd.GeoDataFrame, list]:
    """
    Create a GeoDataFrame of cross-section.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of cross-sections.
    list
        The list of dictionaries of cross-sections.
    """
    names, listAttributes = [name.decode('utf-8').strip() for name in data_his['cross_section_name'].data.compute()], []
    x = data_his['cross_section_geom_node_coordx'].data.compute()
    y = data_his['cross_section_geom_node_coordy'].data.compute()
    p1, p2 = linearCreator(x, y)
    geometry = gpd.GeoSeries([shapely.geometry.LineString([p1, p2])])
    gdf = checkCoordinateReferenceSystem(names, geometry, data_his)
    crsValues = [
        'cross_section_velocity', 'cross_section_area', 'cross_section_discharge', 'cross_section_cumulative_discharge',
        'cross_section_temperature', 'cross_section_cumulative_temperature', 'cross_section_salt',
        'cross_section_cumulative_salt', 'cross_section_Contaminant', 'cross_section_cumulative_Contaminant'
    ]
    listAttributes = [{item: variablesNames[item] if item in variablesNames else item} for item in crsValues]
    return gdf, listAttributes

def selectInsitu(data_his: xr.Dataset, data_map: xr.Dataset, name: str, stationId: str, type: str) -> pd.DataFrame:
    """
    Get insitu data.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his file.
    data_map: xr.Dataset
        The dataset received from _map file.
    name: str
        The name of defined variable in _his file.
    stationId: str
        The name of the station.
    type: str
        The type of data, accepted values are: 'station_name' or 'source_sink_name'.

    Returns:
    -------
    pd.DataFrame
        A DataFrame containing the insitu data.
    """
    names = [x.decode('utf-8').strip() for x in data_his[type].data.compute()]
    if stationId not in names: return pd.DataFrame()
    idx = names.index(stationId)
    index = [pd.to_datetime(id).strftime('%Y-%m-%d %H:%M:%S') for id in data_his['time'].data]
    if type == 'station_name':
        result = pd.DataFrame(index=index)
        z_layer = numberFormatter(data_map['mesh2d_layer_z'].data.compute())
        arr = data_his[name].data[:, idx, :].compute()
        for i in range(arr.shape[1]):
            i_rev = -(i+1)
            result[f'Depth: {z_layer[i_rev]} m'] = numberFormatter(arr[:, i_rev])
    else:
        temp = pd.DataFrame(data_his[variablesNames[name]].values, columns=names, index=index)
        result = temp[[stationId]]
    return result.dropna(axis=1, how='all').reset_index()

def thermoclineComputer(data_map: xr.Dataset) -> pd.DataFrame:
    """
    Compute thermocline in each time step.

    Parameters:
    ----------
    data_map: xr.Dataset
        The dataset received from _map file.

    Returns:
    -------
    pd.DataFrame
        The DataFrame containing the thermocline in each time step.
    """
    z_layers = numberFormatter(data_map['mesh2d_layer_z'].data.compute())
    times, temp = data_map['time'].data.compute(), data_map['mesh2d_tem1'].data
    mean = da.nanmean(temp, axis=1).compute()
    columns = [pd.to_datetime(id).strftime('%Y-%m-%d %H:%M:%S') for id in times]
    df = pd.DataFrame(mean.T, index=z_layers, columns=columns)


    # columns, data_list = [], []
    # for i in range(len(times)):
    #     col_name = pd.to_datetime(times[i]).strftime('%Y-%m-%d %H:%M:%S')
    #     value = np.nanmean(data_map['mesh2d_tem1'].values[i,:,:], axis=0)
    #     columns.append(col_name)
    #     data_list.append(numberFormatter(value))
    # df = pd.DataFrame(np.column_stack(data_list), index=z_layers, columns=columns)
    return df.reset_index()

def timeseriesCreator(data_his: xr.Dataset, key: str, timeColumn: str='time') -> pd.DataFrame:
    """
    Create a GeoDataFrame of timeseries.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his file.
    key: str
        The key of the timeseries, used to define the name of the variable.
    columns: list
        The columns of the timeseries.

    Returns:
    -------
    pd.DataFrame
        The DataFrame of timeseries.
    """
    name = 'source_sink_name' if key.endswith('_source') else 'station_name'
    columns = [i.decode('utf-8').strip() for i in data_his[name].data.compute()]
    temp = variablesNames.get(key, key)
    if key.startswith('wb_'): columns = ['Water balance'] # Used for water balance
    elif key.endswith('_crs'): 
        columns = ['Cross-section'] # Used for cross-section
        temp = key.replace('_crs', '')
    if name not in data_his.variables.keys(): return pd.DataFrame()
    index = [pd.to_datetime(i).strftime('%Y-%m-%d %H:%M:%S') for i in data_his[timeColumn].data]
    df = pd.DataFrame(index=index, data=numberFormatter(data_his[temp].data.compute()), columns=columns)
    return df.reset_index()

def unstructuredGridCreator(data_map: xr.Dataset) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of unstructured grid.

    Parameters:
    ----------
    data_map: xr.Dataset
        The dataset received from _map file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of unstructured grid.
    """
    # Use dask array to speed up, keep lazy-load
    node_x, node_y = data_map['mesh2d_node_x'].data, data_map['mesh2d_node_y'].data
    coords = da.stack([node_x, node_y], axis=1)
    faces = xr.where(np.isnan(data_map['mesh2d_face_nodes']), 0, data_map['mesh2d_face_nodes']).data.astype(int)-1
    counts = da.sum(faces != -1, axis=1)
    # Compute to create polygons
    coords_np, faces_np, counts_np = coords.compute(), faces.compute(), counts.compute()
    polygons = [shapely.geometry.Polygon(coords_np[face[:count]]) for face, count in zip(faces_np, counts_np)]
    # Check coordinate reference system
    if 'wgs84' in data_map.variables:
        crs_code = data_map['wgs84'].attrs.get('EPSG_code', 4326)
        grid = gpd.GeoDataFrame(geometry=polygons, crs=crs_code)
    else:
        crs_code = data_map['projected_coordinate_system'].attrs.get('EPSG_code', 4326)
        # Convert to WGS84 if not already
        grid = gpd.GeoDataFrame(geometry=polygons, crs=crs_code).to_crs(epsg=4326)
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
    value = np.sum(weight * z_values[idx], axis=1)/np.sum(weight, axis=1)
    return numberFormatter(value)

def layerCounter(data_map: xr.Dataset) -> dict:
    """
    Check how many layers are available.

    Parameters:
    ----------
    data_map: xr.Dataset
        The dataset received from _map file.

    Returns:
    -------
    dict
        A dictionary containing the index and value of velocity layers.
    """
    layers, z_layer = {}, np.round(data_map['mesh2d_layer_z'].data.compute(), 2)
    # Add depth-average if available
    if {'mesh2d_ucxa', 'mesh2d_ucya'}.issubset(data_map.variables.keys()): layers[-1] = 'Average'
    # Iterate from bottom to surface
    ucx = data_map['mesh2d_ucx'].data
    ucy = data_map['mesh2d_ucy'].data
    ucm = data_map['mesh2d_ucmag'].data
    for i in reversed(range(len(z_layer))):
        # Use dask to speed up, keep lazy-load
        ucx_i = ucx[:, :, i].compute()
        ucy_i = ucy[:, :, i].compute()
        ucm_i = ucm[:, :, i].compute()
        # Check if all values are nan
        if (np.isnan(ucx_i).all() or np.isnan(ucy_i).all() or np.isnan(ucm_i).all()): continue
        layers[len(z_layer)-i-1] = f'Depth: {z_layer[i]} m'
    return layers

def vectorComputer(data_map: xr.Dataset, value_type: str, layer_reverse: dict, step: int=-1) -> gpd.GeoDataFrame:
    """
    Compute vector in each layer and average value (if possible)

    Parameters:  
    ----------
    data_map: xr.Dataset
        The dataset received from _map file.
    value_type: str
        The type of vector to compute: 'Average' or one specific layer.
    layer_reverse: dict
        The dictionary containing the index and value of reversed vector layers.
    step: int
        The index of the interested time step.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame containing the vector map of the mesh.
    """
    if step < 0: step = len(data_map['time']) - 1
    if value_type == 'Average':
        # Average velocity in each layer
        ucx = data_map['mesh2d_ucxa'].isel(time=step).values
        ucy = data_map['mesh2d_ucya'].isel(time=step).values
        ucm = data_map['mesh2d_ucmaga'].isel(time=step).values
    else:
        # Velocity for specific layer (in reverse order)
        row_idx = len(layer_reverse) - int(layer_reverse[value_type]) - 1
        ucx = data_map['mesh2d_ucx'].isel(time=step).values[:, row_idx-1]
        ucy = data_map['mesh2d_ucy'].isel(time=step).values[:, row_idx-1]
        ucm = data_map['mesh2d_ucmag'].isel(time=step).values[:, row_idx-1]
    # Get indices of non-nan values
    col_idx = np.where(~np.isnan(ucx) & ~np.isnan(ucy) & ~np.isnan(ucm))
    x_coords = data_map['mesh2d_face_x'].values[col_idx]
    y_coords = data_map['mesh2d_face_y'].values[col_idx]
    # Prepare values
    ucx_flat = np.round(ucx.astype(np.float64), 5) 
    ucy_flat = np.round(ucy.astype(np.float64), 5) 
    ucm_flat = np.round(ucm.astype(np.float64), 2)
    result = {"time": pd.to_datetime(data_map['time'].values[step]).strftime('%Y-%m-%d %H:%M:%S'),
        "coordinates": np.column_stack((x_coords, y_coords)).tolist(),
        "values": np.vstack([ucx_flat, ucy_flat, ucm_flat]).T.tolist(),
    }
    return result

def fileWriter(template_path: str, params: dict) -> str:
    """
    Write to file with predefined parameters

    Parameters
    ----------
    template_path: str
        The path of template file
    params: dict
        The dictionary of parameters

    Returns
    -------
    str
        The content of saved file
    """
    # Open the file and read its contents
    with open(template_path, 'r') as file:
        file_content = file.read()
    # Replace placeholders with actual values
    for key, value in params.items():
        file_content = file_content.replace(f'{{{key}}}', str(value))
    # Adjust the structure
    lines, result = [], []
    for line in file_content.split('\n'):
        if '#' in line and not line.strip().startswith('#'):
            left, right = line.split('#', 1)
            left, middle = left.split("=", 1)
            lines.append((left + " = ", middle.strip(), '#' + right.strip()))
        else: lines.append((line.strip(), "", ""))
    max_len = max(len(middle) for _, middle, _ in lines) + 1
    for left, middle, right in lines:
        result.append(left + middle.ljust(max_len) + right)
    result = "\n".join(result)
    return result

def contentWriter(project_name: str, filename: str, data: list, content: str, unit: str='sec') -> tuple:
    """
    Write to file with predefined parameters

    Parameters
    ----------
    project_name: str
        The name of the project
    filename: str
        The name of the file
    data: list
        The list of data
    content: str
        The content of the file
    ref_utc: datetime
        The reference time
    unit: str
        The unit of time

    Returns
    -------
    tuple
        The status and message
    """
    try:
        path = os.path.join(PROJECT_STATIC_ROOT, project_name, "input")
        # Write weather.tim file
        with open(os.path.join(path, filename), 'w') as f:
            for row in data:
                if unit == 'sec': row[0] = int(row[0]/1000)
                elif unit == 'min': row[0] = int(row[0]/(1000*60))
                temp = '  '.join([str(r) for r in row])
                f.write(f"{temp}\n")
        # Add weather data to FlowFM.ext file
        ext_path = os.path.join(path, "FlowFM.ext")
        if os.path.exists(ext_path):
            with open(ext_path, encoding="utf-8") as f:
                update_content = f.read()
            parts = re.split(r'\n\s*\n', update_content)
            parts = [p.strip() for p in parts if p.strip()]
            if (any(filename in part for part in parts)): 
                index = parts.index([part for part in parts if filename in part][0])
                parts[index] = content
            else: parts.append(content)
            with open(ext_path, 'w') as file:
                file.write(f"\n{'\n\n'.join(parts)}\n")
        else:
            with open(ext_path, 'w') as f:
                f.write(f"\n{content}\n")
        status, message = 'ok', f"Data is saved successfully."
    except Exception as e:
        status, message = 'error', f"Error: {str(e)}"
    return status, message

def postProcess(directory: str) -> dict:
    """
    Moving folders generated by FlowFM

    Parameters
    ----------
    directory: str
        The directory of the project

    Returns
    -------
    dict
        {'status': 'ok'/'error', 'message': str}
    """
    try:
        parent_path = os.path.dirname(directory)
        output_folder = os.path.join(parent_path, 'output')
        os.makedirs(output_folder, exist_ok=True) if not os.path.exists(output_folder) else shutil.rmtree(output_folder, onexc=remove_readonly)
        output_HYD_path = os.path.join(output_folder, 'HYD')
        # Create the directory output_HYD_path
        if os.path.exists(output_HYD_path): shutil.rmtree(output_HYD_path, onexc=remove_readonly)
        os.makedirs(output_HYD_path, exist_ok=True)
        subdirs = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
        if not subdirs: return {'status': 'error', 'message': 'No simulation output folders found.'}
        # Copy folder DFM_DELWAQ to the parent directory
        DFM_DELWAQ_from = os.path.join(directory, 'DFM_DELWAQ')
        DFM_DELWAQ_to = os.path.join(parent_path, 'DFM_DELWAQ')
        if os.path.exists(DFM_DELWAQ_to): shutil.rmtree(DFM_DELWAQ_to, onexc=remove_readonly)
        if os.path.exists(DFM_DELWAQ_from):
            shutil.copytree(DFM_DELWAQ_from, DFM_DELWAQ_to)
            shutil.rmtree(DFM_DELWAQ_from, onexc=remove_readonly)
        # Copy files to the directory output
        DFM_OUTPUT_folder = os.path.join(directory, 'DFM_OUTPUT')
        if not os.path.exists(DFM_OUTPUT_folder):
            return {'status': 'error', 'message': 'No output folder found.'}
        select_files = ['FlowFM.dia', 'FlowFM_his.nc', 'FlowFM_map.nc']
        found_files = [f for f in os.listdir(DFM_OUTPUT_folder) 
                       if (os.path.isfile(os.path.join(DFM_OUTPUT_folder, f)) and f in select_files)]
        if not found_files: return {'status': 'error', 'message': 'No required files found in the output folder.'}
        # Convert .nc files to .zarr and save to output_HYD_path
        for f in found_files:
            if f.endswith('.nc'):
                ds = xr.open_dataset(os.path.join(DFM_OUTPUT_folder, f), chunks={'time': 1})
                zarr_path = os.path.join(output_HYD_path, f.replace('.nc', '.zarr'))
                ds.to_zarr(zarr_path, mode='w', consolidated=True)
                ds.close()
            else: shutil.copy(os.path.join(DFM_OUTPUT_folder, f), output_HYD_path)
        # Clean DFM_OUTPUT folder
        shutil.rmtree(DFM_OUTPUT_folder, onexc=remove_readonly)
        return {'status': 'ok', 'message': 'Data is saved successfully.'}
    except Exception as e: return {'status': 'error', 'message': {str(e)}}

def clean_nans(obj) -> dict:
    """
    Clean nans in dictionary

    Parameters
    ----------
    obj: dict
        The dictionary to clean

    Returns
    -------
    dict
        The cleaned dictionary
    """
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    elif isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    else: return obj

def interpolate_Profile(array: np.ndarray, depths: list, x_new: float, col: int) -> float:
    """
    Interpolate value from 2D array based on x_new and column index col for profile data.

    Parameters
    ----------
    array: np.ndarray
        The 2D array of values containing values at specific layers.
    depths: list
        The list of depth values corresponding with index.
    x_new: float
        The new x value to interpolate.
    col: int
        The column index to interpolate.

    Returns
    -------
    float
        The interpolated value.
    """
    if array is None or col >= array.shape[1]: return np.nan
    series = np.asarray(array[:, col], dtype=float)
    mask = ~np.isnan(series)
    valid_depths, valid_values = np.array(depths)[mask], series[mask]
    # If no valid values -> return nan
    if len(valid_depths) == 0: return np.nan
    # If only one valid value -> return that value
    if len(valid_depths) == 1: return float(valid_values[0])
    # If x_new smaller than min -> get min value
    if x_new <= valid_depths.min(): return float(valid_values[np.argmin(valid_depths)])
    # If x_new larger than max -> get max value
    if x_new >= valid_depths.max(): return float(valid_values[np.argmax(valid_depths)])
    # If x_new in between -> find indices and interpolate
    idx = np.searchsorted(valid_depths, x_new)
    b1, b2 = valid_depths[idx - 1], valid_depths[idx]
    v1, v2 = valid_values[idx - 1], valid_values[idx]
    return float(v1 + (v2 - v1) * (x_new - b1) / (b2 - b1))