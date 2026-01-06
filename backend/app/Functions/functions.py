import shapely, os, re, shutil, stat, json, asyncio
import base64, time, subprocess, signal, chardet, math
import geopandas as gpd, pandas as pd
import numpy as np, xarray as xr, dask.array as da
from scipy.spatial import cKDTree
from scipy.interpolate import griddata
from config import PROJECT_STATIC_ROOT, ALLOWED_USERS_PATH
from redis.asyncio.lock import Lock
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status

security = HTTPBasic()

def encoding_detect(file_path: str) -> str:
    """Detect the encoding of a file."""
    encoding = 'utf-8'
    if not os.path.exists(file_path) or not os.path.isfile(file_path): return encoding
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
    return encoding

ALLOWED_USERS = json.load(open(ALLOWED_USERS_PATH, "r", encoding=encoding_detect(ALLOWED_USERS_PATH)))

def basic_auth(credentials: HTTPBasicCredentials=Depends(security)):
    username, password = credentials.username, credentials.password
    if username not in ALLOWED_USERS or ALLOWED_USERS[username] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized", headers={"WWW-Authenticate": "Basic"}
        )
    return username

def basic_auth_ws(auth_header: str):
    if not auth_header or not auth_header.startswith("Basic "): return None
    token = auth_header.split(" ")[1]
    try:
        decoded = base64.b64decode(token).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception: return None
    if username not in ALLOWED_USERS or ALLOWED_USERS[username] != password: return None
    return username

def project_definer(old_name, username='admin'):
    return f'{username}/{old_name}' if username!='admin' else 'demo'

def remove_readonly(func, path, excinfo):
    # Change the readonly bit, but not the file contents
    os.chmod(path, stat.S_IWRITE)
    func(path)

def safe_remove(path, retries=10, delay=1):
    for _ in range(retries):
        try:
            os.remove(path)
            return
        except PermissionError:
            time.sleep(delay)
    raise Exception(f"Cannot delete file: {path}")

async def auto_extend(lock: Lock, interval: int = 10):
    """
    Auto-extend Redis lock every `interval` seconds, only if still owned.
    """
    try:
        while True:
            await asyncio.sleep(interval)
            try:
                if not await lock.locked(): break
            except Exception: break
            try: await lock.extend()
            except Exception: break
    except asyncio.CancelledError: pass

def encode_array(arr: np.ndarray) -> str:
    """Encode numpy array float32 to base64 string for fast transfer."""
    arr = arr.astype(np.float32)
    return base64.b64encode(arr.tobytes()).decode()

def decode_array(b64_str: str, shape, dtype=np.float32) -> np.ndarray:
    """Decode base64 string to numpy array."""
    arr = np.frombuffer(base64.b64decode(b64_str), dtype=dtype)
    return arr.reshape(shape)

async def layer_lock(redis, project_name: str, layer: str, timeout: int = 10):
    """Context manager lock for a specific layer."""
    lock = redis.lock(f"project:{project_name}:layer:{layer}", timeout=timeout)
    await lock.acquire()
    try: yield
    finally: await lock.release()

def serialize_geometry(gdf: gpd.GeoDataFrame):
    """
    Convert GeoDataFrame to dict GeoJSON (Polygon / MultiPolygon -> coordinates list)
    """
    features_serializable = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None: geom_serial = None
        else: geom_serial = shapely.geometry.mapping(geom)
        properties = {k: v for k, v in row.items() if k != gdf.geometry.name}
        features_serializable.append({
            "type": "Feature",
            "properties": properties,
            "geometry": geom_serial
        })
    grid_dict = {
        "type": "FeatureCollection",
        "features": features_serializable
    }
    return grid_dict

async def load_dataset_cached(project_cache, key, dm, dir_path, filename):
    """
    Load dataset from DatasetManager once per project and cache in memory.
    """
    if project_cache is None or not filename: return None
    path = os.path.normpath(os.path.join(dir_path, filename))
    if not os.path.exists(path): return None
    ds = dm.get(path)
    project_cache[key] = ds
    return ds

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
    # 1. Physical
    # 1.1. Conservative and Decaying Tracers
    'cTR1': 'Conservative Tracer 1 (g/m³)', 'dTR1': 'Decaying Tracer 1 (g/m³)',
    'cTR2': 'Conservative Tracer 2 (g/m³)', 'dTR2': 'Decaying Tracer 2 (g/m³)',
    'cTR3': 'Conservative Tracer 3 (g/m³)', 'dTR3': 'Decaying Tracer 3 (g/m³)',
    'RcDecTR1': 'Decay rate tracer1 for AGE calculations (1/day)',
    'RcDecTR2': 'Decay rate tracer2 for AGE calculations (1/day)',
    'RcDecTR3': 'Decay rate tracer3 for AGE calculations (1/day)',
    # 1.2. Suspended Sediment
    'IM1': 'Inorganic Matter (IM1) (gDM/m³)', 'IM1S1': 'IM1 in layer S1 (g/m²)',
    'IM2': 'Inorganic Matter (IM2) (gDM/m³)', 'IM2S1': 'IM2 in layer S1 (g/m²)',
    'IM3': 'Inorganic Matter (IM3) (gDM/m³)', 'IM3S1': 'IM3 in layer S1 (g/m²)',
    'VSedIM1': 'Sedimentation velocity IM1 (m/day)', 'TaucSIM1': 'Critical shear stress for sedimentation IM1 (N/m²)',
    'VSedIM2': 'Sedimentation velocity IM2 (m/day)', 'TaucSIM2': 'Critical shear stress for sedimentation IM2 (N/m²)',
    'VSedIM3': 'Sedimentation velocity IM3 (m/day)', 'TaucSIM3': 'Critical shear stress for sedimentation IM3 (N/m²)',
    'TaucRS1DM': 'Critical shear stress for resuspension DM layer S1 (N/m²)',
    # 2. Chemical 
    # 2.1. Simple Oxygen
    'NH4': 'Ammonium (g/m³)', 'CBOD5': 'Carbonaceous BOD (g/m³)', 'DO': 'Dissolved Oxygen concentration (g/m³)',
    'OXY': 'Dissolved Oxygen (g/m³)', 'SOD': 'Sediment Oxygen Demand (g/m²)',
    'RcNit': 'First-order Nitrification Rate (1/day)', 'RcBOD': 'Decay rate BOD (first pool) at 20°C (1/day)',
    'COXBOD': 'Critical oxygen concentration for BOD decay (g/m³)', 'OOXBOD': 'Optimum Oxygen concentration for BOD decay (g/m³)',
    'CFLBOD': 'Oxygen function level for Oxygen below COXBOD', 'O2FuncBOD': 'Oxygen function for CBOD decay',
    'BODu': 'Calculated Carbonaceous BOD at ultimate (g/m³)', 'SWRear': 'Switch for Oxygen reaeration formulation',
    'KLRear': 'Reaeration transfer coefficient (m/day)', 'fSOD': 'Zeroth-order sediment Oxygen demand flux (g/m²/day)',
    'RcSOD': 'Decay rate SOD at 20°C (1/day)', 'Temp': 'Ambient water Temperature (°C)', 'VWind': 'Wind speed (m/s)',
    # 2.2. Oxygen with Biochemical Oxygen Demand (BOD) (water phase only)
    'Salinity': 'Salinity (g/kg)', 'RcBOD': 'Decay rate BOD (first pool) at 20°C (1/day)',
    'Phyt': 'Total carbon in phytoplankton (g/m³)', 'SaturOXY': 'Saturation Concentration (g/m³)',
    'SatPercOXY': 'Actual Saturation Percentage O2 (%)',
    # 2.3. Cadmium
    'Cd': 'Cadmium (g/m³)', 'CdS1': 'Cadmium in S1 (g/m²)', 'ZResDM': 'Zeroth-order resuspension flux DM (g/m²/day)',
    # 2.4. Eutrophication (Eutrof 1a model)
    'AAP': 'Adsorbed Ortho Phosphate (g/m³)', 'DetC': 'Detritus Carbon (g/m³)', 'DetN': 'Detritus Nitrogen (g/m³)',
    'DetP': 'Detritus Phosphorus (g/m³)', 'GREEN':'Algae (non-Diatoms) (g/m³)', 'NO3':'Nitrate (g/m³)',
    'PO4': 'Ortho-Phosphate (g/m³)', 'Cl':'Chloride (g/m³)', 'Opal':'Inorganic Silica (g/m³)',
    'SWAdsP': 'Switch for Adsorbed Phosphate', 'KdPO4AAP': 'distrib. coeff. (-) or ads. eq. const. (m³/g)',
    'RcDetC': 'First-order mineralisation rate DetC (1/day)', 'TcDetC': 'Temperature coefficient for mineralisation DetC',
    'CTMin': 'Critical temperature for mineralisation (°C)', 'NCRatGreen': 'N:C ratio Greens (gN/gC)',
    'PCRatGreen': 'P:C ratio Greens (gP/gC)', 'FrAutGreen': 'Fraction autolysis Greens',
    'FrDetGreen': 'Fraction to detritus by mortality Greens', 'VSedDetC': 'Sedimentation velocity DetC (m/day)',
    'TauCSDetC': 'Critical shear stress for sedimentation DetC (N/m²)', 'RcDetN': 'First-order mineralisation rate DetN (1/day)',
    'TcDetN': 'Temperature coefficient for mineralisation DetN', 'RcDetP': 'First-order mineralisation rate DetP (1/day)',
    'MRespGreen': 'Maintenance respiration Greens st.temp', 'GRespGreen': 'Growth respiration factor Greens',
    'Mort0Green': 'Mortality rate constant Greens', 'SalM1Green': 'Lower salinity limit for mortality Greens',
    'SalM2Green': 'Upper salinity limit for mortality Greens (g/kg)', 'TcNit': 'Temperature coefficient for nitrification',
    'CTNit': 'Critical Temperature for nitrification (°C)', 'COXNIT': 'Critical Oxygen concentration for nitrification (g/m³)',
    'OOXNIT': 'Optimum Oxygen concentration for nitrification (g/m³)', 'TcDenWat': 'Temperature coefficient for denitrification',
    'COXDEN': 'Critical Oxygen concentration for denitrification (g/m³)', 'RcDenWat': 'First-order denitrification rate in water column (1/day)',
    'OOXDEN': 'Optimum Oxygen concentration for denitrification (g/m³)', 'TCRear': 'Temperature coefficient for rearation',
    'O2FuncBOD': 'Oxygen function for CBOD decay', 'fResS1DM': 'Total resuspension flux DM from layer S1 (g/m²/day)',
    'ExtVlIM1': 'VL specific extinction coefficient M1 (m²/gDM)', 'ExtVlBak': 'Background extinction visible light (1/m)',
    'DayL': 'Daylength (0-1) (day)', 'OptDLGreen': 'Daylength for growth saturation Greens (day)',
    'PrfNH4gree': 'Ammonium preferency over nitrate Greens', 'KMDINgreen': 'Half-saturation value N Greens (gN/m³)',
    'KMPgreen': 'Half-saturation value P Greens (gP/m³)', 'RadSatGree': 'Total radiation growth saturation greens (W/m²)',
    'TcGroGreen': 'Temperature coefficient for processes Greens', 'ExtVlDetC': 'VL specific extinction coefficient DetC (m²/gC)',
    'ExtVlGreen': 'VL specific extinction coefficient Greens (m²/gC)', 'RadSurf': 'Irradiation at the water surface (W/m²)',
    'Chezy': 'Chezy coefficient (m^0.5/s)', 'AlgN': 'Total Nitrogen in algae (gN/gC)', 'AlgP': 'Total Phosphorus in algae (gP/gC)',
    'SS': 'Suspended Solids (g/m³)', 'TotN': 'Total Nitrogen (including algae) (g/m³)', 'TotP': 'Total Phosphorus (including algae) (g/m³)',
    'KjelN': 'Kjeldahl Nitrogen (g/m³)', 'LimDLGreen': 'Daylength limitation function for Greens (0-1)',
    'LimNutGree': 'Nutrient limitation function for Greens (0-1)', 'LimRadGree': 'Radiation limitation function for Greens (0-1)',
    'Chlfa': 'Chlorophyll-a concentration (g/m³)', 'ExtVlPhyt': 'VL extinction by Phytoplankton (m²/gC)',
    # 2.5. Trace Metals
    'ASWTOT': 'Total Arsenic (g/m³)', 'CUWTOT': 'Total Copper (g/m³)', 'NIWTOT': 'Total Nickel (g/m³)', 'PBWTOT': 'Total Lead (g/m³)',
    'POCW': 'POC in water (g/m³)', 'AOCW': 'Algen Koolstof (g/m³)', 'DOCW': 'Opgelost organisch C waterkolom (g/m³)',
    'SSW': 'Zwevende stof water (g/m³)', 'ZNWTOT': 'Total Zinc (g/m³)', 'ASREDT': 'Arseen total gereduceerde laag (g/m³)',
    'ASSTOT': 'Arseen total aerobe laag (g/m³)', 'ASSUBT': 'Arseen total in onderlaag (g/m³)', 'CUREDT': 'Koper total gereduceerde laag (g/m³)',
    'CUSTOT': 'Koper total aerobe laag (g/m³)', 'CUSUBT': 'Koper total in onderlaag (g/m³)', 'NIREDT': 'Nikkel total gereduceerde laag (g/m³)',
    'NISTOT': 'Nikkel total aerobe laag (g/m³)', 'NISUBT': 'Nikkel total in onderlaag (g/m³)', 'PBREDT': 'Lood total gereduceerde laag (g/m³)',
    'PBSTOT': 'Lood total aerobe laag (g/m³)', 'PBSUBT': 'Lood total in onderlaag (g/m³)', 'DOCB': 'Opgelost orgamisch C toplaag (g/m³)',
    'DOCSUB': 'Opgelost orgamisch C sediment onderlaag (g/m³)', 'POCB': 'POC conc. in sediment (g/m³)', 'POCSUB': 'opgelost POC in onderlaag (g/m³)',
    'S': 'Total S', 'ZNREDT': 'Zink total gereduceerde laag (g/m³)', 'ZNSTOT': 'Zink total aerobe laag (g/m³)', 'ZNSUBT': 'Zink total in onderlaag (g/m³)',
    'aAs': 'Correctiefactor pH', 'aCu': 'Correctiefactor pH', 'aNi': 'Correctiefactor pH', 'aPb': 'Correctiefactor pH', 'aZn': 'Correctiefactor pH',
    'bAs': 'Correctiefactor CL', 'bCu': 'Correctiefactor CL', 'bNi': 'Correctiefactor pH', 'bPb': 'Correctiefactor Cl', 'bZn': 'Correctiefactor Cl',
    'alfa': 'Conversion factor algae in POC (gPOC/gAOC)', 'CUSulf': 'Constant conc. Cu-Sulfide precipitate (g/m³)', 'DZ1': 'Thickness aerobic top layer (m)',
    'DZ2': 'Thickness reduced sublayer (m)', 'Ez0': 'Effective diffusion coeff sediment/water (m²/day)', 'fbx': 'Percentage sediment < 16um',
    'fc': 'Carbon;organic matter ratio algae', 'fwx': 'Percentage suspended solids < 16 um', 'KAsDOC': 'Partitioncoeff. As on DOC (m³/gDOC)',
    'KAsSS': 'Partitioncoeff. As on SS (equivalents) (l/eq*10-6)', 'KAsSSW': 'Partitioncoeff. As on SS (m³/gSSW)', 'KCuDOC': 'Partitioncoeff. Cu on DOC (m³/gDOC)',
    'KCuSS': 'Partitioncoeff. Cu on SS (equivalents) (l/eq*10-6)', 'KCuSSW': 'Partitioncoeff. Cu on SS (m³/gSSW)', 'KdAOC': 'Phytoplankton decay rate (1/day)',
    'KHYDW': 'Snelheidsconstante hydrolyse POC water (1/day)', 'KHYDB': 'Snelheidsconstante hydrolyse POC sediment (1/day)',
    'KDMINW': 'Snelheidsconstante mineralisatie water (1/day)', 'KDMINB': 'Snelheidsconstante mineralisatie sediment (1/day)',
    'KNiDOC': 'Partitioncoeff. Ni on DOC (m³/gDOC)', 'KNiSS': 'Partitioncoeff. Ni on SS (equivalents) (l/eq*10-6)',
    'KPbDOC': 'Partitioncoeff. Pb on DOC (m³/gDOC)', 'KPbSS': 'Partitioncoeff. Pb on SS (equivalents) (l/eq*10-6)',
    'KPbSSW': 'Partitioncoeff. Pb on SS (m³/gSSW)', 'KZnDOC': 'Partitioncoeff. Zn on DOC (m³/gDOC)', 'KZnSS': 'Partitioncoeff. Zn on SS (equivalents) (l/eq*10-6)',
    'KZnSSW': 'Partitioncoeff. Zn on SS (m³/gSSW)', 'NIsulf': 'Constant conc. Ni-Sulfide precipitate (g/m³)', 'Pbsulf': 'Constant conc. Pb-Sulfide precipitate (g/m³)',
    'POR': 'Porosity', 'RHOANO': 'Density of organic matter (g/m³)', 'RHOORG': 'Density of inorganic matter (g/m³)', 'Vsp': 'Sedimentatiesnelheid algen (m/day)',
    'Vss': 'Sedimentatiesnelheid SS (m/day)', 'Vsn': 'Sedimentatiesnelheid organische stof (m/day)', 'Znsulf': 'Constant conc. Zn-Sulfide precipitate (g/m³)',
    'pHb': 'Zuurgraad waterbodem (pH)', 'PAOC': 'AOC productiesnelheid (g/m³/day)', 'Fres': 'Resuspensie flux (g/m²/day)',
    'ASatm': 'Gedistribueerde bron As (g/m²/day)', 'CUatm': 'Gedistribueerde bron Cu (g/m²/day)', 'NIatm': 'Gedistribueerde bron Ni (g/m²/day)',
    'PBatm': 'Gedistribueerde bron Pb (g/m²/day)', 'ZNatm': 'Gedistribueerde bron Zn (g/m²/day)',
    # 3. Microbial
    # 3.1. Coliform Bacteria
    'Salinity': 'Salinity (g/kg)', 'EColi': 'E.Coli bacteria (MPN/m³)', 'RcMrtEColi': 'First-order mortality rate E.Coli (1/day)',
    'ExtVl': 'Total extinction coefficient visible light (1/m)', 'DayRadSurf': 'Irradiation at the water surface (W/m²)',
    # 4. Water Quality - General
    'volume': 'Volume (m³)'
}

def numberFormatter(arr: np.array, decimals: int=2) -> list:
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
    list
        The list with formatted numbers.
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
        return np.reshape(result, arr.shape)
    except:
        print("Input array contains non-numeric values")
        return list(arr)

def getVectorNames() -> list:
    """
    Get the names of the vector variables.

    Returns:
    -------
    list
        The list containing the names of the vector variables.
    """
    result = [(0,'Velocity')]
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
    if float(vmin) < 0 and float(vmax) < 0: return False
    return bool(float(vmin) != float(vmax))

def getVariablesNames(Out_files: list, model_type: str='') -> dict:
    """
    Get the names of the variables in the dataset received from *.nc file.

    Parameters:
    ----------
    Out_files: list
        The list of the *.nc files (in xr.Dataset format).
    model_type: str
        The type of the model used.

    Returns:
    -------
    dict
        The dictionary containing the names of the variables.
    """
    result = {}
    for data in Out_files:
        if data is None: continue
        # This is a hydrodynamic his file
        if 'time' in data.sizes and any(k in data.sizes for k in ['stations', 'cross_section', 'source_sink']):
            print(f"- Checking Hydrodynamic Simulation: His file...")
            # Prepare data for hydrodynamic options
            result['hyd_obs'] = data.sizes['stations'] > 0 if ('stations' in data.sizes) else False
            result['cross_sections'] = False
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
            print(f"- Checking Hydrodynamic Simulation: Map file...")
            result['z_layers'] = checkVariables(data, 'mesh2d_layer_z')
            # Prepare data for thermocline parameters
            # 1. Thermocline
            result['thermocline_hyd'] = checkVariables(data, 'mesh2d_tem1')
            # 2. Spatial single layer hydrodynamic maps
            result['hyd_wl_dynamic'] = checkVariables(data, 'mesh2d_s1')
            result['hyd_wd_dynamic'] = checkVariables(data, 'mesh2d_waterdepth')
            result['single_layer'] = True if (result['hyd_wl_dynamic'] or result['hyd_wd_dynamic']) else False
            # 3. Spatial multi layer hydrodynamic maps
            result['spatial_salinity'] = checkVariables(data, 'mesh2d_sa1')
            result['spatial_contaminant'] = checkVariables(data, 'mesh2d_Contaminant')
            result['multi_layer'] = True if (result['thermocline_hyd'] or
                result['spatial_salinity'] or result['spatial_contaminant']) else False
            # 4. Spatial static maps
            result['waterdepth_static'] = checkVariables(data, 'mesh2d_waterdepth')
            result['spatial_static'] = True if (result['waterdepth_static']) else False
            result['spatial_map'] = True if (result['single_layer'] or result['multi_layer']) else False
            result['hide_map'] = result['spatial_map']
        # This is a water quality his file
        elif ('nTimesDlwq' in data.sizes and not any(k in data.sizes for k in ['mesh2d_nNodes', 'mesh2d_nEdges'])):
            print(f"- Checking Water Quality Simulation: His file...")
            variables = set(data.variables.keys()) - set(['nTimesDlwqBnd', 'station_name', 'station_x', 'station_y', 'station_z', 'nTimesDlwq'])
            result['waq_his'] = False
            # Prepare data for Physical option
            # 1. Conservative and Decaying Tracers
            if model_type == 'conservative-tracers':
                result['waq_his_conservative_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_conservative_selector'].append(item)
                result['waq_his_conservative_decay'] = True if len(result['waq_his_conservative_selector']) > 0 else False
                result['waq_his'] = result['waq_his_conservative_decay']
            # 2. Suspended Sediment
            elif model_type == 'suspend-sediment':
                result['waq_his_suspended_sediment_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_suspended_sediment_selector'].append(item)
                result['waq_his_suspended_sediment'] = True if len(result['waq_his_suspended_sediment_selector']) > 0 else False
                result['waq_his'] = result['waq_his_suspended_sediment']
            # Prepare data for Chemical option
            # 1. Simple Oxygen
            elif model_type == 'simple-oxygen':
                result['waq_his_simple_oxygen_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_simple_oxygen_selector'].append(item)
                result['waq_his_simple_oxygen'] = True if len(result['waq_his_simple_oxygen_selector']) > 0 else False
                result['waq_his'] = result['waq_his_simple_oxygen']
            # 2. Oxygen and BOD (water phase only)
            elif model_type == 'oxygen-bod-water':
                result['waq_his_oxygen_bod_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_oxygen_bod_selector'].append(item)            
                result['waq_his_oxygen_bod'] = True if (len(result['waq_his_oxygen_bod_selector'])) else False
                result['waq_his'] = result['waq_his_oxygen_bod']
            # 3. Cadmium
            elif model_type == 'cadmium':
                result['waq_his_cadmium_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_cadmium_selector'].append(item)
                result['waq_his_cadmium'] = True if len(result['waq_his_cadmium_selector']) > 0 else False
                result['waq_his'] = result['waq_his_cadmium']
            # 4. Eutrophication
            elif model_type == 'eutrophication':
                result['waq_his_eutrophication_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_eutrophication_selector'].append(item)
                result['waq_his_eutrophication'] = True if len(result['waq_his_eutrophication_selector']) > 0 else False
                result['waq_his'] = result['waq_his_eutrophication']
            # 5. Trace Metals
            elif model_type == 'trace-metals':
                result['waq_his_trace_metals_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_trace_metals_selector'].append(item)
                result['waq_his_trace_metals'] = True if len(result['waq_his_trace_metals_selector']) > 0 else False
                result['waq_his'] = result['waq_his_trace_metals']
            # Prepare data for Microbial option
            elif model_type == 'coliform':
                result['waq_his_coliform_selector'] = []
                for item in variables:
                    if checkVariables(data, item): result['waq_his_coliform_selector'].append(item)
                result['waq_his_coliform'] = True if len(result['waq_his_coliform_selector']) > 0 else False
                result['waq_his'] = result['waq_his_coliform']
        # This is a water quality map file      
        elif ('nTimesDlwq' in data.sizes and any(k in data.sizes for k in ['mesh2d_nNodes', 'mesh2d_nEdges'])):
            print(f'- Checking Water Quality Simulation: Map file...')
            result['wq_map'] = result['thermocline_waq'] = False
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
                        if item1 not in elements_check: result['waq_map_conservative_selector'].append(item1)
                result['waq_map_conservative_selector'] = list(dict.fromkeys(result['waq_map_conservative_selector']))
                if len(result['waq_map_conservative_selector']) > 0:
                    result['wq_map'] = result['waq_map_conservative_decay'] = result['thermocline_waq'] = True              
            # 2. Suspended Sediment
            elif model_type == 'suspend-sediment':
                result['waq_map_suspended_sediment_selector'], result['waq_map_suspended_sediment'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_suspended_sediment_selector']}
                        if item1 not in elements_check: result['waq_map_suspended_sediment_selector'].append(item1)
                result['waq_map_suspended_sediment_selector'] = list(dict.fromkeys(result['waq_map_suspended_sediment_selector']))
                if len(result['waq_map_suspended_sediment_selector']) > 0:
                    result['wq_map'] = result['waq_map_suspended_sediment'] = result['thermocline_waq'] = True
            # Prepare data for Chemical option
            # 1. Simple Oxygen
            elif model_type == 'simple-oxygen':
                result['waq_map_simple_oxygen_selector'], result['waq_map_simple_oxygen'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_simple_oxygen_selector']}
                        if item1 not in elements_check: result['waq_map_simple_oxygen_selector'].append(item1)
                result['waq_map_simple_oxygen_selector'] = list(dict.fromkeys(result['waq_map_simple_oxygen_selector']))
                if len(result['waq_map_simple_oxygen_selector']) > 0:
                    result['wq_map'] = result['waq_map_simple_oxygen'] = result['thermocline_waq'] = True
            # 2. Oxygen and BOD (water phase only)
            elif model_type == 'oxygen-bod-water':
                result['waq_map_oxygen_bod_selector'], result['waq_map_oxygen_bod'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_oxygen_bod_selector']}
                        if item1 not in elements_check: result['waq_map_oxygen_bod_selector'].append(item1)
                result['waq_map_oxygen_bod_selector'] = list(dict.fromkeys(result['waq_map_oxygen_bod_selector']))
                if len(result['waq_map_oxygen_bod_selector']) > 0:  
                    result['wq_map'] = result['waq_map_oxygen_bod'] = result['thermocline_waq'] = True
            # 3. Cadmium
            elif model_type == 'cadmium':
                result['waq_map_cadmium_selector'], result['waq_map_cadmium'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_cadmium_selector']}
                        if item1 not in elements_check: result['waq_map_cadmium_selector'].append(item1)
                result['waq_map_cadmium_selector'] = list(dict.fromkeys(result['waq_map_cadmium_selector']))
                if len(result['waq_map_cadmium_selector']) > 0:
                    result['wq_map'] = result['waq_map_cadmium'] = result['thermocline_waq'] = True
            # 4. Eutrophication
            elif model_type == 'eutrophication':
                result['waq_map_eutrophication_selector'], result['waq_map_eutrophication'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_eutrophication_selector']}
                        if item1 not in elements_check: result['waq_map_eutrophication_selector'].append(item1)
                result['waq_map_eutrophication_selector'] = list(dict.fromkeys(result['waq_map_eutrophication_selector']))
                if len(result['waq_map_eutrophication_selector']) > 0:
                    result['wq_map'] = result['waq_map_eutrophication'] = result['thermocline_waq'] = True
            # 5. Trace Metals
            elif model_type == 'trace-metals':
                result['waq_map_trace_metals_selector'], result['waq_map_trace_metals'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x[0] for x in result['waq_map_trace_metals_selector']}
                        if item1 not in elements_check: result['waq_map_trace_metals_selector'].append(item1)
                result['waq_map_trace_metals_selector'] = list(dict.fromkeys(result['waq_map_trace_metals_selector']))
                if len(result['waq_map_trace_metals_selector']) > 0:
                    result['wq_map'] = result['waq_map_trace_metals'] = result['thermocline_waq'] = True
            # Prepare data for Microbial option
            elif model_type == 'coliform':
                result['waq_map_coliform_selector'], result['waq_map_coliform'] = [], False
                for item in variables:
                    item1 = item.replace('mesh2d_', '').replace('2d_', '')
                    if checkVariables(data, item):
                        elements_check = {x for x in result['waq_map_coliform_selector']}
                        if item1 not in elements_check: result['waq_map_coliform_selector'].append(item1)
                result['waq_map_coliform_selector'] = list(dict.fromkeys(result['waq_map_coliform_selector']))
                if len(result['waq_map_coliform_selector']) > 0:
                    result['wq_map'] = result['waq_map_coliform'] = result['thermocline_waq'] = True
            result['spatial_map'] = result['single_layer'] = result['multi_layer'] = result['wq_map']
            result['hide_map'] = result['spatial_map']
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
    if not isinstance(values, list): values = [values]
    result = []
    for value in values:
        result.append(dict.get(value, value))
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
    with open(f'{dialog_file}', 'r', encoding=encoding_detect(dialog_file)) as f:
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
        List of _his.nc files.

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
        crs_code = data_his['wgs84'].attrs.get('EPSG_code', 'EPSG:4326')
        result = gpd.GeoDataFrame(data={'name': name, 'geometry': geometry}, crs=crs_code)
    else:
        crs_code = data_his['projected_coordinate_system'].attrs.get('EPSG_code', 'EPSG:4326')
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
        z_values: np.ndarray, n_neighbors: int=2, geo_type: str='polygon') -> np.ndarray:
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
    geo_type: str
        The type of geometry, accepted values are: 'polygon' or 'point'.

    Returns:
    -------
    np.ndarray
        The interpolated z values.
    """
    gdf_known = gpd.GeoDataFrame(geometry=gpd.points_from_xy(x_coords, y_coords), crs = grid_net.crs).to_crs(epsg=32632)
    gdf_points = grid_net.copy().to_crs(epsg=32632)
    if geo_type == 'polygon': gdf_points['geometry'] = gdf_points['geometry'].centroid
    tree = cKDTree(list(zip(gdf_known['geometry'].x, gdf_known['geometry'].y)))
    dists, idx = tree.query(list(zip(gdf_points['geometry'].x, gdf_points['geometry'].y)), k = n_neighbors)
    weight = 1 / (dists + 1e-10)**2
    value = np.sum(weight * z_values[idx], axis=1)/np.sum(weight, axis=1)
    return numberFormatter(value)

def layerCounter(data_map: xr.Dataset, type: str='hyd') -> dict:
    """
    Check how many layers are available.

    Parameters:
    ----------
    data_map: xr.Dataset
        The dataset received from _map file.
    type: str
        The type of data, accepted values are: 'hyd' or 'waq'.

    Returns:
    -------
    dict
        A dictionary containing the index and value of velocity layers in reversed order.
    """
    layers = {}
    if type == 'hyd':
        z_layer = [round(x, 2) for x in data_map['mesh2d_layer_z'].values]
        # Add depth-average if available
        if {'mesh2d_ucxa', 'mesh2d_ucya'}.issubset(data_map.variables.keys()): layers['-1'] = 'Average'
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
            layers[str(len(z_layer)-i-1)] = f'Depth: {z_layer[i]} m'
    else:
        z_layer = np.round([100*x for x in data_map['mesh2d_layer_dlwq'].data.compute()], 0)
        layers['-1'] = 'Average'
        for i in reversed(range(len(z_layer))):
            layers[str(len(z_layer)-i-1)] = f'Sigma: {z_layer[i]} %'
    return layers

def vectorComputer(data_map: xr.Dataset, value_type: str, row_idx: int, step: int=-1) -> dict:
    """
    Compute vector in each layer and average value (if possible)

    Parameters:  
    ----------
    data_map: xr.Dataset
        The dataset received from _map file.
    value_type: str
        The type of vector to compute: 'Average' or one specific layer.
    row_idx: int
        The index of the interested layer.
    step: int
        The index of the interested time step.

    Returns:
    -------
    dict
        A dictionary containing time, coordinates, and values of the vector.
    """
    if value_type == 'Average':
        # Average velocity in each layer
        ucx = data_map['mesh2d_ucxa'].isel(time=step).values
        ucy = data_map['mesh2d_ucya'].isel(time=step).values
        ucm = data_map['mesh2d_ucmaga'].isel(time=step).values
    else:
        # Velocity for specific layer
        ucx = data_map['mesh2d_ucx'].isel(time=step).values[:, row_idx]
        ucy = data_map['mesh2d_ucy'].isel(time=step).values[:, row_idx]
        ucm = data_map['mesh2d_ucmag'].isel(time=step).values[:, row_idx]
    # Get indices of non-nan values
    col_idx = np.where(~np.isnan(ucx) & ~np.isnan(ucy) & ~np.isnan(ucm))
    # Coordinates (filtered)
    x_coords = data_map['mesh2d_face_x'].values[col_idx]
    y_coords = data_map['mesh2d_face_y'].values[col_idx]
    # Values (filtered)
    ucx_valid = np.round(ucx[col_idx].astype(np.float64), 5)
    ucy_valid = np.round(ucy[col_idx].astype(np.float64), 5)
    ucm_valid = np.round(ucm[col_idx].astype(np.float64), 2)
    result = {"time": pd.to_datetime(data_map['time'].values[step]).strftime('%Y-%m-%d %H:%M:%S'),
        "coordinates": np.column_stack((x_coords, y_coords)).tolist(),
        "values": np.column_stack((ucx_valid, ucy_valid, ucm_valid)).tolist()
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
    with open(template_path, 'r', encoding=encoding_detect(template_path)) as file:
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
        path = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "input"))
        # Write weather.tim file
        tim_path = os.path.normpath(os.path.join(path, filename))
        with open(tim_path, 'w', encoding=encoding_detect(tim_path)) as f:
            for row in data:
                if unit == 'sec': row[0] = int(row[0]/1000)
                elif unit == 'min': row[0] = int(row[0]/(1000*60))
                temp = '  '.join([str(r) for r in row])
                f.write(f"{temp}\n")
        # Add weather data to FlowFM.ext file
        ext_path = os.path.normpath(os.path.join(path, "FlowFM.ext"))
        if os.path.exists(ext_path):
            with open(ext_path, 'r', encoding=encoding_detect(ext_path)) as f:
                update_content = f.read()
            parts = re.split(r'\n\s*\n', update_content)
            parts = [p.strip() for p in parts if p.strip()]
            if (any(filename in part for part in parts)): 
                index = parts.index([part for part in parts if filename in part][0])
                parts[index] = content
            else: parts.append(content)
            with open(ext_path, 'w', encoding=encoding_detect(ext_path)) as file:
                joined_parts = '\n\n'.join(parts)
                file.write(f"\n{joined_parts}\n")
        else:
            with open(ext_path, 'w', encoding=encoding_detect(ext_path)) as f:
                f.write(f"\n{content}\n")
        status, message = 'ok', "Data is saved successfully."
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
        output_folder = os.path.normpath(os.path.join(parent_path, 'output'))
        os.makedirs(output_folder, exist_ok=True)
        output_HYD_path = os.path.normpath(os.path.join(output_folder, 'HYD'))
        # Create the directory output_HYD_path
        if os.path.exists(output_HYD_path): shutil.rmtree(output_HYD_path, onerror=remove_readonly)
        os.makedirs(output_HYD_path, exist_ok=True)
        subdirs = [d for d in os.listdir(directory) if os.path.isdir(os.path.normpath(os.path.join(directory, d)))]
        if not subdirs: return {'status': 'error', 'message': f'No simulation output folders found: {subdirs}.'}
        # Copy folder DFM_DELWAQ to the parent directory
        DFM_DELWAQ_from = os.path.normpath(os.path.join(directory, 'DFM_DELWAQ'))
        DFM_DELWAQ_to = os.path.normpath(os.path.join(parent_path, 'DFM_DELWAQ'))
        if os.path.exists(DFM_DELWAQ_to): shutil.rmtree(DFM_DELWAQ_to, onerror=remove_readonly)
        if os.path.exists(DFM_DELWAQ_from):
            shutil.copytree(DFM_DELWAQ_from, DFM_DELWAQ_to)
            shutil.rmtree(DFM_DELWAQ_from, onerror=remove_readonly)
        # Copy files to the directory output
        DFM_OUTPUT_folder = os.path.normpath(os.path.join(directory, 'DFM_OUTPUT'))
        if not os.path.exists(DFM_OUTPUT_folder):
            return {'status': 'error', 'message': 'No output folder found'}
        select_files = ['FlowFM.dia', 'FlowFM_his.nc', 'FlowFM_map.nc']
        found_files = [f for f in os.listdir(DFM_OUTPUT_folder) if f in select_files]
        if len(found_files) == 0: return {'status': 'error', 'message': 'No required files found in the output folder'}
        # Copy and Remove the outputs
        for f in found_files:
            src = os.path.normpath(os.path.join(DFM_OUTPUT_folder, f))
            # # Using .nc format
            # shutil.copy2(src, output_HYD_path)

            # Using .zarr format
            if f.endswith('.nc'):
                zarr_path = os.path.normpath(os.path.join(output_HYD_path, f.replace('.nc', '.zarr')))
                tmp_path = zarr_path + "_tmp"
                if os.path.exists(tmp_path): shutil.rmtree(tmp_path, onerror=remove_readonly)
                with xr.open_dataset(src, chunks='auto') as ds:
                    ds.to_zarr(tmp_path, mode='w', consolidated=True, compute=True)
                os.rename(tmp_path, zarr_path)
            else: shutil.copy2(src, output_HYD_path)
            safe_remove(src)
        # Clean DFM_OUTPUT folder
        if os.path.exists(DFM_OUTPUT_folder): shutil.rmtree(DFM_OUTPUT_folder, onerror=remove_readonly)
        return {'status': 'ok', 'message': 'Simulation completed successfully'}
    except Exception as e: return {'status': 'error', 'message': str(e)}

def meshProcess(is_hyd: bool, arr: np.ndarray, cache: dict) -> np.ndarray:
    """
    Optimized mesh processing using vectorization and interp1d interpolation.

    Parameters
    ----------
    is_hyd: bool
        True if HYD, False if WAQ.
    arr: np.ndarray
        The array to be processed.
    cache: dict
        Cache containing 'df', 'depth_values', 'n_rows'.

    Returns
    -------
    np.ndarray
        The smoothed values.
    """
    cache_copy = cache.copy()
    df, n_rows = pd.DataFrame(cache_copy["df"]), cache_copy["n_rows"]
    df_depth = np.array(df["depth"].values, dtype=float)
    df_depth_rounded = abs(np.round(df_depth, 0))
    depth_values = np.array(cache_copy["depth_values"], dtype=float)
    depth_rounded = abs(np.round(depth_values, 0))
    index_map = {int(v): len(depth_rounded)-i-1 for i, v in enumerate(depth_rounded)}
    # Pre-allocate frame
    frame = np.full((len(df), abs(n_rows)), np.nan, float)
    values_filtered = arr[df.index.values, :] if is_hyd else arr[:, df.index.values]
    for i in range(abs(n_rows)):
        mask_depth = ((df['depth'].values <= -i) & (i in depth_rounded))
        row_idx = np.where(mask_depth)[0]
        if len(row_idx) > 0: frame[row_idx, i] = values_filtered[row_idx, index_map[i]]
        # Define value for max row
        if i in df_depth_rounded:
            pos_row = np.where(df_depth_rounded == i)[0]
            best_idx = np.argmax(np.where(depth_rounded <= i)[0])
            vals = values_filtered[pos_row, best_idx]
            if np.isnan(vals).any():
                temp_vals = []
                for idx, v in enumerate(vals):
                    if np.isnan(v):
                        count = best_idx + 1
                        while count <= len(depth_rounded) - 1:
                            v = values_filtered[pos_row[idx], count]
                            if not np.isnan(v): break
                            count += 1
                    temp_vals.append(v)
                temp_vals = np.array(temp_vals)
            else: temp_vals = vals
            frame[pos_row, i] = temp_vals
    frame[:, 0] = frame[:, int(depth_rounded[0])]  # Fill the first column
    # Interpolate
    mask_valid = -np.arange(abs(n_rows))[None, :] >= df_depth[:, None]
    x_idx, y_idx = np.where(~np.isnan(frame))
    if len(x_idx) > 0:
        vals = frame[x_idx, y_idx]
        # If only one point, use that value for the whole grid cell
        if not (vals.min() == vals.max()):
            grid_x, grid_y = np.indices(frame.shape)          
            # rbf = Rbf(x_idx, y_idx, vals, function='cubic')
            # frame = rbf(grid_x, grid_y)
            frame = griddata(points=np.column_stack([x_idx, y_idx]), 
                            values=vals, xi=(grid_x, grid_y), method='cubic')
        else: frame[:, :] = vals.min()
    frame[~mask_valid] = np.nan
    smoothed_transpose = frame.T
    max_row = np.max(np.where(mask_valid.T)[0])
    smoothed_transpose = smoothed_transpose[:max_row + 2, :]
    return smoothed_transpose

def seconds_datetime(seconds: int) -> tuple:
    days = seconds // 86400
    seconds %= 86400
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds = seconds % 60
    return days, f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def kill_process(process):
    if not process: return {"status": "ok", "message": "No process to kill."}
    try:
        if process.poll() is not None: return {"status": "ok", "message": "Simulation stopped."}
        # Try terminate
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)
            process.wait(timeout=5)
            return {"status": "ok", "message": "Simulation stopped (graceful)."}
        except Exception: pass
        try:
            process.terminate()
            process.wait(timeout=5)
            return {"status": "ok", "message": "Simulation terminated."}
        except Exception: pass
        # Force kill for Windows
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return {"status": "ok", "message": "Simulation force killed."}
    except Exception as e: 
        return {"status": "error", "message": str(e)}
    


# import sys, os, json, math
# sys.path.append('backend/app/')
# import xarray as xr, numpy as np, geopandas as gpd
# import pandas as pd
# from Functions import functions
# from scipy.interpolate import Rbf, griddata

# path = r'backend\Delft_Projects\demo\output\HYD\FlowFM_map.zarr'
# layer_path = r'backend\Delft_Projects\demo\output\config\layers_hyd.json'
# hyd_map = xr.open_zarr(path, consolidated=True)
# query, is_hyd = 'temp_multi_dynamic', True
# name = functions.variablesNames.get(query, query)
# values, fnm = hyd_map[name].values, functions.numberFormatter
# layer_reverse = json.load(open(layer_path))
# with open(r'points.json', 'r') as f:
#     points = json.load(f)
# depth_values = [float(v.split(' ')[1]) for k, v in layer_reverse.items() if int(k) >= 0]
# max_layer = float(max(np.array(depth_values), key=abs))
# n_rows = math.ceil(abs(max_layer)/10)*10 + 1 if max_layer < 0 else -(math.ceil(abs(max_layer)/10)*10 + 1)
# mesh_cache = { "depth_values": depth_values, "n_rows": n_rows, "df": None}
# time_column = 'time' if is_hyd else 'nTimesDlwq'
# time_stamps = pd.to_datetime(hyd_map[time_column]).strftime('%Y-%m-%d %H:%M:%S').tolist()
# points_arr, arr = np.array(points), values[-1,:,:]
# # Create GeoDataFrame for interpolation
# grid = functions.unstructuredGridCreator(hyd_map)
# x_coords, y_coords = points_arr[:, 2], points_arr[:, 1]
# gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(x_coords, y_coords), crs=grid.crs)
# gdf['depth'] = functions.interpolation_Z(gdf, hyd_map['mesh2d_node_x'].values, 
#     hyd_map['mesh2d_node_y'].values, hyd_map['mesh2d_node_z'].values)
# # Find polygons that the points are in
# gdf_filtered = gpd.sjoin(gdf, grid, how="left", predicate="intersects")
# gdf_filtered.set_index('index_right', inplace=True)
# df_serialized = gdf_filtered.drop(columns=['geometry'])
# mesh_cache["df"] = df_serialized.to_dict(orient='list')

# cache_copy = mesh_cache.copy()
# df, n_rows = pd.DataFrame(cache_copy["df"]), cache_copy["n_rows"]
# df_depth = np.array(df["depth"].values, dtype=float)
# df_depth_rounded = abs(np.round(df_depth, 0))
# depth_values = np.array(cache_copy["depth_values"], dtype=float)
# depth_rounded = abs(np.round(depth_values, 0))
# index_map = {int(v): len(depth_rounded)-i-1 for i, v in enumerate(depth_rounded)}
# # Pre-allocate frame
# frame = np.full((len(df), abs(n_rows)), np.nan, float)
# values_filtered = arr[df.index.values, :] if is_hyd else arr[:, df.index.values]
# for i in range(abs(n_rows)):
#     mask_depth = ((df['depth'].values <= -i) & (i in depth_rounded))
#     row_idx = np.where(mask_depth)[0]
#     if len(row_idx) > 0: frame[row_idx, i] = values_filtered[row_idx, index_map[i]]
#     if i in df_depth_rounded:
#         pos_row = np.where(df_depth_rounded == i)[0]
#         best_idx = np.argmax(np.where(depth_rounded <= i)[0])
#         vals = values_filtered[pos_row, best_idx]
#         print(i, pos_row, best_idx, vals)
#         if np.isnan(vals).any():
#             temp_vals = []
#             for idx, v in enumerate(vals):
#                 if np.isnan(v):
#                     count = best_idx + 1
#                     while count <= len(depth_rounded) - 1:
#                         v = values_filtered[pos_row[idx], count]
#                         if not np.isnan(v): break
#                         count += 1
#                 temp_vals.append(v)
#             print('temp_vals', temp_vals)
#             temp_vals = np.array(temp_vals)
#         else: temp_vals = vals
#         frame[pos_row, i] = temp_vals
# frame[:, 0] = frame[:, int(depth_rounded[0])]
# # Interpolate
# mask_valid = -np.arange(abs(n_rows))[None, :] >= df_depth[:, None]
# # x_idx, y_idx = np.where(~np.isnan(frame))
# # if len(x_idx) > 0:
# #     vals = frame[x_idx, y_idx]
# #     # If only one point, use that value for the whole grid cell
# #     if vals.min() == vals.max(): frame[:, :] = vals.min()
# #     else:
# #         grid_x, grid_y = np.indices(frame.shape)
# #         frame = griddata(points=np.column_stack([x_idx, y_idx]), values=vals, xi=(grid_x, grid_y), method='linear')
# # frame[~mask_valid] = np.nan

# pd.DataFrame(frame.T).to_csv('output.csv', index=False)

# [[0, 62.470850967084374, 6.420822143554688], [9.23640894386088, 62.47086907772017, 6.420997536700706], [18.472812286066265, 62.47088718834497, 6.4211729298467235], [27.709210027335093, 62.470905298958805, 6.421348322992742], [36.94560216683003, 62.47092340956165, 6.421523716138759], [46.18198870449777, 62.470941520153495, 6.421699109284776], [55.41836964057911, 62.470959630734356, 6.421874502430793], [64.65474497544844, 62.470977741304246, 6.4220498955768095], [73.89111470926336, 62.47099585186317, 6.422225288722826], [83.12747884140927, 62.47101396241111, 6.422400681868845], [92.36383737173787, 62.47103207294805, 6.422576075014862], [101.60019030027908, 62.471050183474, 6.42275146816088], [110.83653762749043, 62.47106829398898, 6.422926861306896], [120.07287935310184, 62.47108640449297, 6.423102254452914], [129.30921547735403, 62.471104514985996, 6.423277647598931], [138.54554599933255, 62.471122625468006, 6.423453040744949], [147.7818709199226, 62.471140735939045, 6.423628433890967], [157.01819023915397, 62.47115884639911, 6.423803827036984], [166.25450395657853, 62.4711769568482, 6.423979220183], [175.49081207218748, 62.47119506728629, 6.4241546133290175], [184.72711458583254, 62.47121317771339, 6.424330006475034], [193.9634114981495, 62.471231288129516, 6.424505399621053], [203.19970280847318, 62.47124939853465, 6.42468079276707], [212.43598851747802, 62.471267508928825, 6.424856185913087], [221.67226862454936, 62.471285619312006, 6.425031579059104], [230.90854312962827, 62.471303729684195, 6.425206972205122], [240.14481203343317, 62.47132184004542, 6.42538236535114], [249.38107533512718, 62.47133995039565, 6.425557758497157], [258.6173330346568, 62.471358060734886, 6.425733151643175], [267.85358513273513, 62.471376171063156, 6.42590854478919], [277.08983162900887, 62.47139428138044, 6.426083937935208], [286.32607252298527, 62.47141239168673, 6.426259331081225], [295.56230781564443, 62.47143050198205, 6.426434724227243], [304.7985375061491, 62.47144861226638, 6.426610117373261], [314.03476159504595, 62.47146672253974, 6.426785510519278], [323.27098008124244, 62.47148483280208, 6.426960903665295], [332.5071929660185, 62.471502943053466, 6.427136296811312], [341.7434002490981, 62.47152105329388, 6.427311689957329], [350.9796019300838, 62.471539163523296, 6.4274870831033475], [360.2157980088269, 62.47155727374172, 6.427662476249365], [369.4519884857852, 62.47157538394918, 6.427837869395381], [378.6881733607777, 62.47159349414565, 6.428013262541398], [387.9243526335284, 62.47161160433113, 6.428188655687416], [397.16052630449485, 62.47162971450564, 6.428364048833433], [406.39669437276234, 62.471647824669134, 6.428539441979451], [415.6328568399053, 62.47166593482169, 6.428714835125469], [424.8690137047032, 62.47168404496325, 6.428890228271485], [434.10516496723056, 62.471702155093816, 6.429065621417503], [443.3413106274282, 62.47172026521339, 6.42924101456352], [452.5774506853259, 62.471738375321976, 6.429416407709539], [461.81358514198104, 62.47175648541962, 6.4295918008555555], [471.0497139957904, 62.47177459550625, 6.429767194001573], [480.28583724763877, 62.471792705581905, 6.429942587147589], [489.5219548971734, 62.47181081564657, 6.430117980293606], [498.75806694493446, 62.47182892570027, 6.430293373439623], [507.9941733903523, 62.47184703574298, 6.4304687665856415], [517.2302742331063, 62.47186514577469, 6.430644159731659], [526.46636947426, 62.47188325579545, 6.430819552877677], [535.7024591127204, 62.4719013658052, 6.430994946023693], [544.9385431489065, 62.47191947580397, 6.431170339169711], [554.1746215823702, 62.47193758579174, 6.4313457323157275], [563.4106944140917, 62.47195569576855, 6.431521125461746], [572.6467616432336, 62.471973805734365, 6.4316965186077635], [581.8828232704258, 62.471991915689216, 6.431871911753779], [591.1188792951426, 62.472010025633075, 6.432047304899797], [600.3549297177971, 62.472028135565964, 6.432222698045814], [609.5909745378135, 62.47204624548786, 6.432398091191831], [618.827013755483, 62.47206435539877, 6.4325734843378495], [628.0630473703128, 62.47208246529868, 6.432748877483867], [637.2990753836659, 62.47210057518765, 6.432924270629884], [646.5350977938948, 62.47211868506561, 6.433099663775901], [655.7711146014568, 62.472136794932574, 6.433275056921919], [665.0071258070707, 62.472154904788574, 6.433450450067937], [674.243131409727, 62.472173014633576, 6.433625843213954], [683.4791314104888, 62.47219112446762, 6.43380123635997], [692.7151258084422, 62.472209234290666, 6.433976629505987], [701.951114604172, 62.47222734410274, 6.434152022652005], [711.1870977967579, 62.47224545390381, 6.4343274157980215], [720.4230753876968, 62.47226356369393, 6.43450280894404], [729.6590473752902, 62.472281673473034, 6.4346782020900575], [738.8950137600851, 62.47229978324115, 6.434853595236075], [748.1309745432272, 62.47231789299832, 6.435028988382092], [757.366929722897, 62.47233600274447, 6.435204381528109], [766.6028793003682, 62.47235411247966, 6.435379774674126], [775.8388232757599, 62.47237222220388, 6.435555167820144], [785.0747616475016, 62.47239033191708, 6.435730560966161], [794.3106944175618, 62.47240844161934, 6.435905954112178], [803.5466215842488, 62.47242655131059, 6.436081347258195], [812.7825431478474, 62.47244466099084, 6.436256740404213], [822.0184591098482, 62.47246277066015, 6.4364321335502295], [831.2543694683042, 62.47248088031844, 6.436607526696248], [840.4902742244443, 62.47249898996577, 6.4367829198422655], [849.7261733775653, 62.47251709960211, 6.436958312988282], [858.9620669277413, 62.47253520922745, 6.4371337061343], [868.1979548754299, 62.472553318841825, 6.437309099280317], [877.4338372210054, 62.47257142844524, 6.437484492426336], [886.6697139625976, 62.47258953803763, 6.437659885572352], [895.9055851017858, 62.47260764761906, 6.437835278718368], [905.1414506380006, 62.47262575718949, 6.438010671864386], [914.3773105718268, 62.47264386674896, 6.438186065010403], [923.6131649030333, 62.47266197629746, 6.43836145815642], [932.8490136307053, 62.472680085834945, 6.438536851302438], [942.084856755212, 62.47269819536144, 6.438712244448456], [951.3206942777878, 62.47271630487699, 6.4388876375944735], [960.5565261964799, 62.47273441438152, 6.43906303074049], [969.7923525127397, 62.47275252387509, 6.439238423886508], [979.0281732257756, 62.47277063335766, 6.439413817032524], [988.2639883363942, 62.47278874282927, 6.439589210178543], [997.4997978435429, 62.472806852289885, 6.4397646033245595], [1006.7356017476396, 62.47282496173951, 6.439939996470576], [1015.9714000490588, 62.47284307117817, 6.440115389616594], [1025.2071927472248, 62.47286118060583, 6.440290782762611], [1034.4429798427675, 62.47287929002253, 6.440466175908628], [1043.678761334428, 62.47289739942821, 6.440641569054646], [1052.9145372241237, 62.47291550882296, 6.440816962200664], [1062.1503075097748, 62.47293361820668, 6.440992355346681], [1071.386072193349, 62.47295172757946, 6.441167748492698], [1080.6218312728936, 62.472969836941225, 6.441343141638716], [1089.8575847498157, 62.47298794629202, 6.441518534784734], [1099.0933326232332, 62.47300605563183, 6.44169392793075], [1108.329074893311, 62.47302416496064, 6.441869321076767], [1117.5648115607216, 62.47304227427849, 6.442044714222784], [1126.8005426247182, 62.47306038358535, 6.442220107368802], [1136.0362680857577, 62.473078492881235, 6.442395500514818], [1145.271987942926, 62.47309660216611, 6.442570893660837], [1154.507702197796, 62.47311471144004, 6.442746286806854], [1163.7434108485052, 62.47313282070295, 6.442921679952872], [1172.97911389637, 62.4731509299549, 6.443097073098889], [1182.214811340778, 62.47316903919585, 6.443272466244906], [1191.4505031821402, 62.473187148425836, 6.443447859390923], [1200.6861894201877, 62.473205257644835, 6.44362325253694], [1209.921870055205, 62.473223366852864, 6.443798645682958], [1219.1575450866173, 62.4732414760499, 6.443974038828975], [1228.3932145144981, 62.473259585235944, 6.444149431974992], [1237.6288783389616, 62.473277694411, 6.44432482512101], [1246.8645365601192, 62.473295803575084, 6.444500218267026], [1256.100189178607, 62.47331391272821, 6.444675611413045], [1265.3358361927278, 62.47333202187031, 6.444851004559062], [1274.57147760436, 62.473350131001474, 6.445026397705079], [1283.8071134116847, 62.473368240121616, 6.445201790851097], [1293.0427436160194, 62.47338634923079, 6.445377183997114], [1302.2783682167062, 62.47340445832898, 6.445552577143133], [1311.513987213552, 62.47342256741617, 6.445727970289148], [1320.7496006079245, 62.47344067649242, 6.445903363435165], [1329.9852083974004, 62.47345878555763, 6.446078756581183], [1339.2208105845018, 62.473476894611906, 6.4462541497272], [1348.4564071676202, 62.47349500365518, 6.446429542873217], [1357.6919981477354, 62.47351311268749, 6.446604936019235], [1366.9275835240107, 62.47353122170881, 6.446780329165253], [1376.1631632963033, 62.47354933071913, 6.44695572231127], [1385.3987374648993, 62.473567439718465, 6.447131115457287], [1394.634306030389, 62.473585548706836, 6.447306508603305], [1403.869868992496, 62.47360365768424, 6.447481901749321], [1413.1054263500907, 62.473621766650616, 6.447657294895339], [1422.3409781046626, 62.47363987560604, 6.447832688041356], [1431.5765242556358, 62.473657984550485, 6.448008081187373], [1440.8120648029133, 62.473676093483945, 6.448183474333391], [1450.0475997462634, 62.47369420240641, 6.448358867479408], [1459.283129085455, 62.47371231131788, 6.448534260625425], [1468.5186528216393, 62.473730420218395, 6.448709653771443], [1477.754170953636, 62.47374852910791, 6.448885046917461], [1486.9896834822898, 62.47376663798646, 6.4490604400634775], [1496.225190406988, 62.473784746854015, 6.449235833209495], [1505.46069172836, 62.47380285571061, 6.449411226355513], [1514.6961874454846, 62.473820964556204, 6.449586619501529], [1523.9316775587815, 62.47383907339081, 6.449762012647547], [1533.167162067802, 62.473857182214424, 6.4499374057935634], [1542.4026409736548, 62.47387529102708, 6.450112798939581], [1551.638114275246, 62.47389339982873, 6.450288192085599], [1560.8735819733781, 62.47391150861942, 6.450463585231615], [1570.109044067309, 62.473929617399115, 6.450638978377634], [1579.344500557924, 62.47394772616785, 6.450814371523651], [1588.5799514437028, 62.473965834925565, 6.450989764669669], [1597.8153967257927, 62.47398394367231, 6.4511651578156854], [1607.0508364044374, 62.47400205240809, 6.451340550961703], [1616.2862704788477, 62.47402016113288, 6.45151594410772], [1625.521698949096, 62.47403826984667, 6.451691337253737], [1634.757121815812, 62.474056378549506, 6.451866730399755], [1643.9925390782491, 62.474074487241346, 6.4520421235457714], [1653.2279507369967, 62.474092595922215, 6.452217516691789], [1662.4633567914805, 62.47411070459209, 6.452392909837807], [1671.6987572418116, 62.474128813250985, 6.452568302983823], [1680.9341520877667, 62.47414692189888, 6.452743696129842], [1690.1695413305736, 62.47416503053583, 6.452919089275859], [1699.4049249684963, 62.47418313916177, 6.453094482421876], [1699.4049249684963, 62.47418313916177, 6.453094482421876], [1708.5661621840054, 62.47421448847751, 6.453261990700999], [1717.7287369555374, 62.474245837760314, 6.453429498980124], [1726.8926278359374, 62.47427718701022, 6.453597007259247], [1736.057813826758, 62.47430853622721, 6.45376451553837], [1745.2242743680736, 62.474339885411275, 6.453932023817495], [1754.3919893272728, 62.47437123456243, 6.454099532096618], [1763.5609389871129, 62.47440258368067, 6.454267040375742], [1772.7311040363263, 62.47443393276601, 6.454434548654865], [1781.9024655574704, 62.47446528181842, 6.4546020569339895], [1791.0750050197348, 62.47449663083793, 6.454769565213112], [1800.2487042659675, 62.474527979824515, 6.4549370734922356], [1809.4235455067562, 62.474559328778206, 6.455104581771359], [1818.599511307823, 62.47459067769897, 6.455272090050483], [1827.7765845840004, 62.47462202658683, 6.4554395983296065], [1836.9547485882067, 62.47465337544174, 6.45560710660873], [1846.1339869072847, 62.47468472426378, 6.455774614887853], [1855.3142834475957, 62.47471607305289, 6.455942123166977], [1864.4956224324771, 62.47474742180908, 6.456109631446101], [1873.6779883929396, 62.47477877053237, 6.456277139725224], [1882.86136615895, 62.47481011922273, 6.456444648004349], [1892.0457408543284, 62.47484146788019, 6.456612156283472], [1901.231097888112, 62.47487281650473, 6.456779664562595], [1910.4174229492548, 62.47490416509637, 6.456947172841718], [1919.6047019979328, 62.47493551365508, 6.457114681120842], [1928.792921261072, 62.47496686218087, 6.457282189399967], [1937.9820672260348, 62.47499821067376, 6.45744969767909], [1947.1721266332693, 62.475029559133745, 6.457617205958214], [1956.3630864706213, 62.47506090756081, 6.457784714237336], [1965.554933969356, 62.475092255954976, 6.457952222516461], [1974.7476565947559, 62.47512360431619, 6.458119730795584], [1983.9412420473702, 62.47515495264453, 6.458287239074708], [1993.1356782493872, 62.47518630093994, 6.458454747353831], [2002.3309533460124, 62.47521764920243, 6.458622255632956], [2011.5270556980556, 62.47524899743202, 6.458789763912079], [2020.7239738761098, 62.47528034562868, 6.458957272191202], [2029.9216966584263, 62.47531169379245, 6.459124780470327], [2039.1202130229765, 62.47534304192329, 6.45929228874945], [2048.3195121458493, 62.4753743900212, 6.459459797028574], [2057.5195833971466, 62.475405738086245, 6.459627305307697], [2066.7204163317397, 62.47543708611833, 6.4597948135868215], [2075.922000692907, 62.475468434117545, 6.459962321865944], [2085.124326400547, 62.47549978208381, 6.460129830145068], [2094.327383553857, 62.475531130017174, 6.460297338424191], [2103.5311624234546, 62.47556247791764, 6.4604648467033154], [2112.7356534477008, 62.47559382578518, 6.460632354982439], [2121.9408472310333, 62.4756251736198, 6.460799863261562], [2131.1467345403585, 62.47565652142151, 6.4609673715406855], [2140.353306299979, 62.47568786919033, 6.461134879819809], [2149.5605535881386, 62.47571921692622, 6.461302388098933], [2158.768467635428, 62.47575056462919, 6.461469896378056], [2167.9770398217715, 62.475781912299254, 6.461637404657181], [2177.186261671041, 62.475813259936416, 6.461804912936304], [2186.3961248493897, 62.47584460754066, 6.461972421215427], [2195.6066211623843, 62.475875955111974, 6.462139929494551], [2204.817742552836, 62.47590730265039, 6.462307437773674], [2214.029481095731, 62.47593865015588, 6.462474946052799], [2223.241828998174, 62.475969997628475, 6.462642454331922], [2232.45477859491, 62.47600134506817, 6.462809962611046], [2241.6683223451364, 62.47603269247494, 6.462977470890168], [2250.882452832189, 62.47606403984878, 6.463144979169293], [2260.097162760264, 62.47609538718972, 6.463312487448416], [2269.3124449503475, 62.47612673449774, 6.46347999572754], [2278.5282923411414, 62.47615808177288, 6.463647504006663], [2287.744697980866, 62.47618942901505, 6.463815012285788], [2296.961655034481, 62.476220776224366, 6.463982520564911], [2306.1791567701994, 62.476252123400734, 6.464150028844034], [2315.3971965670958, 62.4762834705442, 6.464317537123159], [2324.6157679063895, 62.476314817654746, 6.464485045402282], [2333.8348643738696, 62.47634616473239, 6.464652553681406], [2343.0544796546837, 62.47637751177713, 6.464820061960529], [2352.274607532646, 62.47640885878895, 6.4649875702396535], [2361.4952418881617, 62.476440205767844, 6.465155078518776], [2370.716376697986, 62.47647155271384, 6.4653225867979], [2379.9380060306216, 62.47650289962693, 6.465490095077024], [2389.160124044701, 62.47653424650707, 6.4656576033561475], [2398.3827249921906, 62.476565593354344, 6.465825111635271], [2407.605803208688, 62.47659694016869, 6.4659926199143944], [2416.8293531183735, 62.47662828695013, 6.4661601281935175], [2426.053369228909, 62.47665963369865, 6.466327636472641], [2435.2778461310136, 62.47669098041425, 6.466495144751765], [2444.5027784978392, 62.476722327096944, 6.466662653030888], [2453.7281610815294, 62.476753673746735, 6.466830161310013], [2462.9539887120804, 62.47678502036361, 6.466997669589136], [2472.180256297523, 62.476816366947574, 6.467165177868259], [2481.4069588205007, 62.47684771349862, 6.467332686147383], [2490.6340913378463, 62.47687906001674, 6.467500194426506], [2499.8616489810674, 62.476910406501986, 6.467667702705631], [2509.0896269491786, 62.47694175295428, 6.467835210984754], [2518.31802051609, 62.47697309937371, 6.468002719263878], [2527.546825019188, 62.47700444576017, 6.468170227543], [2536.776035869577, 62.477035792113774, 6.468337735822125], [2546.0056485391865, 62.47706713843444, 6.468505244101248], [2555.235658568059, 62.47709848472219, 6.468672752380372], [2564.4660615600483, 62.477129830977034, 6.468840260659495], [2573.6968531812586, 62.47716117719896, 6.46900776893862], [2582.9280291601644, 62.47719252338798, 6.469175277217744], [2592.159585286009, 62.477223869544105, 6.469342785496866], [2601.391517406181, 62.4772552156673, 6.469510293775991], [2610.623821427915, 62.47728656175757, 6.469677802055114], [2619.8564933171983, 62.47731790781497, 6.469845310334238], [2629.0895290926496, 62.477349253839414, 6.470012818613361], [2638.3229248336365, 62.47738059983099, 6.470180326892486], [2647.556676668815, 62.47741194578961, 6.470347835171609], [2656.790780785302, 62.47744329171536, 6.470515343450732], [2666.0252334183665, 62.477474637608154, 6.4706828517298565], [2675.2600308598326, 62.47750598346808, 6.4708503600089795], [2684.495169448397, 62.477537329295075, 6.471017868288103], [2693.7306455745597, 62.47756867508915, 6.4711853765672265], [2702.9664556783714, 62.477600020850325, 6.4713528848463495], [2712.2025962471657, 62.47763136657857, 6.4715203931254734], [2721.439063818156, 62.47766271227395, 6.471687901404597], [2730.6758549709225, 62.47769405793637, 6.47185540968372], [2739.9129663364647, 62.47772540356592, 6.472022917962845], [2749.1503945853988, 62.477756749162516, 6.472190426241968], [2758.3881364376803, 62.47778809472622, 6.472357934521091], [2767.626188654289, 62.477819440257015, 6.472525442800215], [2776.8645480403866, 62.47785078575492, 6.472692951079338], [2786.1032114418663, 62.47788213121989, 6.472860459358463], [2795.3421757470023, 62.47791347665194, 6.473027967637586], [2804.581437886167, 62.47794482205109, 6.47319547591671], [2813.82099482882, 62.477976167417346, 6.473362984195832], [2823.0608435834592, 62.47800751275067, 6.473530492474957], [2832.300981198683, 62.47803885805109, 6.473698000754081], [2841.5414047604613, 62.478070203318595, 6.473865509033204]]

