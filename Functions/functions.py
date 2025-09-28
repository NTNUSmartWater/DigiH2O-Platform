import shapely, os, re, shutil, stat
import geopandas as gpd, pandas as pd
import numpy as np, xarray as xr
from scipy.spatial import cKDTree
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
    # For Dynamic map: Hydrodynamics
    'wl_dynamic':'mesh2d_s1', 'wd_dynamic':'mesh2d_waterdepth',
    # For Dynamic map: Physical options
    'temp_multi_dynamic':'mesh2d_tem1', 'sal_multi_dynamic':'mesh2d_sa1', 'cont_multi_dynamic':'mesh2d_Contaminant',
    
    # # For Water quality options at point
    # 'fdf_POC_wq':'DetC', 'fdf_PON_wq':'DetN', 'fdf_POP_wq':'DetP', 'df_NH4_wq':'NH4', 'df_NO3_wq':'NO3', 'df_PO4_wq':'PO4',
    # 'df_DO_wq':'OXY', 'df_Chl_wq':'Cl', 'nitrogen_total_wq':'TotN', 'nitrogen_algae_wq':'AlgN', 'nitrogen_kjeldahl_wq':'KjelN',
    # 'phosphorus_total_wq':'TotP', 'phosphorus_algae_wq': 'AlgP', 'daylength_greens_wq':'LimDLGreen', 'nutrient_greens_wq':'LimNutGree',
    # 'radiation_greens_wq':'LimRadGree', 'inorganic_matter_wq':'IM1', 'opal_si_wq':'Opal', 'sediment_oxygen_wq':'SOD', 'suspended_solids_wq':'SS',
    # 'chlorophyll_wq':'Chlfa', 'extinction_phytoplankton_wq':'ExtVlPhyt', 'adsorbed_ortho_phosphate_wq':'AAP', 'dyamo_wq':'GREEN',
    # # For Dynamic map: Water Quality options
    # 'fdf_POC_wq_map_dynamic':'mesh2d_2d_DetC', 'fdf_POC_wq_map_multi_dynamic':'mesh2d_DetC', 'fdf_PON_wq_map_dynamic':'mesh2d_2d_DetN', 'fdf_PON_wq_map_multi_dynamic':'mesh2d_DetN',
    # 'fdf_POP_wq_map_dynamic':'mesh2d_2d_DetP', 'fdf_POP_wq_map_multi_dynamic':'mesh2d_DetP', 'df_NH4_wq_map_dynamic':'mesh2d_2d_NH4', 'df_NH4_wq_map_multi_dynamic':'mesh2d_NH4',
    # 'df_NO3_wq_map_dynamic':'mesh2d_2d_NO3', 'df_NO3_wq_map_multi_dynamic':'mesh2d_NO3', 'df_PO4_wq_map_dynamic':'mesh2d_2d_PO4', 'df_PO4_wq_map_multi_dynamic':'mesh2d_PO4',
    # 'fdf_OXY_wq_map_dynamic':'mesh2d_2d_OXY', 'fdf_OXY_wq_map_multi_dynamic':'mesh2d_OXY', 'fdf_OXY_wq_map_dynamic':'mesh2d_2d_Cl', 'fdf_OXY_wq_map_multi_dynamic':'mesh2d_Cl',
    # 'nitrogen_total_wq_map_dynamic':'mesh2d_2d_TotN', 'nitrogen_total_wq_map_multi_dynamic':'mesh2d_TotN', 'nitrogen_total_wq_map_dynamic':'mesh2d_2d_AlgN',
    # 'nitrogen_total_wq_map_multi_dynamic':'mesh2d_AlgN', 'nitrogen_kjeldahl_wq_map_dynamic':'mesh2d_2d_KjelN', 'nitrogen_kjeldahl_wq_map_multi_dynamic':'mesh2d_KjelN',
    # 'nitrogen_kjeldahl_wq_map_dynamic':'mesh2d_2d_KjelN', 'nitrogen_kjeldahl_wq_map_multi_dynamic':'mesh2d_KjelN', 'total_phosphorus_wq_map_dynamic':'mesh2d_2d_TotP',
    # 'total_phosphorus_wq_map_multi_dynamic':'mesh2d_TotP', 'phosphorus_algae_wq_map_dynamic':'mesh2d_2d_AlgP', 'phosphorus_algae_wq_map_multi_dynamic':'mesh2d_AlgP',
    # 'daylength_greens_wq_map_dynamic':'mesh2d_2d_LimDLGreen', 'daylength_greens_wq_map_multi_dynamic':'mesh2d_LimDLGreen',
    # 'nutrient_greens_wq_map_dynamic':'mesh2d_2d_LimNutGree', 'nutrient_greens_wq_map_multi_dynamic':'mesh2d_LimNutGree',
    # 'radiation_greens_wq_map_dynamic':'mesh2d_2d_LimRadGree', 'radiation_greens_wq_map_multi_dynamic':'mesh2d_LimRadGree',
    # 'adsorbed_ortho_phosphate_wq_map_dynamic':'mesh2d_2d_AAP', 'adsorbed_ortho_phosphate_wq_map_multi_dynamic':'mesh2d_AAP',
    # 'dyamo_wq_map_dynamic':'mesh2d_2d_GREEN', 'dyamo_wq_map_multi_dynamic':'mesh2d_GREEN', 'inorganic_matter_wq_map_dynamic':'mesh2d_2d_IM1', 'inorganic_matter_wq_map_multi_dynamic':'mesh2d_IM1',
    # 'opal_si_wq_map_dynamic':'mesh2d_2d_Opal', 'opal_si_wq_map_multi_dynamic':'mesh2d_Opal', 'sediment_oxygen_wq_map_dynamic':'mesh2d_2d_SOD', 'sediment_oxygen_wq_map_multi_dynamic':'mesh2d_SOD',
    # 'suspended_solids_wq_map_dynamic':'mesh2d_2d_SS', 'suspended_solids_wq_map_multi_dynamic':'mesh2d_SS', 'chlorophyll_wq_map_dynamic':'mesh2d_2d_Chlfa', 'chlorophyll_wq_map_multi_dynamic':'mesh2d_Chlfa',
    # 'extinction_phytoplankton_wq_map_dynamic':'mesh2d_2d_ExtVlPhyt', 'extinction_phytoplankton_wq_map_multi_dynamic':'mesh2d_ExtVlPhyt', 'volume_wq_map_dynamic':'mesh2d_2d_volume', 'volume_wq_map_multi_dynamic':'mesh2d_volume',
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

def getVariablesNames(path_NC: list) -> dict:
    """
    Get the names of the variables in the dataset received from *.nc file.

    Parameters:
    ----------
    path_NC: list
        The list of path of the *.nc files.

    Returns:
    -------
    dict
        The dictionary containing the names of the variables.
    """
    result = {}
    for path in path_NC:
        if path is None or not os.path.exists(path): continue
        data = xr.open_dataset(path)
        # This is a hydrodynamic his file
        if ('time' in data.sizes and ('stations' or 'cross_section' or 'source_sink') in data.sizes):
            print(f"File: {os.path.basename(path)} - Checking Hydrodynamic Simulation ...")
            # Prepare data for hydrodynamic options
            result['hyd_obs'] = data.sizes['stations'] > 0 if ('stations' in data.sizes) else False
            result['cross_sections'] = False
            if 'cross_section' in data.sizes and data.sizes['cross_section'] > 0:
                x = np.unique(data['cross_section_geom_node_coordx'].values)
                y = np.unique(data['cross_section_geom_node_coordy'].values)
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
        elif ('time' in data.sizes and ('mesh2d_nNodes' or 'mesh2d_nEdges') in data.sizes):
            print(f"File: {os.path.basename(path)} - Checking Hydrodynamics Simulation ...")
            # Prepare data for thermocline parameters
            # 1. Thermocline
            result['thermocline'] = checkVariables(data, 'mesh2d_tem1')
            # 2. Spatial dynamic maps
            result['hyd_wl_dynamic'] = checkVariables(data, 'mesh2d_s1')
            result['hyd_wd_dynamic'] = checkVariables(data, 'mesh2d_waterdepth')
            result['single_layer'] = True if (result['hyd_wl_dynamic'] or result['hyd_wd_dynamic']) else False
            # 3. Spatial physical maps
            result['spatial_salinity'] = checkVariables(data, 'mesh2d_sa1')
            result['spatial_contaminant'] = checkVariables(data, 'mesh2d_Contaminant')
            result['multi_layer'] = True if (result['thermocline'] or
                result['spatial_salinity'] or result['spatial_contaminant']) else False
            result['hyd_spatial'] = True if (result['single_layer'] or result['multi_layer']) else False
            # 4. Spatial static maps
            result['waterdepth_static'] = checkVariables(data, 'mesh2d_waterdepth')
            result['spatial_static'] = True if (result['waterdepth_static']) else False
        # This is a water quality his file
        elif ('nTimesDlwq' in data.sizes and not ('mesh2d_nNodes' or 'mesh2d_nEdges') in data.sizes):
            print(f"File: {os.path.basename(path)} - Checking Water Quality Simulation ...")
            # Prepare data for Physical option
            # 1. Conservative and Decaying Tracers
            result['waq_his_conservative_selector'] = []
            result['waq_his_conservative_1'] = checkVariables(data, 'cTR1')
            if result['waq_his_conservative_1']: result['waq_his_conservative_selector'].append('cTR1 (g/m³)')
            result['waq_his_conservative_2'] = checkVariables(data, 'cTR2')
            if result['waq_his_conservative_2']: result['waq_his_conservative_selector'].append('cTR2 (g/m³)')
            result['waq_his_conservative_3'] = checkVariables(data, 'cTR3')
            if result['waq_his_conservative_3']: result['waq_his_conservative_selector'].append('cTR3 (g/m³)')
            result['waq_his_decay_1'] = checkVariables(data, 'dTR1')
            if result['waq_his_decay_1']: result['waq_his_conservative_selector'].append('dTR1 (g/m³)')
            result['waq_his_decay_2'] = checkVariables(data, 'dTR2')
            if result['waq_his_decay_2']: result['waq_his_conservative_selector'].append('dTR2 (g/m³)')
            result['waq_his_decay_3'] = checkVariables(data, 'dTR3')
            if result['waq_his_decay_3']: result['waq_his_conservative_selector'].append('dTR3 (g/m³)')
            result['waq_his_conservative_decay'] = True if (result['waq_his_conservative_1'] or result['waq_his_conservative_2'] or
                result['waq_his_conservative_3'] or result['waq_his_decay_1'] or result['waq_his_decay_2'] or result['waq_his_decay_3']) else False
            # 2. Suspended Sediment
            result['waq_his_suspended_sediment_selector'] = []
            result['waq_his_physical_inorganic_1'] = checkVariables(data, 'IM1')
            if result['waq_his_physical_inorganic_1']: result['waq_his_suspended_sediment_selector'].append('IM1 (g/m³)')
            result['waq_his_physical_inorganic_2'] = checkVariables(data, 'IM2')
            if result['waq_his_physical_inorganic_2']: result['waq_his_suspended_sediment_selector'].append('IM2 (g/m³)')
            result['waq_his_physical_inorganic_3'] = checkVariables(data, 'IM3')
            if result['waq_his_physical_inorganic_3']: result['waq_his_suspended_sediment_selector'].append('IM3 (g/m³)')
            result['waq_his_physical_inorganic_s1'] = checkVariables(data, 'IM1S1')
            if result['waq_his_physical_inorganic_s1']: result['waq_his_suspended_sediment_selector'].append('IM1S1 (g/m³)')
            result['waq_his_physical_inorganic_s2'] = checkVariables(data, 'IM2S1')
            if result['waq_his_physical_inorganic_s2']: result['waq_his_suspended_sediment_selector'].append('IM2S1 (g/m³)')
            result['waq_his_physical_inorganic_s3'] = checkVariables(data, 'IM3S1')
            if result['waq_his_physical_inorganic_s3']: result['waq_his_suspended_sediment_selector'].append('IM3S1 (g/m³)')
            result['waq_his_suspended_sediment'] = True if (result['waq_his_physical_inorganic_1'] or result['waq_his_physical_inorganic_2'] or
                result['waq_his_physical_inorganic_3'] or result['waq_his_physical_inorganic_s1'] or result['waq_his_physical_inorganic_s2'] or
                result['waq_his_physical_inorganic_s3']) else False
            result['waq_his_physical'] = True if (result['waq_his_conservative_decay'] or result['waq_his_suspended_sediment']) else False
            # Prepare data for Chemical option
            # 1. Simple Oxygen or Oxygen and BOD (water phase only)
            result['waq_his_simple_oxygen_selector'] = []
            result['waq_his_chemical_ammonium'] = checkVariables(data, 'NH4')
            if result['waq_his_chemical_ammonium']: result['waq_his_simple_oxygen_selector'].append('NH4 (g/m³)')
            result['wq_his_chemical_carbonaceous'] = checkVariables(data, 'CBOD5')
            if result['wq_his_chemical_carbonaceous']: result['waq_his_simple_oxygen_selector'].append('CBOD5 (g/m³)')
            result['wq_his_chemical_oxygen'] = checkVariables(data, 'OXY')
            if result['wq_his_chemical_oxygen']: result['waq_his_simple_oxygen_selector'].append('OXY (g/m³)')
            result['wq_his_chemical_sediment_oxygen'] = checkVariables(data, 'SOD')
            if result['wq_his_chemical_sediment_oxygen']: result['waq_his_simple_oxygen_selector'].append('SOD (g/m²)')
            result['wq_his_chemical_dfoxygen_concentration'] = checkVariables(data, 'DO')
            if result['wq_his_chemical_dfoxygen_concentration']: result['waq_his_simple_oxygen_selector'].append('DO (g/m³)')
            result['waq_his_simple_oxygen'] = True if (result['waq_his_chemical_ammonium'] or 
                result['wq_his_chemical_carbonaceous'] or result['wq_his_chemical_oxygen'] or 
                result['wq_his_chemical_sediment_oxygen'] or result['wq_his_chemical_dfoxygen_concentration']) else False
            # 2. Cadmium
            result['waq_his_cadmium_selector'] = []
            if result['waq_his_physical_inorganic_1']: result['waq_his_cadmium_selector'].append('IM1 (g/m³)')
            result['waq_his_chemical_cadmium'] = checkVariables(data, 'Cd')
            if result['waq_his_chemical_cadmium']: result['waq_his_cadmium_selector'].append('Cd (mg/m³)')
            if result['waq_his_physical_inorganic_s1']: result['waq_his_cadmium_selector'].append('IM1S1 (g/m³)')
            result['waq_his_chemical_cadmium_s1'] = checkVariables(data, 'CdS1')
            if result['waq_his_chemical_cadmium_s1']: result['waq_his_cadmium_selector'].append('CdS1 (mg/m³)')
            result['waq_his_cadmium'] = True if (result['waq_his_physical_inorganic_1'] or result['waq_his_chemical_cadmium'] or
                result['waq_his_physical_inorganic_s1'] or result['waq_his_chemical_cadmium_s1']) else False
            # 3. Eutrophication
            result['waq_his_eutrophication_selector'] = []
            if result['waq_his_chemical_ammonium']: result['waq_his_eutrophication_selector'].append('NH4 (g/m³)')
            result['waq_his_chemical_algenconcentration'] = checkVariables(data, 'A')
            if result['waq_his_chemical_algenconcentration']: result['waq_his_eutrophication_selector'].append('A (g/m³)')
            result['waq_his_chemical_orthop_concentration'] = checkVariables(data, 'DP')
            if result['waq_his_chemical_orthop_concentration']: result['waq_his_eutrophication_selector'].append('DP (g/m³)')
            result['waq_his_chemical_particular_p_concentration'] = checkVariables(data, 'PP')
            if result['waq_his_chemical_particular_p_concentration']: result['waq_his_eutrophication_selector'].append('PP (g/m³)')
            result['waq_his_chemical_organic_n_concentration'] = checkVariables(data, 'NORG')
            if result['waq_his_chemical_organic_n_concentration']: result['waq_his_eutrophication_selector'].append('NORG (g/m³)')
            result['waq_his_chemical_nitrate_n_concentration'] = checkVariables(data, 'NO3')
            if result['waq_his_chemical_nitrate_n_concentration']: result['waq_his_eutrophication_selector'].append('NO3 (g/m³)')
            result['waq_his_eutrophication'] = True if (result['waq_his_chemical_ammonium'] or result['waq_his_chemical_algenconcentration'] or
                result['waq_his_chemical_orthop_concentration'] or result['waq_his_chemical_particular_p_concentration'] or
                result['waq_his_chemical_organic_n_concentration'] or result['waq_his_chemical_nitrate_n_concentration']) else False
            # 4. Trace Metals
            result['waq_his_trace_metals_selector'] = []
            result['waq_his_chemical_arseen_total'] = checkVariables(data, 'ASWTOT')
            if result['waq_his_chemical_arseen_total']: result['waq_his_trace_metals_selector'].append('ASWTOT (mg/m³)')
            result['waq_his_chemical_koper_total'] = checkVariables(data, 'CUWTOT')
            if result['waq_his_chemical_koper_total']: result['waq_his_trace_metals_selector'].append('CUWTOT (mg/m³)')
            result['waq_his_chemical_nikkel_total'] = checkVariables(data, 'NIWTOT')
            if result['waq_his_chemical_nikkel_total']: result['waq_his_trace_metals_selector'].append('NIWTOT (mg/m³)')
            result['waq_his_chemical_lood_total'] = checkVariables(data, 'PBWTOT')
            if result['waq_his_chemical_lood_total']: result['waq_his_trace_metals_selector'].append('PBWTOT (mg/m³)')
            result['waq_his_chemical_poc_water'] = checkVariables(data, 'POCW')
            if result['waq_his_chemical_poc_water']: result['waq_his_trace_metals_selector'].append('POCW (g/m³)')
            result['waq_his_chemical_alkel_koolstof'] = checkVariables(data, 'AOCW')
            if result['waq_his_chemical_alkel_koolstof']: result['waq_his_trace_metals_selector'].append('AOCW (g/m³)')
            result['waq_his_chemical_opgelost'] = checkVariables(data, 'DOCW')
            if result['waq_his_chemical_opgelost']: result['waq_his_trace_metals_selector'].append('DOCW (g/m³)')
            result['waq_his_chemical_zwevende'] = checkVariables(data, 'SSW')
            if result['waq_his_chemical_zwevende']: result['waq_his_trace_metals_selector'].append('SSW (g/m³)')
            result['waq_his_chemical_zind_total'] = checkVariables(data, 'ZNWTOT')
            if result['waq_his_chemical_zind_total']: result['waq_his_trace_metals_selector'].append('ZNWTOT (mg/m³)')
            result['waq_his_chemical_arseen_gededuceer'] = checkVariables(data, 'ASREDT')
            if result['waq_his_chemical_arseen_gededuceer']: result['waq_his_trace_metals_selector'].append('ASREDT (mg/m³)')
            result['waq_his_chemical_arseen_aerobe'] = checkVariables(data, 'ASSTOT')
            if result['waq_his_chemical_arseen_aerobe']: result['waq_his_trace_metals_selector'].append('ASSTOT (mg/m³)')
            result['waq_his_chemical_arseen_onderlaag'] = checkVariables(data, 'ASSUBT')
            if result['waq_his_chemical_arseen_onderlaag']: result['waq_his_trace_metals_selector'].append('ASSUBT (mg/m³)')
            result['waq_his_chemical_koper_gededuceer'] = checkVariables(data, 'CUREDT')
            if result['waq_his_chemical_koper_gededuceer']: result['waq_his_trace_metals_selector'].append('CUREDT (mg/m³)')
            result['waq_his_chemical_koper_aerobe'] = checkVariables(data, 'CUSTOT')
            if result['waq_his_chemical_koper_aerobe']: result['waq_his_trace_metals_selector'].append('CUSTOT (mg/m³)')
            result['waq_his_chemical_koper_onderlaag'] = checkVariables(data, 'CUSUBT')
            if result['waq_his_chemical_koper_onderlaag']: result['waq_his_trace_metals_selector'].append('CUSUBT (mg/m³)')
            result['waq_his_chemical_nikkel_gededuceer'] = checkVariables(data, 'NIREDT')
            if result['waq_his_chemical_nikkel_gededuceer']: result['waq_his_trace_metals_selector'].append('NIREDT (mg/m³)')
            result['waq_his_chemical_nikkel_aerobe'] = checkVariables(data, 'NISTOT')
            if result['waq_his_chemical_nikkel_aerobe']: result['waq_his_trace_metals_selector'].append('NISTOT (mg/m³)')
            result['waq_his_chemical_nikkel_onderlaag'] = checkVariables(data, 'NISUBT')
            if result['waq_his_chemical_nikkel_onderlaag']: result['waq_his_trace_metals_selector'].append('NISUBT (mg/m³)')
            result['waq_his_chemical_lood_gededuceer'] = checkVariables(data, 'PBREDT')
            if result['waq_his_chemical_lood_gededuceer']: result['waq_his_trace_metals_selector'].append('PBREDT (mg/m³)')
            result['waq_his_chemical_lood_aerobe'] = checkVariables(data, 'PBSTOT')
            if result['waq_his_chemical_lood_aerobe']: result['waq_his_trace_metals_selector'].append('PBSTOT (mg/m³)')
            result['waq_his_chemical_lood_onderlaag'] = checkVariables(data, 'PBSUBT')
            if result['waq_his_chemical_lood_onderlaag']: result['waq_his_trace_metals_selector'].append('PBSUBT (mg/m³)')
            result['waq_his_chemical_opgelost_toplaag'] = checkVariables(data, 'DOCB')
            if result['waq_his_chemical_opgelost_toplaag']: result['waq_his_trace_metals_selector'].append('DOCB (g/m³)')
            result['waq_his_chemical_opgelost_onderlaag'] = checkVariables(data, 'DOCSUB')
            if result['waq_his_chemical_opgelost_onderlaag']: result['waq_his_trace_metals_selector'].append('DOCSUB (g/m³)')
            result['waq_his_chemical_poc_sediment'] = checkVariables(data, 'POCB'),
            if result['waq_his_chemical_poc_sediment']: result['waq_his_trace_metals_selector'].append('POCB (g/m³)')
            result['waq_his_chemical_poc_onderlaag'] = checkVariables(data, 'POCSUB')
            if result['waq_his_chemical_poc_onderlaag']: result['waq_his_trace_metals_selector'].append('POCSUB (g/m³)')
            result['waq_his_chemical_s_total'] = checkVariables(data, 'S')
            if result['waq_his_chemical_s_total']: result['waq_his_trace_metals_selector'].append('S (g/m³)')
            result['waq_his_chemical_zink_gededuceer'] = checkVariables(data, 'ZNREDT')
            if result['waq_his_chemical_zink_gededuceer']: result['waq_his_trace_metals_selector'].append('ZNREDT (mg/m³)')
            result['waq_his_chemical_zink_aerobe'] = checkVariables(data, 'ZNSTOT')
            if result['waq_his_chemical_zink_aerobe']: result['waq_his_trace_metals_selector'].append('ZNSTOT (mg/m³)')
            result['waq_his_chemical_zink_onderlaag'] = checkVariables(data, 'ZNSUBT')
            if result['waq_his_chemical_zink_onderlaag']: result['waq_his_trace_metals_selector'].append('ZNSUBT (mg/m³)')
            result['waq_his_trace_metals'] = True if (result['waq_his_chemical_arseen_total'] or result['waq_his_chemical_koper_total'] or
                result['waq_his_chemical_nikkel_total'] or result['waq_his_chemical_lood_total'] or result['waq_his_chemical_poc_water'] or
                result['waq_his_chemical_alkel_koolstof'] or result['waq_his_chemical_opgelost'] or result['waq_his_chemical_zwevende'] or
                result['waq_his_chemical_zind_total'] or result['waq_his_chemical_arseen_gededuceer'] or result['waq_his_chemical_arseen_aerobe'] or
                result['waq_his_chemical_arseen_onderlaag'] or result['waq_his_chemical_koper_gededuceer'] or result['waq_his_chemical_koper_aerobe'] or
                result['waq_his_chemical_koper_onderlaag'] or result['waq_his_chemical_nikkel_gededuceer'] or result['waq_his_chemical_nikkel_aerobe'] or 
                result['waq_his_chemical_nikkel_onderlaag'] or result['waq_his_chemical_lood_gededuceer'] or result['waq_his_chemical_lood_aerobe'] or
                result['waq_his_chemical_lood_onderlaag'] or result['waq_his_chemical_opgelost_toplaag'] or result['waq_his_chemical_opgelost_onderlaag'] or
                result['waq_his_chemical_poc_sediment'] or result['waq_his_chemical_poc_onderlaag'] or result['waq_his_chemical_s_total'] or
                result['waq_his_chemical_zink_gededuceer'] or result['waq_his_chemical_zink_aerobe'] or result['waq_his_chemical_zink_onderlaag']) else False
            result['waq_his_chemical'] = True if (result['waq_his_simple_oxygen'] or result['waq_his_cadmium'] or
                result['waq_his_eutrophication'] or result['waq_his_trace_metals']) else False
            # Prepare data for Microbial option
            result['waq_his_coliform_selector'] = []
            result['waq_his_microbial_salinity'] = checkVariables(data, 'Salinity')
            if result['waq_his_microbial_salinity']: result['waq_his_coliform_selector'].append('Salinity (%)')
            result['waq_his_microbial_ecoli'] = checkVariables(data, 'EColi')
            if result['waq_his_microbial_ecoli']: result['waq_his_coliform_selector'].append('EColi (MPN/100ml)')
            result['waq_his_coliform'] = True if (result['waq_his_microbial_salinity'] or result['waq_his_microbial_ecoli']) else False
            result['waq_his_microbial'] = True if (result['waq_his_coliform']) else False
            result['wq_his'] = True if (result['waq_his_physical'] or result['waq_his_chemical'] or result['waq_his_microbial']) else False
        # This is a water quality map file      
        elif ('nTimesDlwq' in data.sizes and ('mesh2d_nNodes' or 'mesh2d_nEdges') in data.sizes):
            print(f'File: {os.path.basename(path)} - Checking Water Quality Simulation ...')
            # Prepare data for Physical option
            # 1. Conservative and Decaying Tracers
            result['waq_map_conservative_selector'] = []
            result['waq_map_conservative_1'] = checkVariables(data, 'cTR1')
            if result['waq_map_conservative_1']: result['waq_map_conservative_selector'].append('cTR1 (g/m³)')
            result['waq_map_conservative_2'] = checkVariables(data, 'cTR2')
            if result['waq_map_conservative_2']: result['waq_map_conservative_selector'].append('cTR2 (g/m³)')
            result['waq_map_conservative_3'] = checkVariables(data, 'cTR3')
            if result['waq_map_conservative_3']: result['waq_map_conservative_selector'].append('cTR3 (g/m³)')
            result['waq_map_decay_1'] = checkVariables(data, 'dTR1')
            if result['waq_map_decay_1']: result['waq_map_conservative_selector'].append('dTR1 (g/m³)')
            result['waq_map_decay_2'] = checkVariables(data, 'dTR2')
            if result['waq_map_decay_2']: result['waq_map_conservative_selector'].append('dTR2 (g/m³)')
            result['waq_map_decay_3'] = checkVariables(data, 'dTR3')
            if result['waq_map_decay_3']: result['waq_map_conservative_selector'].append('dTR3 (g/m³)')
            result['waq_map_conservative_decay'] = True if (result['waq_map_conservative_1'] or result['waq_map_conservative_2'] or
                result['waq_map_conservative_3'] or result['waq_map_decay_1'] or result['waq_map_decay_2'] or result['waq_map_decay_3']) else False
            # 2. Suspended Sediment
            result['waq_map_suspended_sediment_selector'] = []
            result['waq_map_physical_inorganic_1'] = checkVariables(data, 'IM1')
            if result['waq_map_physical_inorganic_1']: result['waq_map_suspended_sediment_selector'].append('IM1 (g/m³)')
            result['waq_map_physical_inorganic_2'] = checkVariables(data, 'IM2')
            if result['waq_map_physical_inorganic_2']: result['waq_map_suspended_sediment_selector'].append('IM2 (g/m³)')
            result['waq_map_physical_inorganic_3'] = checkVariables(data, 'IM3')
            if result['waq_map_physical_inorganic_3']: result['waq_map_suspended_sediment_selector'].append('IM3 (g/m³)')
            result['waq_map_physical_inorganic_s1'] = checkVariables(data, 'IM1S1')
            if result['waq_map_physical_inorganic_s1']: result['waq_map_suspended_sediment_selector'].append('IM1S1 (g/m³)')
            result['waq_map_physical_inorganic_s2'] = checkVariables(data, 'IM2S1')
            if result['waq_map_physical_inorganic_s2']: result['waq_map_suspended_sediment_selector'].append('IM2S1 (g/m³)')
            result['waq_map_physical_inorganic_s3'] = checkVariables(data, 'IM3S1')
            if result['waq_map_physical_inorganic_s3']: result['waq_map_suspended_sediment_selector'].append('IM3S1 (g/m³)')
            result['waq_map_suspended_sediment'] = True if (result['waq_map_physical_inorganic_1'] or result['waq_map_physical_inorganic_2'] or
                result['waq_map_physical_inorganic_3'] or result['waq_map_physical_inorganic_s1'] or result['waq_map_physical_inorganic_s2'] or
                result['waq_map_physical_inorganic_s3']) else False
            result['waq_map_physical'] = True if (result['waq_map_conservative_decay'] or result['waq_map_suspended_sediment']) else False
            # Prepare data for Chemical option
            # 1. Simple Oxygen or Oxygen and BOD (water phase only)
            result['waq_map_simple_oxygen_selector'] = []
            result['waq_map_chemical_ammonium'] = checkVariables(data, 'NH4')
            if result['waq_map_chemical_ammonium']: result['waq_map_simple_oxygen_selector'].append('NH4 (g/m³)')
            result['wq_map_chemical_carbonaceous'] = checkVariables(data, 'CBOD5')
            if result['wq_map_chemical_carbonaceous']: result['waq_map_simple_oxygen_selector'].append('CBOD5 (g/m³)')
            result['wq_map_chemical_oxygen'] = checkVariables(data, 'OXY')
            if result['wq_map_chemical_oxygen']: result['waq_map_simple_oxygen_selector'].append('OXY (g/m³)')
            result['wq_map_chemical_sediment_oxygen'] = checkVariables(data, 'SOD')
            if result['wq_map_chemical_sediment_oxygen']: result['waq_map_simple_oxygen_selector'].append('SOD (g/m²)')
            result['wq_map_chemical_dfoxygen_concentration'] = checkVariables(data, 'DO')
            if result['wq_map_chemical_dfoxygen_concentration']: result['waq_map_simple_oxygen_selector'].append('DO (g/m³)')
            result['waq_map_simple_oxygen'] = True if (result['waq_map_chemical_ammonium'] or 
                result['wq_map_chemical_carbonaceous'] or result['wq_map_chemical_oxygen'] or 
                result['wq_map_chemical_sediment_oxygen'] or result['wq_map_chemical_dfoxygen_concentration']) else False
            # 2. Cadmium
            result['waq_map_cadmium_selector'] = []
            if result['waq_map_physical_inorganic_1']: result['waq_map_cadmium_selector'].append('IM1 (g/m³)')
            result['waq_map_chemical_cadmium'] = checkVariables(data, 'Cd')
            if result['waq_map_chemical_cadmium']: result['waq_map_cadmium_selector'].append('Cd (mg/m³)')
            if result['waq_map_physical_inorganic_s1']: result['waq_map_cadmium_selector'].append('IM1S1 (g/m³)')
            result['waq_map_chemical_cadmium_s1'] = checkVariables(data, 'CdS1')
            if result['waq_map_chemical_cadmium_s1']: result['waq_map_cadmium_selector'].append('CdS1 (mg/m³)')
            result['waq_map_cadmium'] = True if (result['waq_map_physical_inorganic_1'] or result['waq_map_chemical_cadmium'] or
                result['waq_map_physical_inorganic_s1'] or result['waq_map_chemical_cadmium_s1']) else False
            # 3. Eutrophication
            result['waq_map_eutrophication_selector'] = []
            if result['waq_map_chemical_ammonium']: result['waq_map_eutrophication_selector'].append('NH4 (g/m³)')
            result['waq_map_chemical_algenconcentration'] = checkVariables(data, 'A')
            if result['waq_map_chemical_algenconcentration']: result['waq_map_eutrophication_selector'].append('A (g/m³)')
            result['waq_map_chemical_orthop_concentration'] = checkVariables(data, 'DP')
            if result['waq_map_chemical_orthop_concentration']: result['waq_map_eutrophication_selector'].append('DP (g/m³)')
            result['waq_map_chemical_particular_p_concentration'] = checkVariables(data, 'PP')
            if result['waq_map_chemical_particular_p_concentration']: result['waq_map_eutrophication_selector'].append('PP (g/m³)')
            result['waq_map_chemical_organic_n_concentration'] = checkVariables(data, 'NORG')
            if result['waq_map_chemical_organic_n_concentration']: result['waq_map_eutrophication_selector'].append('NORG (g/m³)')
            result['waq_map_chemical_nitrate_n_concentration'] = checkVariables(data, 'NO3')
            if result['waq_map_chemical_nitrate_n_concentration']: result['waq_map_eutrophication_selector'].append('NO3 (g/m³)')
            result['waq_map_eutrophication'] = True if (result['waq_map_chemical_ammonium'] or result['waq_map_chemical_algenconcentration'] or
                result['waq_map_chemical_orthop_concentration'] or result['waq_map_chemical_particular_p_concentration'] or
                result['waq_map_chemical_organic_n_concentration'] or result['waq_map_chemical_nitrate_n_concentration']) else False
            # 4. Trace Metals
            result['waq_map_trace_metals_selector'] = []
            result['waq_map_chemical_arseen_total'] = checkVariables(data, 'ASWTOT')
            if result['waq_map_chemical_arseen_total']: result['waq_map_trace_metals_selector'].append('ASWTOT (mg/m³)')
            result['waq_map_chemical_koper_total'] = checkVariables(data, 'CUWTOT')
            if result['waq_map_chemical_koper_total']: result['waq_map_trace_metals_selector'].append('CUWTOT (mg/m³)')
            result['waq_map_chemical_nikkel_total'] = checkVariables(data, 'NIWTOT')
            if result['waq_map_chemical_nikkel_total']: result['waq_map_trace_metals_selector'].append('NIWTOT (mg/m³)')
            result['waq_map_chemical_lood_total'] = checkVariables(data, 'PBWTOT')
            if result['waq_map_chemical_lood_total']: result['waq_map_trace_metals_selector'].append('PBWTOT (mg/m³)')
            result['waq_map_chemical_poc_water'] = checkVariables(data, 'POCW')
            if result['waq_map_chemical_poc_water']: result['waq_map_trace_metals_selector'].append('POCW (g/m³)')
            result['waq_map_chemical_alkel_koolstof'] = checkVariables(data, 'AOCW')
            if result['waq_map_chemical_alkel_koolstof']: result['waq_map_trace_metals_selector'].append('AOCW (g/m³)')
            result['waq_map_chemical_opgelost'] = checkVariables(data, 'DOCW')
            if result['waq_map_chemical_opgelost']: result['waq_map_trace_metals_selector'].append('DOCW (g/m³)')
            result['waq_map_chemical_zwevende'] = checkVariables(data, 'SSW')
            if result['waq_map_chemical_zwevende']: result['waq_map_trace_metals_selector'].append('SSW (g/m³)')
            result['waq_map_chemical_zind_total'] = checkVariables(data, 'ZNWTOT')
            if result['waq_map_chemical_zind_total']: result['waq_map_trace_metals_selector'].append('ZNWTOT (mg/m³)')
            result['waq_map_chemical_arseen_gededuceer'] = checkVariables(data, 'ASREDT')
            if result['waq_map_chemical_arseen_gededuceer']: result['waq_map_trace_metals_selector'].append('ASREDT (mg/m³)')
            result['waq_map_chemical_arseen_aerobe'] = checkVariables(data, 'ASSTOT')
            if result['waq_map_chemical_arseen_aerobe']: result['waq_map_trace_metals_selector'].append('ASSTOT (mg/m³)')
            result['waq_map_chemical_arseen_onderlaag'] = checkVariables(data, 'ASSUBT')
            if result['waq_map_chemical_arseen_onderlaag']: result['waq_map_trace_metals_selector'].append('ASSUBT (mg/m³)')
            result['waq_map_chemical_koper_gededuceer'] = checkVariables(data, 'CUREDT')
            if result['waq_map_chemical_koper_gededuceer']: result['waq_map_trace_metals_selector'].append('CUREDT (mg/m³)')
            result['waq_map_chemical_koper_aerobe'] = checkVariables(data, 'CUSTOT')
            if result['waq_map_chemical_koper_aerobe']: result['waq_map_trace_metals_selector'].append('CUSTOT (mg/m³)')
            result['waq_map_chemical_koper_onderlaag'] = checkVariables(data, 'CUSUBT')
            if result['waq_map_chemical_koper_onderlaag']: result['waq_map_trace_metals_selector'].append('CUSUBT (mg/m³)')
            result['waq_map_chemical_nikkel_gededuceer'] = checkVariables(data, 'NIREDT')
            if result['waq_map_chemical_nikkel_gededuceer']: result['waq_map_trace_metals_selector'].append('NIREDT (mg/m³)')
            result['waq_map_chemical_nikkel_aerobe'] = checkVariables(data, 'NISTOT')
            if result['waq_map_chemical_nikkel_aerobe']: result['waq_map_trace_metals_selector'].append('NISTOT (mg/m³)')
            result['waq_map_chemical_nikkel_onderlaag'] = checkVariables(data, 'NISUBT')
            if result['waq_map_chemical_nikkel_onderlaag']: result['waq_map_trace_metals_selector'].append('NISUBT (mg/m³)')
            result['waq_map_chemical_lood_gededuceer'] = checkVariables(data, 'PBREDT')
            if result['waq_map_chemical_lood_gededuceer']: result['waq_map_trace_metals_selector'].append('PBREDT (mg/m³)')
            result['waq_map_chemical_lood_aerobe'] = checkVariables(data, 'PBSTOT')
            if result['waq_map_chemical_lood_aerobe']: result['waq_map_trace_metals_selector'].append('PBSTOT (mg/m³)')
            result['waq_map_chemical_lood_onderlaag'] = checkVariables(data, 'PBSUBT')
            if result['waq_map_chemical_lood_onderlaag']: result['waq_map_trace_metals_selector'].append('PBSUBT (mg/m³)')
            result['waq_map_chemical_opgelost_toplaag'] = checkVariables(data, 'DOCB')
            if result['waq_map_chemical_opgelost_toplaag']: result['waq_map_trace_metals_selector'].append('DOCB (g/m³)')
            result['waq_map_chemical_opgelost_onderlaag'] = checkVariables(data, 'DOCSUB')
            if result['waq_map_chemical_opgelost_onderlaag']: result['waq_map_trace_metals_selector'].append('DOCSUB (g/m³)')
            result['waq_map_chemical_poc_sediment'] = checkVariables(data, 'POCB'),
            if result['waq_map_chemical_poc_sediment']: result['waq_map_trace_metals_selector'].append('POCB (g/m³)')
            result['waq_map_chemical_poc_onderlaag'] = checkVariables(data, 'POCSUB')
            if result['waq_map_chemical_poc_onderlaag']: result['waq_map_trace_metals_selector'].append('POCSUB (g/m³)')
            result['waq_map_chemical_s_total'] = checkVariables(data, 'S')
            if result['waq_map_chemical_s_total']: result['waq_map_trace_metals_selector'].append('S (g/m³)')
            result['waq_map_chemical_zink_gededuceer'] = checkVariables(data, 'ZNREDT')
            if result['waq_map_chemical_zink_gededuceer']: result['waq_map_trace_metals_selector'].append('ZNREDT (mg/m³)')
            result['waq_map_chemical_zink_aerobe'] = checkVariables(data, 'ZNSTOT')
            if result['waq_map_chemical_zink_aerobe']: result['waq_map_trace_metals_selector'].append('ZNSTOT (mg/m³)')
            result['waq_map_chemical_zink_onderlaag'] = checkVariables(data, 'ZNSUBT')
            if result['waq_map_chemical_zink_onderlaag']: result['waq_map_trace_metals_selector'].append('ZNSUBT (mg/m³)')
            result['waq_map_trace_metals'] = True if (result['waq_map_chemical_arseen_total'] or result['waq_map_chemical_koper_total'] or
                result['waq_map_chemical_nikkel_total'] or result['waq_map_chemical_lood_total'] or result['waq_map_chemical_poc_water'] or
                result['waq_map_chemical_alkel_koolstof'] or result['waq_map_chemical_opgelost'] or result['waq_map_chemical_zwevende'] or
                result['waq_map_chemical_zind_total'] or result['waq_map_chemical_arseen_gededuceer'] or result['waq_map_chemical_arseen_aerobe'] or
                result['waq_map_chemical_arseen_onderlaag'] or result['waq_map_chemical_koper_gededuceer'] or result['waq_map_chemical_koper_aerobe'] or
                result['waq_map_chemical_koper_onderlaag'] or result['waq_map_chemical_nikkel_gededuceer'] or result['waq_map_chemical_nikkel_aerobe'] or 
                result['waq_map_chemical_nikkel_onderlaag'] or result['waq_map_chemical_lood_gededuceer'] or result['waq_map_chemical_lood_aerobe'] or
                result['waq_map_chemical_lood_onderlaag'] or result['waq_map_chemical_opgelost_toplaag'] or result['waq_map_chemical_opgelost_onderlaag'] or
                result['waq_map_chemical_poc_sediment'] or result['waq_map_chemical_poc_onderlaag'] or result['waq_map_chemical_s_total'] or
                result['waq_map_chemical_zink_gededuceer'] or result['waq_map_chemical_zink_aerobe'] or result['waq_map_chemical_zink_onderlaag']) else False
            result['waq_map_chemical'] = True if (result['waq_map_simple_oxygen'] or result['waq_map_cadmium'] or
                result['waq_map_eutrophication'] or result['waq_map_trace_metals']) else False
            # Prepare data for Microbial option
            result['waq_map_coliform_selector'] = []
            result['waq_map_microbial_salinity'] = checkVariables(data, 'Salinity')
            if result['waq_map_microbial_salinity']: result['waq_map_coliform_selector'].append('Salinity (%)')
            result['waq_map_microbial_ecoli'] = checkVariables(data, 'EColi')
            if result['waq_map_microbial_ecoli']: result['waq_map_coliform_selector'].append('EColi (MPN/100ml)')
            result['waq_map_coliform'] = True if (result['waq_map_microbial_salinity'] or result['waq_map_microbial_ecoli']) else False
            result['waq_map_microbial'] = True if (result['waq_map_coliform']) else False
            result['wq_map'] = True if (result['waq_map_physical'] or result['waq_map_chemical'] or result['waq_map_microbial']) else False

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

def getSummary(dialog_path: str, NC_paths: list) -> list:
    """
    Get the summary of the dataset received from *.nc file.

    Parameters:
    ----------
    dialog_path: str
        The path of the dialog *.dia file.
    NC_paths: list
        List of _his.nc files.

    Returns:
    -------
    list
        The list containing the summary of the dataset.
    """
    dialog, result = dialogReader(dialog_path), []
    if len(dialog) > 0:
        result.append({'parameter': 'Computation started', 'value': dialog['computation_start']})
        result.append({'parameter': 'Computation finished', 'value': dialog['computation_finish']})
        result.append({'parameter': 'Area (m2)', 'value': dialog['area']})
        result.append({'parameter': 'Volume (m3)', 'value': dialog['volume']})
    if len(NC_paths) == 0: return result
    for file in NC_paths:
        if file is not None and os.path.exists(file):
            data_his, filename = xr.open_dataset(file), os.path.basename(file).replace('_his.nc', '')
            if ('time' in data_his.sizes):
                result.append({'parameter': 'Start Date (Hydrodynamic Simulation)', 'value': pd.to_datetime(data_his['time'].values[0]).strftime('%Y-%m-%d %H:%M:%S')})
                result.append({'parameter': 'Stop Date (Hydrodynamic Simulation)', 'value': pd.to_datetime(data_his['time'].values[-1]).strftime('%Y-%m-%d %H:%M:%S')})
                result.append({'parameter': 'Number of Time Steps', 'value': data_his.sizes['time']})
            if ('laydim' in data_his.sizes): result.append({'parameter': 'Number of Layers', 'value': data_his.sizes['laydim']})
            if ('stations' in data_his.sizes and data_his.sizes['stations'] > 0): result.append({'parameter': 'Number of Observation Stations', 'value': data_his.sizes['stations']})
            if ('cross_section' in data_his.sizes and data_his.sizes['cross_section'] > 0): result.append({'parameter': 'Number of Cross Sections', 'value': data_his.sizes['cross_section']})
            if ('source_sink' in data_his.sizes and data_his.sizes['source_sink'] > 0): result.append({'parameter': 'Number of Sources/Sinks', 'value': data_his.sizes['source_sink']})
            if ('nTimesDlwq' in data_his.sizes):
                result.append({'parameter': f'Start Date ({filename})', 'value': pd.to_datetime(data_his['nTimesDlwq'].values[0]).strftime('%Y-%m-%d %H:%M:%S')})
                result.append({'parameter': f'Stop Date ({filename})', 'value': pd.to_datetime(data_his['nTimesDlwq'].values[-1]).strftime('%Y-%m-%d %H:%M:%S')})
                result.append({'parameter': f'Number of Time Steps ({filename})', 'value': data_his.sizes['nTimesDlwq']})
            if ('nStations' in data_his.sizes): result.append({'parameter': f'Number of Observation Stations ({filename})', 'value': data_his.sizes['nStations']})
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

def stationCreator(his_path: str, x_column: str, y_column: str, crs_code: str='') -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of stations.

    Parameters:
    ----------
    his_path: str
        The path of the hydrodynamic simulation (_his.nc) file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of stations.
    """
    data_his = xr.open_dataset(his_path)
    names = [name.decode('utf-8').strip() for name in data_his['station_name'].values]
    geometry = gpd.points_from_xy(data_his[x_column].values, data_his[y_column].values)
    if crs_code != '': return gpd.GeoDataFrame(data={'name': names, 'geometry': geometry}, crs=crs_code)
    return checkCoordinateReferenceSystem(names, geometry, data_his)

def sourceCreator(his_path: str) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of sources/sinks.

    Parameters:
    ----------
    his_path: str
        The path of the hydrodynamic simulation (_his.nc) file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of sources/sinks.
    """
    data_his = xr.open_dataset(his_path)
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

def crosssectionCreator(his_path: str) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of cross-section.

    Parameters:
    ----------
    his_path: str
        The path of the hydrodynamic simulation (_his.nc) file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of cross-sections.
    """
    data_his = xr.open_dataset(his_path)
    names = [name.decode('utf-8').strip() for name in data_his['cross_section_name'].values]
    x = data_his['cross_section_geom_node_coordx'].values
    y = data_his['cross_section_geom_node_coordy'].values
    p1, p2 = linearCreator(x, y)
    geometry = gpd.GeoSeries([shapely.geometry.LineString([p1, p2])])
    return checkCoordinateReferenceSystem(names, geometry, data_his)

def selectInsitu(his_path: str, map_path: str, name: str, station: str, type: str) -> pd.DataFrame:
    """
    Get insitu data.

    Parameters:
    ----------
    his_path: str
        The path of the hydrodynamic simulation (_his.nc) file.
    map_path: str
        The path of the hydrodynamic simulation (_map.nc) file.
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
    data_his, data_map = xr.open_dataset(his_path), xr.open_dataset(map_path)
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

def thermoclineComputer(file_path: str) -> pd.DataFrame:
    """
    Compute thermocline in each time step.

    Parameters:
    ----------
    file_path: str
        The path of the hydrodynamic simulation (_map.nc) file.

    Returns:
    -------
    pd.DataFrame
        The DataFrame containing the thermocline in each time step.
    """
    data = xr.open_dataset(file_path)
    index_ = numberFormatter(data['mesh2d_layer_z'].values)
    times = data['time'].values
    columns, data_list = [], []
    for i in range(len(times)):
        col_name = pd.to_datetime(times[i]).strftime('%Y-%m-%d %H:%M:%S')
        value = np.nanmean(data['mesh2d_tem1'].values[i,:,:], axis=0)
        columns.append(col_name)
        data_list.append(numberFormatter(value))
    df = pd.DataFrame(np.column_stack(data_list), index=index_, columns=columns).reset_index()
    return df

def timeseriesCreator(his_path: str, key: str, timeColumn: str='time') -> pd.DataFrame:
    """
    Create a GeoDataFrame of timeseries.

    Parameters:
    ----------
    his_path: str
        The path of the hydrodynamic or water quality simulation (_his.nc) file.
    key: str
        The key of the timeseries, used to define the name of the variable.
    columns: list
        The columns of the timeseries.

    Returns:
    -------
    pd.DataFrame
        The DataFrame of timeseries.
    """
    data_his = xr.open_dataset(his_path)
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

def unstructuredGridCreator(file_path: str) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame of unstructured grid.

    Parameters:
    ----------
    file_path: str
        The path of _map.nc file.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame of unstructured grid.
    """
    data_map = xr.open_dataset(file_path)
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

def assignValuesToMeshes(grid: gpd.GeoDataFrame, map_path: str, key: str, time_column: str) -> gpd.GeoDataFrame:
    """
    Interpolate or extrapolate z values for grid from known points
    using Inverse Distance Weighting (IDW) method.

    Parameters:
    ----------
    grid: gpd.GeoDataFrame
        The GeoDataFrame containing the meshes/unstructured grid.
    map_path: str
        The path of the hydrodynamic or water quality simulation (_map.nc) file.
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
    result, temp_grid, data_map = {}, grid.copy(), xr.open_dataset(map_path)
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

def selectPolygon(map_path: str, idx: int, key:str, time_column: str, column_layer: str) -> dict:
    """
    Get attributes of a selected polygon during the simulation.

    Parameters:
    ----------
    map_path: str
        The path of the hydrodynamic or water quality simulation (_map.nc) file.
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
    data_map = xr.open_dataset(map_path)
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

def velocityChecker(file_path: str) -> dict:
    """
    Check how many velocity layers are available.

    Parameters:
    ----------
    file_path: str
        The path to _map.nc file.

    Returns:
    -------
    dict
        A dictionary containing the index and value of velocity layers.
    """
    data_map = xr.open_dataset(file_path)
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

def velocityComputer(map_path: str, value_type: str, layer_reverse: dict) -> gpd.GeoDataFrame:
    """
    Compute velocity in each layer and average value (if possible)

    Parameters:  
    ----------
    map_path: str
        The path to _map.nc file.
    value_type: str
        The type of velocity to compute: 'Depth-average' or one specific layer.
    layer_reverse: dict
        The dictionary containing the index and value of reversed velocity layers.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame containing the vector map of the mesh.
    """
    result, data_map = {}, xr.open_dataset(map_path)
    idx = len(data_map['mesh2d_layer_z'].values) - int(layer_reverse[value_type]) - 1
    if value_type == 'Average':
        # Average velocity in each layer
        ucx = data_map['mesh2d_ucxa'].values
        ucy = data_map['mesh2d_ucya'].values
        ucm = data_map['mesh2d_ucmaga'].values
    else:
        # Velocity for specific layer
        ucx = data_map['mesh2d_ucx'].values[:, :, idx]
        ucy = data_map['mesh2d_ucy'].values[:, :, idx]
        ucm = data_map['mesh2d_ucmag'].values[:, :, idx]
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
    output_folder = os.path.join(parent_path, 'output')
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    output_HYD_path = os.path.join(output_folder, 'HYD')
    # Create the directory output_HYD_path
    if os.path.exists(output_HYD_path): shutil.rmtree(output_HYD_path, onexc=remove_readonly)
    os.makedirs(output_HYD_path, exist_ok=True)
    subdirs = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
    if len(subdirs) == 0: return {'status': 'error', 'message': 'No output directory for simulations found.'}
    # Copy folder DFM_DELWAQ to the parent directory
    DFM_DELWAQ_path = os.path.join(parent_path, 'DFM_DELWAQ')
    if os.path.exists(DFM_DELWAQ_path): shutil.rmtree(DFM_DELWAQ_path, onexc=remove_readonly)
    try: shutil.copytree(os.path.join(directory, 'DFM_DELWAQ'), DFM_DELWAQ_path)
    except Exception as e: return {'status': 'error', 'message': {str(e)}}
    # Delete folder DFM_DELWAQ
    try: shutil.rmtree(os.path.join(directory, 'DFM_DELWAQ'), onexc=remove_readonly)
    except Exception as e: return {'status': 'error', 'message': {str(e)}}
    # Copy files to the directory output
    try:
        # Copy files to the directory output
        DFM_OUTPUT_folder = os.path.join(directory, 'DFM_OUTPUT')
        select_files = ['FlowFM.dia', 'FlowFM_his.nc', 'FlowFM_map.nc']
        files = [f for f in os.listdir(DFM_OUTPUT_folder) if (os.path.isfile(os.path.join(DFM_OUTPUT_folder, f)) and f in select_files)]
        if len(files) <= 1: return {'status': 'error', 'message': 'No *.nc files found.'}
        for f in files:
            shutil.copy(os.path.join(DFM_OUTPUT_folder, f), output_HYD_path)
        # Delete folder DFM_OUTPUT
        shutil.rmtree(DFM_OUTPUT_folder, onexc=remove_readonly)
    except Exception as e: return {'status': 'error', 'message': {str(e)}}
    # Delete files in folder common_files
    common_path = os.path.join(parent_path, 'common_files')
    if os.path.exists(common_path): shutil.rmtree(common_path, onexc=remove_readonly)
    os.makedirs(common_path, exist_ok=True)
    return {'status': 'ok', 'message': 'Data is saved successfully.'}