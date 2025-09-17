import shapely, os, re, shutil, stat
import geopandas as gpd, pandas as pd
import numpy as np, xarray as xr
from scipy.spatial import cKDTree
from dateutil import parser
from datetime import datetime, timezone
from config import PROJECT_STATIC_ROOT

def remove_readonly(func, path, excinfo):
    # Change the readonly bit, but not the file contents
    os.chmod(path, stat.S_IWRITE)
    func(path)

variablesNames = {
    # For In-situ options
    'temp':'temperature', 'sal':'salinity', 'cont':'Contaminant', # For stations
    'pre_discharge_source':'source_sink_prescribed_discharge', 'pre_discharge_increment_source':'source_sink_prescribed_salinity_increment', # For sources
    'pre_temperature_increment_source':'source_sink_prescribed_temperature_increment', 'avg_discharge_source':'source_sink_discharge_average', # For sources
    'discharge_source':'source_sink_current_discharge', 'cumulative_volume_source':'source_sink_cumulative_volume',  # For sources
    'velocity_crs':'cross_section_velocity', 'area_crs':'cross_section_area',  'discharge_crs':'cross_section_discharge', # For cross sections
    'culdis_crs':'cross_section_cumulative_discharge', 'salt_crs':'cross_section_salt', 'cumsalt_crs': 'cross_section_cumulative_salt', # For cross sections
    'temp_crs':'cross_section_temperature', 'cumtemp_crs':'cross_section_cumulative_temperature', # For cross sections
    'cont_crs':'cross_section_Contaminant', 'cumcont_crs':'cross_section_cumulative_Contaminant', # For cross sections
    # For Static map
    'depth':'depth',
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
    # For Water quality options at point
    'fdf_POC_wq':'DetC', 'fdf_PON_wq':'DetN', 'fdf_POP_wq':'DetP', 'df_NH4_wq':'NH4', 'df_NO3_wq':'NO3', 'df_PO4_wq':'PO4',
    'df_DO_wq':'OXY', 'df_Chl_wq':'Cl', 'nitrogen_total_wq':'TotN', 'nitrogen_algae_wq':'AlgN', 'nitrogen_kjeldahl_wq':'KjelN',
    'phosphorus_total_wq':'TotP', 'phosphorus_algae_wq': 'AlgP', 'daylength_greens_wq':'LimDLGreen', 'nutrient_greens_wq':'LimNutGree',
    'radiation_greens_wq':'LimRadGree', 'inorganic_matter_wq':'IM1', 'opal_si_wq':'Opal', 'sediment_oxygen_wq':'SOD', 'suspended_solids_wq':'SS',
    'chlorophyll_wq':'Chlfa', 'extinction_phytoplankton_wq':'ExtVlPhyt', 'adsorbed_ortho_phosphate_wq':'AAP', 'dyamo_wq':'GREEN',
    # For Dynamic map: Hydrodynamics
    'wl_dynamic':'mesh2d_s1', 'wd_dynamic':'mesh2d_waterdepth',
    # For Dynamic map: Physical options
    'temp_multi_dynamic':'mesh2d_tem1', 'sal_multi_dynamic':'mesh2d_sa1', 'cont_multi_dynamic':'mesh2d_Contaminant',
    # For Dynamic map: Water Quality options
    'fdf_POC_wq_map_dynamic':'mesh2d_2d_DetC', 'fdf_POC_wq_map_multi_dynamic':'mesh2d_DetC', 'fdf_PON_wq_map_dynamic':'mesh2d_2d_DetN', 'fdf_PON_wq_map_multi_dynamic':'mesh2d_DetN',
    'fdf_POP_wq_map_dynamic':'mesh2d_2d_DetP', 'fdf_POP_wq_map_multi_dynamic':'mesh2d_DetP', 'df_NH4_wq_map_dynamic':'mesh2d_2d_NH4', 'df_NH4_wq_map_multi_dynamic':'mesh2d_NH4',
    'df_NO3_wq_map_dynamic':'mesh2d_2d_NO3', 'df_NO3_wq_map_multi_dynamic':'mesh2d_NO3', 'df_PO4_wq_map_dynamic':'mesh2d_2d_PO4', 'df_PO4_wq_map_multi_dynamic':'mesh2d_PO4',
    'fdf_OXY_wq_map_dynamic':'mesh2d_2d_OXY', 'fdf_OXY_wq_map_multi_dynamic':'mesh2d_OXY', 'fdf_OXY_wq_map_dynamic':'mesh2d_2d_Cl', 'fdf_OXY_wq_map_multi_dynamic':'mesh2d_Cl',
    'nitrogen_total_wq_map_dynamic':'mesh2d_2d_TotN', 'nitrogen_total_wq_map_multi_dynamic':'mesh2d_TotN', 'nitrogen_total_wq_map_dynamic':'mesh2d_2d_AlgN',
    'nitrogen_total_wq_map_multi_dynamic':'mesh2d_AlgN', 'nitrogen_kjeldahl_wq_map_dynamic':'mesh2d_2d_KjelN', 'nitrogen_kjeldahl_wq_map_multi_dynamic':'mesh2d_KjelN',
    'nitrogen_kjeldahl_wq_map_dynamic':'mesh2d_2d_KjelN', 'nitrogen_kjeldahl_wq_map_multi_dynamic':'mesh2d_KjelN', 'total_phosphorus_wq_map_dynamic':'mesh2d_2d_TotP',
    'total_phosphorus_wq_map_multi_dynamic':'mesh2d_TotP', 'phosphorus_algae_wq_map_dynamic':'mesh2d_2d_AlgP', 'phosphorus_algae_wq_map_multi_dynamic':'mesh2d_AlgP',
    'daylength_greens_wq_map_dynamic':'mesh2d_2d_LimDLGreen', 'daylength_greens_wq_map_multi_dynamic':'mesh2d_LimDLGreen',
    'nutrient_greens_wq_map_dynamic':'mesh2d_2d_LimNutGree', 'nutrient_greens_wq_map_multi_dynamic':'mesh2d_LimNutGree',
    'radiation_greens_wq_map_dynamic':'mesh2d_2d_LimRadGree', 'radiation_greens_wq_map_multi_dynamic':'mesh2d_LimRadGree',
    'adsorbed_ortho_phosphate_wq_map_dynamic':'mesh2d_2d_AAP', 'adsorbed_ortho_phosphate_wq_map_multi_dynamic':'mesh2d_AAP',
    'dyamo_wq_map_dynamic':'mesh2d_2d_GREEN', 'dyamo_wq_map_multi_dynamic':'mesh2d_GREEN', 'inorganic_matter_wq_map_dynamic':'mesh2d_2d_IM1', 'inorganic_matter_wq_map_multi_dynamic':'mesh2d_IM1',
    'opal_si_wq_map_dynamic':'mesh2d_2d_Opal', 'opal_si_wq_map_multi_dynamic':'mesh2d_Opal', 'sediment_oxygen_wq_map_dynamic':'mesh2d_2d_SOD', 'sediment_oxygen_wq_map_multi_dynamic':'mesh2d_SOD',
    'suspended_solids_wq_map_dynamic':'mesh2d_2d_SS', 'suspended_solids_wq_map_multi_dynamic':'mesh2d_SS', 'chlorophyll_wq_map_dynamic':'mesh2d_2d_Chlfa', 'chlorophyll_wq_map_multi_dynamic':'mesh2d_Chlfa',
    'extinction_phytoplankton_wq_map_dynamic':'mesh2d_2d_ExtVlPhyt', 'extinction_phytoplankton_wq_map_multi_dynamic':'mesh2d_ExtVlPhyt', 'volume_wq_map_dynamic':'mesh2d_2d_volume', 'volume_wq_map_multi_dynamic':'mesh2d_volume',
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
    # Check if all variables are available in the variablesNames dictionary
    if variablesNames not in data.variables: return False
    else: return float(data[variablesNames].min()) != float(data[variablesNames].max())

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
    # This is a general his file
    if ('time' in data.sizes and ('stations' or 'cross_section' or 'source_sink') in data.sizes):
        print("Checking His file for Hydrodynamics Simulation ...")
        # Prepare data for general options
        result['points'] = data.sizes['stations'] > 0 if ('stations' in data.sizes) else False
        result['cross_sections'] = False
        if ('cross_section' in data.sizes and data.sizes['cross_section'] > 0):
            x = np.unique(data['cross_section_geom_node_coordx'].values)
            y = np.unique(data['cross_section_geom_node_coordy'].values)
            if (x.shape[0] > 1 and y.shape[0] > 1 and x != y): result['cross_sections'] = True
        result['sources'] = data.sizes['source_sink'] > 0 if ('source_sink' in data.sizes) else False
        # Prepare data for measured locations
        # 1. Observation points
        # 1.1. Hydrodynamics
        result['global_waterlevel'] = checkVariables(data, 'waterlevel')
        result['global_waterdepth'] = checkVariables(data, 'waterdepth')
        result['global_hydrodynamic'] = True if (result['global_waterlevel'] or result['global_waterdepth']) else False
        # 1.2. Meteorology
        result['global_total_heat_flux'] = checkVariables(data, 'Qtot')
        result['global_precipitation_rate'] = checkVariables(data, 'rain')
        result['global_wind_speed'] = checkVariables(data, 'wind')
        result['global_air_temperature'] = checkVariables(data, 'Tair')
        result['global_relative_humidity'] = checkVariables(data, 'rhum')
        result['global_solar_influx'] = checkVariables(data, 'Qsun')
        result['global_evaporative_heat_flux'] = checkVariables(data, 'Qeva')
        result['global_free_convection_evaporative_heat_flux'] = checkVariables(data, 'Qfreva')
        result['global_sensible_heat_flux'] = checkVariables(data, 'Qcon')
        result['global_free_convection_sensible_heat_flux'] = checkVariables(data, 'Qfrcon')
        result['global_long_wave_back_radiation'] = checkVariables(data, 'Qlong')
        result['global_cloudiness'] = checkVariables(data, 'clou')
        result['global_meteorology'] = True if (result['global_total_heat_flux'] or
            result['global_precipitation_rate'] or result['global_wind_speed'] or
            result['global_air_temperature'] or result['global_relative_humidity'] or
            result['global_solar_influx'] or result['global_evaporative_heat_flux'] or
            result['global_free_convection_evaporative_heat_flux'] or
            result['global_sensible_heat_flux'] or result['global_free_convection_sensible_heat_flux'] or
            result['global_long_wave_back_radiation'] or result['global_cloudiness']) else False
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
        # 4. Global Water balance
        result['global_wb_total_volume'] = checkVariables(data, 'water_balance_total_volume')
        result['global_wb_storage'] = checkVariables(data, 'water_balance_storage')
        result['global_wb_inflow_boundaries'] = checkVariables(data, 'water_balance_boundaries_in')
        result['global_wb_outflow_boundaries'] = checkVariables(data, 'water_balance_boundaries_out')
        result['global_wb_total_boundaries'] = checkVariables(data, 'water_balance_boundaries_total')
        result['global_wb_total_precipitation'] = checkVariables(data, 'water_balance_precipitation_total')
        result['global_wb_total_evaporation'] = checkVariables(data, 'water_balance_evaporation')
        result['global_wb_source_sink'] = checkVariables(data, 'water_balance_source_sink')
        result['global_wb_inflow_groundwater'] = checkVariables(data, 'water_balance_groundwater_in')
        result['global_wb_outflow_groundwater'] = checkVariables(data, 'water_balance_groundwater_out')
        result['global_wb_total_groundwater'] = checkVariables(data, 'water_balance_groundwater_total')
        result['global_wb_ground_precipitation'] = checkVariables(data, 'water_balance_precipitation_on_ground')
        result['global_wb_volume_error'] = checkVariables(data, 'water_balance_volume_error')
        result['global_water_balance'] = True if (result['global_wb_total_volume'] or
            result['global_wb_inflow_boundaries'] or result['global_wb_outflow_boundaries'] or
            result['global_wb_total_boundaries'] or result['global_wb_total_precipitation'] or
            result['global_wb_total_evaporation'] or result['global_wb_source_sink'] or
            result['global_wb_inflow_groundwater'] or result['global_wb_outflow_groundwater'] or
            result['global_wb_total_groundwater'] or result['global_wb_ground_precipitation'] or
            result['global_wb_storage'] or result['global_wb_volume_error']) else False
    # This is a general map file
    elif ('time' in data.sizes and ('mesh2d_nNodes' or 'mesh2d_nEdges') in data.sizes):
        print("Checking Map file for Hydrodynamics Simulation ...")
        # Prepare data for thermocline parameters
        # 1. Thermocline
        result['thermocline'] = checkVariables(data, 'mesh2d_tem1')
        # 2. Spatial dynamic maps
        result['hydrodynamic_waterlevel_dynamic'] = checkVariables(data, 'mesh2d_s1')
        result['hydrodynamic_waterdepth_dynamic'] = checkVariables(data, 'mesh2d_waterdepth')
        result['spatial_hydrodynamic'] = True if (result['hydrodynamic_waterlevel_dynamic'] or
            result['hydrodynamic_waterdepth_dynamic']) else False
        # 3. Spatial physical maps
        result['spatial_salinity'] = checkVariables(data, 'mesh2d_sa1')
        result['spatial_contaminant'] = checkVariables(data, 'mesh2d_Contaminant')
        result['spatial_physical'] = True if (result['thermocline'] or
            result['spatial_salinity'] or result['spatial_contaminant']) else False
        # 4. Spatial static maps
        result['waterdepth_static'] = checkVariables(data, 'mesh2d_waterdepth')
        result['spatial_static'] = True if (result['waterdepth_static']) else False
    # This is a water quality his file
    elif ('nTimesDlwq' in data.sizes and 'nStations' in data.sizes):
        print("Checking His file for Water Quality Simulation ...")
        # Prepare data for Fast Decomposing Fraction
        result['wq_his_fdf_carbon'] = checkVariables(data, 'DetC')
        result['wq_his_fdf_nitrogen'] = checkVariables(data, 'DetN')
        result['wq_his_fdf_phosphate'] = checkVariables(data, 'DetP')
        result['wq_his_fdf'] = True if (result['wq_his_fdf_carbon'] or
            result['wq_his_fdf_nitrogen'] or result['wq_his_fdf_phosphate']) else False
        # Prepare data for Dissolved Form
        result['wq_his_df_ammonium'] = checkVariables(data, 'NH4')
        result['wq_his_df_nitrate'] = checkVariables(data, 'NO3')
        result['wq_his_df_phosphate'] = checkVariables(data, 'PO4')
        result['wq_his_df_oxygen'] = checkVariables(data, 'OXY')
        result['wq_his_df_chloride'] = checkVariables(data, 'Cl')
        result['wq_his_df'] = True if (result['wq_his_df_ammonium'] or
            result['wq_his_df_nitrate'] or result['wq_his_df_phosphate'] or
            result['wq_his_df_oxygen'] or result['wq_his_df_chloride']) else False
        # Prepare data for Nitrogen
        result['wq_his_nitrogen_total'] = checkVariables(data, 'TotN')
        result['wq_his_nitrogen_algae'] = checkVariables(data, 'AlgN')
        result['wq_his_nitrogen_kjeldahl'] = checkVariables(data, 'KjelN')
        result['wq_his_nitrogen'] = True if (result['wq_his_nitrogen_total'] or
            result['wq_his_nitrogen_algae'] or result['wq_his_nitrogen_kjeldahl']) else False
        # Prepare data for Phosphorus
        result['wq_his_phosphorus_total'] = checkVariables(data, 'TotP')
        result['wq_his_phosphorus_algae'] = checkVariables(data, 'AlgP')
        result['wq_his_phosphorus'] = True if (result['wq_his_phosphorus_total'] or
            result['wq_his_phosphorus_algae']) else False
        # Limitation Function for Greens
        result['wq_his_daylength'] = checkVariables(data, 'LimDLGreen')
        result['wq_his_nutrient'] = checkVariables(data, 'LimNutGree')
        result['wq_his_radiation'] = checkVariables(data, 'LimRadGree')
        result['wq_his_greens'] = True if (result['wq_his_daylength'] or
            result['wq_his_nutrient'] or result['wq_his_radiation']) else False
        # Prepare data for other variables
        result['wq_his_aap'] = checkVariables(data, 'AAP')
        result['wq_his_dyamo'] = checkVariables(data, 'GREEN')
        result['wq_his_organic'] = checkVariables(data, 'IM1')
        result['wq_his_opal_si'] = checkVariables(data, 'Opal')
        result['wq_his_sediment'] = checkVariables(data, 'SOD')
        result['wq_his_suspend'] = checkVariables(data, 'SS')
        result['wq_his_chlorophyll'] = checkVariables(data, 'Chlfa')
        result['wq_his_extinction'] = checkVariables(data, 'ExtVlPhyt')
        result['wq_his'] = True if (result['wq_his_fdf'] or result['wq_his_df'] or
            result['wq_his_nitrogen'] or result['wq_his_phosphorus'] or result['wq_his_greens'] or
            result['wq_his_aap'] or result['wq_his_dyamo'] or result['wq_his_organic'] or 
            result['wq_his_opal_si'] or result['wq_his_sediment'] or result['wq_his_suspend'] or
            result['wq_his_chlorophyll'] or result['wq_his_extinction']) else False
    # This is a water quality map file      
    elif ('nTimesDlwq' in data.sizes and ('mesh2d_nNodes' or 'mesh2d_nEdges') in data.sizes):
        print('Checking Map file for Water Quality Simulation ...')
        # Prepare data for Fast Decomposing Fraction
        result['wq_map_fdf_carbon'] = (checkVariables(data, 'mesh2d_DetC') or checkVariables(data, 'mesh2d_2d_DetC'))
        result['wq_map_fdf_nitrogen'] = (checkVariables(data, 'mesh2d_DetN') or checkVariables(data, 'mesh2d_2d_DetN'))
        result['wq_map_fdf_phosphate'] = (checkVariables(data, 'mesh2d_DetP') or checkVariables(data, 'mesh2d_2d_DetP'))
        result['wq_map_fdf'] = True if (result['wq_map_fdf_carbon'] or result['wq_map_fdf_nitrogen'] or result['wq_map_fdf_phosphate']) else False
        # Prepare data for Dissolved Form
        result['wq_map_ammonium'] = (checkVariables(data, 'mesh2d_NH4') or checkVariables(data, 'mesh2d_2d_NH4'))
        result['wq_map_nitrate'] = (checkVariables(data, 'mesh2d_NO3') or checkVariables(data, 'mesh2d_2d_NO3'))
        result['wq_map_phosphate'] = (checkVariables(data, 'mesh2d_PO4') or checkVariables(data, 'mesh2d_2d_PO4'))
        result['wq_map_oxygen'] = (checkVariables(data, 'mesh2d_OXY') or checkVariables(data, 'mesh2d_2d_OXY'))
        result['wq_map_chloride'] = (checkVariables(data, 'mesh2d_Cl') or checkVariables(data, 'mesh2d_2d_Cl'))
        result['wq_map_df'] = True if (result['wq_map_ammonium'] or result['wq_map_nitrate'] or result['wq_map_phosphate'] or
            result['wq_map_oxygen'] or result['wq_map_chloride']) else False
        # Prepare data for Nitrogen
        result['wq_map_nitrogen_total'] = (checkVariables(data, 'mesh2d_TotN') or checkVariables(data, 'mesh2d_2d_TotN'))
        result['wq_map_nitrogen_algae'] = (checkVariables(data, 'mesh2d_AlgN') or checkVariables(data, 'mesh2d_2d_AlgN'))
        result['wq_map_nitrogen_kjeldahl'] = (checkVariables(data, 'mesh2d_Cl') or checkVariables(data, 'mesh2d_2d_Cl'))
        result['wq_map_nitrogen'] = True if (result['wq_map_nitrogen_total'] or
            result['wq_map_nitrogen_algae'] or result['wq_map_nitrogen_kjeldahl']) else False
        # Prepare data for Phosphorus
        result['wq_map_phosphorus_total'] = (checkVariables(data, 'mesh2d_TotP') or checkVariables(data, 'mesh2d_2d_TotP'))
        result['wq_map_phosphorus_algae'] = (checkVariables(data, 'mesh2d_AlgP') or checkVariables(data, 'mesh2d_2d_AlgP'))
        result['wq_map_phosphorus'] = True if (result['wq_map_phosphorus_total'] or result['wq_map_phosphorus_algae']) else False
        # Limitation Function for Greens
        result['wq_map_daylength'] = (checkVariables(data, 'mesh2d_LimDLGreen') or checkVariables(data, 'mesh2d_2d_LimDLGreen'))
        result['wq_map_nutrient'] = (checkVariables(data, 'mesh2d_LimNutGree') or checkVariables(data, 'mesh2d_2d_LimNutGree'))
        result['wq_map_radiation'] = (checkVariables(data, 'mesh2d_LimRadGree') or checkVariables(data, 'mesh2d_2d_LimRadGree'))
        result['wq_map_greens'] = True if (result['wq_map_daylength'] or result['wq_map_nutrient'] or result['wq_map_radiation']) else False
        # Prepare data for other variables
        result['wq_map_aap'] = (checkVariables(data, 'mesh2d_AAP') or checkVariables(data, 'mesh2d_2d_AAP'))
        result['wq_map_dyamo'] = (checkVariables(data, 'mesh2d_GREEN') or checkVariables(data, 'mesh2d_2d_GREEN'))
        result['wq_map_organic'] = (checkVariables(data, 'mesh2d_IM1') or checkVariables(data, 'mesh2d_2d_IM1'))
        result['wq_map_opal_si'] = (checkVariables(data, 'mesh2d_Opal') or checkVariables(data, 'mesh2d_2d_Opal'))
        result['wq_map_sediment'] = (checkVariables(data, 'mesh2d_SOD') or checkVariables(data, 'mesh2d_2d_SOD'))
        result['wq_map_suspend'] = (checkVariables(data, 'mesh2d_SS') or checkVariables(data, 'mesh2d_2d_SS'))
        result['wq_map_chlorophyll'] = (checkVariables(data, 'mesh2d_Chlfa') or checkVariables(data, 'mesh2d_2d_Chlfa'))
        result['wq_map_extinction'] = (checkVariables(data, 'mesh2d_ExtVlPhyt') or checkVariables(data, 'mesh2d_2d_ExtVlPhyt'))
        result['wq_map_volume'] = (checkVariables(data, 'mesh2d_volume') or checkVariables(data, 'mesh2d_2d_volume'))
        result['wq_map'] = True if (result['wq_map_fdf'] or result['wq_map_df'] or
            result['wq_map_nitrogen'] or result['wq_map_phosphorus'] or result['wq_map_greens'] or
            result['wq_map_aap'] or result['wq_map_dyamo'] or result['wq_map_organic'] or 
            result['wq_map_opal_si'] or result['wq_map_sediment'] or result['wq_map_suspend'] or
            result['wq_map_chlorophyll'] or result['wq_map_extinction'] or result['wq_map_volume']) else False
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

def getSummary(dialog_path: str, data_his: xr.Dataset, data_wq_map: xr.Dataset) -> list:
    """
    Get the summary of the dataset received from *.nc file.

    Parameters:
    ----------
    dialog_path: str
        The path of the dialog *.dia file.
    data_his: xr.Dataset
        The dataset received from_his.nc file.
    data_wq_map: xr.Dataset
        The dataset received from _map.nc file for water quality.

    Returns:
    -------
    list
        The list containing the summary of the dataset.
    """
    dialog, result = dialogReader(dialog_path), []
    if (data_his is not None):
        result.append({'parameter': 'Start Date (Hydrodynamic Simulation)', 'value': pd.to_datetime(data_his['time'].values[0]).strftime('%Y-%m-%d %H:%M:%S')})
        result.append({'parameter': 'End Date (Hydrodynamic Simulation)', 'value': pd.to_datetime(data_his['time'].values[-1]).strftime('%Y-%m-%d %H:%M:%S')})
        result.append({'parameter': 'Number of Layers', 'value': data_his.sizes['laydim']})
        result.append({'parameter': 'Number of Time Steps', 'value': data_his.sizes['time']})
    if len(dialog) > 0:
        result.append({'parameter': 'Computation started', 'value': dialog['computation_start']})
        result.append({'parameter': 'Computation finished', 'value': dialog['computation_finish']})
        result.append({'parameter': 'Area (m2)', 'value': dialog['area']})
        result.append({'parameter': 'Volume (m3)', 'value': dialog['volume']})
    if (data_wq_map is not None):
        result.append({'parameter': 'Start Date (Water Quality Simulation)', 'value': pd.to_datetime(data_wq_map['nTimesDlwq'].values[0]).strftime('%Y-%m-%d %H:%M:%S')})
        result.append({'parameter': 'End Date (Water Quality Simulation)', 'value': pd.to_datetime(data_wq_map['nTimesDlwq'].values[-1]).strftime('%Y-%m-%d %H:%M:%S')})
        result.append({'parameter': 'Modified Date (Water Quality Simulation)', 'value': pd.to_datetime(parser.parse(data_wq_map.date_modified.replace(':0.', '.'))).strftime('%Y-%m-%d %H:%M:%S')})
        result.append({'parameter': 'Number of Sigma Layers', 'value': len(data_wq_map['mesh2d_layer_dlwq'].values)})
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
        The dataset received from _his.nc file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame converted to WGS84.
    """
    # Check coordinate reference system
    if 'wgs84' in data_his.variables:
        crs_code = data_his['wgs84'].attrs['EPSG_code']
        result = gpd.GeoDataFrame(data={'name': name, 'geometry': geometry}, crs=crs_code)
    else:
        crs_code = data_his['projected_coordinate_system'].attrs['EPSG_code']
        result = gpd.GeoDataFrame(data={'name': name, 'geometry': geometry}, crs=crs_code)
        result = result.to_crs(epsg=4326)  # Convert to WGS84 if not already
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
    names = [name.decode('utf-8').strip() for name in data_his['station_name'].values]
    geometry = gpd.points_from_xy(data_his['station_x_coordinate'].values, data_his['station_y_coordinate'].values)
    return checkCoordinateReferenceSystem(names, geometry, data_his)

def sourceCreator(data_his: xr.Dataset) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of sources/sinks.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his.nc file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of sources/sinks.
    """
    names = [name.decode('utf-8').strip() for name in data_his['source_sink_name'].values]
    geometry = gpd.points_from_xy(data_his['source_sink_x_coordinate'].values[0], data_his['source_sink_y_coordinate'].values[0])
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

def crosssectionCreator(data_his: xr.Dataset) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of cross-section.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his.nc file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of cross-sections.
    """
    names = [name.decode('utf-8').strip() for name in data_his['cross_section_name'].values]
    x = data_his['cross_section_geom_node_coordx'].values
    y = data_his['cross_section_geom_node_coordy'].values
    p1, p2 = linearCreator(x, y)
    geometry = gpd.GeoSeries([shapely.geometry.LineString([p1, p2])])
    return checkCoordinateReferenceSystem(names, geometry, data_his)

def selectInsitu(data_his: xr.Dataset, data_map: xr.Dataset, name: str, station: str, type: str) -> pd.DataFrame:
    """
    Get insitu data.

    Parameters:
    ----------
    data_his: xr.Dataset
        The dataset received from _his.nc file.
    data_map: xr.Dataset
        The dataset received from _map.nc file.
    name: str
        The name of defined variable in _his.nc file.
    station: str
        The name of the station.
    type: str
        The type of data, accepted values are: 'station_name' or 'source_sink_name'.

    Returns:
    -------
    pd.DataFrame
        A DataFrame containing the insitu data.
    """
    names = [x.decode('utf-8').strip() for x in data_his[type].values]
    if station not in names: return pd.DataFrame()
    idx = names.index(station)
    index = [pd.to_datetime(id).strftime('%Y-%m-%d %H:%M:%S') for id in data_his['time'].values]
    if type == 'station_name':
        result = pd.DataFrame(index=index)
        z_layer = numberFormatter(data_map['mesh2d_layer_z'].values)
        arr = data_his[variablesNames[name]].values[:, idx, :]
        for i in range(arr.shape[1]):
            i_rev = -(i+1)
            arr_rev = numberFormatter(arr[:, i_rev])
            result[f'Depth: {z_layer[i_rev]} m'] = arr_rev
    else:
        temp = pd.DataFrame(data_his[variablesNames[name]].values, columns=names, index=index)
        result = temp[[station]]
    result = result.reset_index()
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
    index_ = numberFormatter(data_map['mesh2d_layer_z'].values)
    times = data_map['time'].values
    columns, data_list = [], []
    for i in range(len(times)):
        col_name = pd.to_datetime(times[i]).strftime('%Y-%m-%d %H:%M:%S')
        value = np.nanmean(data_map['mesh2d_tem1'].values[i,:,:], axis=0)
        columns.append(col_name)
        data_list.append(numberFormatter(value))
    df = pd.DataFrame(np.column_stack(data_list), index=index_, columns=columns).reset_index()
    return df

def timeseriesCreator(data_his: xr.Dataset, key: str) -> pd.DataFrame:
    """
    Create a GeoDataFrame of timeseries.

    Parameters:
    ----------
    ds_his: xr.Dataset
        The dataset received from _his.nc file.
    key: str
        The key of the timeseries, used to define the name of the variable.
    columns: list
        The columns of the timeseries.

    Returns:
    -------
    pd.DataFrame
        The DataFrame of timeseries.
    """
    timeColumn = 'nTimesDlwq' if key.endswith('_wq') else 'time'
    name = 'source_sink_name' if key.endswith('_source') else 'station_name'
    columns = [i.decode('utf-8').strip() for i in data_his[name].values]
    if key.startswith('wb_'): columns = ['Water balance'] # Used for water balance
    elif key.endswith('_crs'): columns = ['Cross-section'] # Used for cross-section
    if name in data_his.variables.keys():
        temp = variablesNames[key] if key in variablesNames.keys() else key
        index = [pd.to_datetime(i).strftime('%Y-%m-%d %H:%M:%S') for i in data_his[timeColumn].values]
        timeseries = pd.DataFrame(index=index, data=numberFormatter(data_his[temp].values), columns=columns).reset_index()
        return timeseries
    else: return pd.DataFrame()

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
    # Check coordinate reference system
    if 'wgs84' in data_map.variables:
        crs_code = data_map['wgs84'].attrs['EPSG_code']
        grid = gpd.GeoDataFrame(geometry=polygons, crs=crs_code)
    else:
        crs_code = data_map['projected_coordinate_system'].attrs['EPSG_code']
        grid = gpd.GeoDataFrame(geometry=polygons, crs=crs_code)
        grid = grid.to_crs(epsg=4326)  # Convert to WGS84 if not already
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
    return numberFormatter(value)

def assignValuesToMeshes(grid: gpd.GeoDataFrame, data_map: xr.Dataset, key: str, time_column: str) -> gpd.GeoDataFrame:
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
    # Convert to numpy array
    arr = numberFormatter(result.to_numpy())
    # Convert to dataframe
    result = pd.DataFrame(arr, index=result.index, columns=result.columns)
    result = temp_grid.join(result)    
    return result.reset_index()

def selectPolygon(data_map: xr.Dataset, idx: int, key:str, time_column: str, column_layer: str) -> dict:
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
        arr_rev = arr[:, i_rev]
        result[f'Layer: {z_layer[i_rev]:.2f} {kt}'] = arr_rev
    result = result.replace(-999.0, np.nan)
    # Convert to numpy array
    arr = numberFormatter(result.to_numpy())
    # Convert to dataframe
    result = pd.DataFrame(arr, index=result.index, columns=result.columns)
    return result.reset_index()

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
        layers[-1] = 'Average'
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
        The type of velocity to compute: 'Depth-average' or one specific layer.
    key: int
        The index of the selected layer.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame containing the vector map of the mesh.
    """
    result = {}
    if value_type == 'Average':
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

def fileWriter(template_path=str, params=dict) -> str:
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
        if "#" in line and not line.strip().startswith("#"):
            left, right = line.split("#", 1)
            left, middle = left.split("=", 1)
            lines.append((left + " = ", middle.strip(), "# " + right.strip()))
        else: lines.append((line.strip(), "", ""))
    max_len = max(len(middle) for _, middle, _ in lines) + 1
    for left, middle, right in lines:
        result.append(left + middle.ljust(max_len) + right)
    result = "\n".join(result)
    return result

def contentWriter(project_name: str, filename: str, data: list, content: str, ref_time: int, unit: str='sec') -> tuple:
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
        seconds = ref_time/1000.0
        t_ref = datetime.fromtimestamp(seconds, tz=timezone.utc)
        # Write weather.tim file
        with open(os.path.join(path, filename), 'w') as f:
            for row in data:
                t = datetime.fromtimestamp(int(row[0])/1000.0, tz=timezone.utc)
                dif = t - t_ref
                if unit == 'sec': row[0] = int(dif.total_seconds())
                elif unit == 'min': row[0] = int(dif.total_seconds() / 60)
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
    None
    """
    parent_path = os.path.dirname(directory)
    output_path = os.path.join(parent_path, 'output')
    # Create the directory output
    if os.path.exists(output_path): shutil.rmtree(output_path, onexc=remove_readonly)
    os.makedirs(output_path, exist_ok=True)
    subdirs = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
    if len(subdirs) == 0: return {'status': 'error', 'message': 'No output directory for simulations found.'}
    
    # # Copy folder DFM_DELWAQ to the parent directory
    # DFM_DELWAQ_path = os.path.join(parent_path, 'DFM_DELWAQ')
    # if os.path.exists(DFM_DELWAQ_path): shutil.rmtree(DFM_DELWAQ_path, onexc=remove_readonly)
    # try: shutil.copytree(os.path.join(directory, 'DFM_DELWAQ'), DFM_DELWAQ_path)
    # except Exception as e: return {'status': 'error', 'message': {str(e)}}
    # # Delete folder DFM_DELWAQ
    # try: shutil.rmtree(os.path.join(directory, 'DFM_DELWAQ'), onexc=remove_readonly)
    # except Exception as e: return {'status': 'error', 'message': {str(e)}}

    # Copy files to the directory output
    try:
        # Copy files to the directory output
        DFM_OUTPUT_path = os.path.join(directory, 'DFM_OUTPUT')
        select_files = ['FlowFM.dia', 'FlowFM_his.nc', 'FlowFM_map.nc']
        files = [f for f in os.listdir(DFM_OUTPUT_path) if (os.path.isfile(os.path.join(DFM_OUTPUT_path, f)) and f in select_files)]
        if len(files) <= 1: return {'status': 'error', 'message': 'No *.nc files found.'}
        for f in files:
            shutil.copy(os.path.join(DFM_OUTPUT_path, f), output_path)
        # Delete folder DFM_OUTPUT
        shutil.rmtree(DFM_OUTPUT_path, onexc=remove_readonly)
    except Exception as e: return {'status': 'error', 'message': {str(e)}}
    # Delete files in folder common_files
    common_path = os.path.join(parent_path, 'common_files')
    if os.path.exists(common_path): shutil.rmtree(common_path, onexc=remove_readonly)
    os.makedirs(common_path, exist_ok=True)
    return {'status': 'ok', 'message': 'Data is saved successfully.'}