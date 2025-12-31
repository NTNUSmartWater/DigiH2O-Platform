import os, json
from config import STATIC_DIR_BACKEND
from Functions import functions
import geopandas as gpd, xarray as xr
from shapely.geometry import Point
from datetime import datetime

def hydReader(hyd_path: str) -> dict:
    """
    Read the hyd file and return a dictionary of the hyd file.

    Parameters
    ----------
    hyd_path : str
        The path to the hyd file.

    Returns
    -------
    dict
        A dictionary of the hyd file.
    """
    # Read the hyd file
    data, check, sinks = {'filename': 'FlowFM.hyd'}, False, []
    with open(hyd_path, 'r', encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        if "number-hydrodynamic-layers" in line: data['n_layers'] = line.split()[1]
        if "hydrodynamic-start-time" in line:
            temp = line.split()[1].replace("'", "")
            dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
            data['start_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        if "hydrodynamic-stop-time" in line:
            temp = line.split()[1].replace("'", "")
            dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
            data['stop_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        if "hydrodynamic-timestep" in line:
            data['time_step1'] = int(line.split()[1].replace("'", ""))
        if "conversion-timestep" in line:
            data['time_step2'] = int(line.split()[1].replace("'", ""))
        if "number-water-quality-segments-per-layer" in line:
            data['n_segments'] = int(line.split()[1])
        if "number-water-quality-layers" in line:
            data['n_layer'] = int(line.split()[1])
        if "attributes-file" in line:
            data['attr_path'] = line.split()[1].replace("'", "")
        if "volumes-file" in line:
            data['vol_path'] = line.split()[1].replace("'", "")
        if "number-horizontal-exchanges" in line:
            data['exchange_x'] = int(line.split()[1])
        if "number-vertical-exchanges" in line:
            data['exchange_z'] = int(line.split()[1])
        if "pointers-file" in line:
            data['ptr_path'] = line.split()[1].replace("'", "")
        if "areas-file" in line:
            data['area_path'] = line.split()[1].replace("'", "")
        if "flows-file" in line:
            data['flow_path'] = line.split()[1].replace("'", "")
        if "lengths-file" in line:
            data['length_path'] = line.split()[1].replace("'", "")
        if "sink-sources" in line: check = True
        if check and "sink-sources" not in line:
            temp = line.split()
            sinks.append([temp[-1], temp[-2], temp[-3]])
        if "end-sink-sources" in line: check = False
        if "horizontal-surfaces-file" in line:
            data['srf_path'] = line.split()[1].replace("'", "")
        if "vert-diffusion-file" in line:
            data['vdf_path'] = line.split()[1].replace("'", "")
        if "temperature-file" in line:
            data['tem_path'] = line.split()[1].replace("'", "")
        if "salinity-file" in line:
            data['sal_path'] = line.split()[1].replace("'", "")
    data['sink_sources'] = sinks
    if 'n_layer' in data and isinstance(data['n_layer'], int):
        data['n_segments'] = data['n_segments'] * data['n_layer']
    else: data['n_layer'] = 0
    return data
    
def segmentFinder(lat:float, lon:float, grid:gpd.GeoDataFrame) -> int:
    """
    Find the segment that the point is in.

    Parameters
    ----------
    lat : float
        The latitude of the point.
    lon : float
        The longitude of the point.
    grid : numpy.ndarray
        The grid of the segments.

    Returns
    -------
    int
        The index of the segment that the point is in.
    """
    if grid.empty: return 0
    # Convert the grid to WGS84 if not already
    if grid.crs != '4326': grid = grid.to_crs(epsg=4326)
    # Find the segment that the point is in
    pt = Point(lon, lat)
    mash = grid.contains(pt)
    polygon = grid.loc[mash]
    if polygon.empty: return 0
    idx = int(polygon.index[0])
    return idx + 1

def wqPreparation(parameters:dict, key:str, output_folder:str, includes_folder:str) -> str:
    """
    Prepare the input files for the water quality simulation

    Parameters
    ----------
    parameters : dict
        The parameters for the water quality simulation.
    key : str
        The key of the water quality model.
    output_folder : str
        The output folder for the water quality simulation.
    includes_folder : str
        The includes folder for the water quality simulation.

    Returns
    -------
    str
        The path to the config file for the water quality simulation.
    """
    try:
        inp_path = os.path.normpath(os.path.join(output_folder, f'{parameters["folder_name"]}.inp'))
        sample_path = os.path.normpath(os.path.join(STATIC_DIR_BACKEND, 'samples', 'waq'))
        params_INP, params_INC, model_type = {}, {}, {"model_type": key}
        grid_path = os.path.normpath(os.path.join(os.path.dirname(parameters['hyd_path']), 'FlowFM_waqgeom.nc'))
        data = xr.open_dataset(grid_path, chunks={'time': 1}, decode_times=False)
        grid = functions.unstructuredGridCreator(data)
        data.close()
        params_INC['t0'], params_INC['t0_scu'] = '1970.01.01 00:00:00', 1
        params_INC['B2_numsettings'] = f'{parameters["scheme"]}.70 ; integration option\n; detailed balance options'
        # Prepare for the config file B2_simtimers
        start = parameters['t_start'].strftime('%Y/%m/%d-%H:%M:%S')
        stop = parameters['t_stop'].strftime('%Y/%m/%d-%H:%M:%S')
        params_INC['B2_simtimers'] = [f"{start} ; start time", f"{stop} ; stop time", 
            f"{parameters['t_step1']} ; timestep constant", f"{parameters['t_step2']} ; timestep"
        ]
        # Prepare for the config file B2_outlocs
        obs_point = list(parameters['obs_data'])
        if len(obs_point) > 0:
            content, points = f'{len(obs_point)} ; nr of monitor locations', []
            for point in obs_point:
                segment = segmentFinder(point[1], point[2], grid)
                if segment == 0: continue
                points.append(f'{point[0]} 1\n{segment}')
            joined = '\n'.join(points)
            params_INC['B2_outlocs'] = f"{content}\n{joined}"
            model_type['wq_obs'] = obs_point
        else: params_INC['B2_outlocs'] = '0 ; nr of monitor locations'
        # Prepare for the config file B2_outputtimers
        params_INC['B2_outputtimers'] = [';  output control (see DELWAQ-manual)', ';  yyyy/mm/dd-hh:mm:ss  yyyy/mm/dd-hh:mm:ss  dddhhmmss',
            f'{start} {stop} {parameters["t_step2"]} ;  start, stop and step for balance output',
            f'{start} {stop} {parameters["t_step2"]} ;  start, stop and step for map output',
            f'{start} {stop} {parameters["t_step2"]} ;  start, stop and step for his output'
        ]
        # Prepare for the config file B3_ugrid
        ugrid_path = os.path.normpath(os.path.join(os.path.dirname(parameters['hyd_path']), 'FlowFM_waqgeom.nc'))
        temp_ugrid = ugrid_path.replace(os.sep, "/")
        params_INC['B3_ugrid'] = f"UGRID '{temp_ugrid}'"
        # Prepare for the config file B3_nrofseg
        params_INC['B3_nrofseg'] = f"{parameters['n_segments']} ; number of segments"
        # Prepare for the config file B3_attributes
        temp_attr = parameters['attr_path'].replace(os.sep, "/")
        params_INC['B3_attributes'] = f"INCLUDE '{temp_attr}' ; attributes file"
        # Prepare for the config file B3_volumes
        temp_vol = parameters['vol_path'].replace(os.sep, "/")
        params_INC['B3_volumes'] = f"-2 ; volumes will be interpolated from a binary file\n'{temp_vol}' ; volumes file from hyd file"
        # Prepare for the config file B4_nrofexch
        params_INC['B4_nrofexch'] = f"{parameters['exchange_x']} {parameters['exchange_y']} {parameters['exchange_z']} ; number of exchanges in three directions"
        # Prepare for the config file B4_pointers
        temp_ptr = parameters['ptr_path'].replace(os.sep, "/")
        params_INC['B4_pointers'] = f"0 ; pointers from binary file.\n'{temp_ptr}' ; pointers file"
        # Prepare for the config file B4_cdispersion
        params_INC['B4_cdispersion'] = "1 0.0 1E-07 ; constant dispersion"
        # Prepare for the config file B4_area
        temp_area = parameters['area_path'].replace(os.sep, "/")
        params_INC['B4_area'] = f"-2 ; areas will be interpolated from a binary file\n'{temp_area}' ; areas file"
        # Prepare for the config file B4_flows
        temp_flow = parameters['flow_path'].replace(os.sep, "/")
        params_INC['B4_flows'] = f"-2 ; flows from binary file\n'{temp_flow}' ; flows file"
        # Prepare for the config file B4_length
        temp_length = parameters['length_path'].replace(os.sep, "/")
        params_INC['B4_length'] = f"0 ; Lengths from binary file\n'{temp_length}' ; lengths file"
        # Prepare for the config file B5
        params_INC['B5_boundlist'] = [";'NodeID' 'Comment field' 'Boundary name used for data grouping'"]
        n_layers, points = int(parameters['n_layers']), parameters['sources']
        if (n_layers > 0) and (len(points) > 0):
            count = 0
            for i in range(n_layers):
                params_INC['B5_boundlist'].append(f"; Boundaries for layer {i+1}")
                for point in points:
                    count += 1
                    params_INC['B5_boundlist'].append(f"'{count}' '' '{point[0]}'")
        params_INC['B5_boundaliases'], params_INC['B5_bounddata'] = '', ''
        # Prepare for the config file B6_loads
        n_loads = parameters["loads_data"]
        if len(list(parameters["loads_data"])) > 0: model_type['wq_loads'] = list(parameters["loads_data"])
        params_INC['B6_loads'] = [f'{len(n_loads)} ; Number of loads']
        params_INC['B6_loads'].append(';SegmentID  Load-name  Comment  Load-type')
        for load in n_loads:
            segment = segmentFinder(load[1], load[2], grid)
            if segment == 0: continue
            params_INC['B6_loads'].append(f"{segment} '{load[0]}' '' ''")
        # Prepare for the config file B6_loads_aliases
        params_INC['B6_loads_aliases'] = []
        for load in n_loads:
            params_INC['B6_loads_aliases'].append(f"USEDATA_ITEM '{load[0]}' FORITEM\n'{load[0]}'")
        # Prepare for the config file B6_loads_data
        tbl_path = os.path.normpath(os.path.join(output_folder, 'includes_deltashell', 'load_data_tables', f'{parameters["folder_name"]}.tbl'))
        temp_btl = tbl_path.replace(os.sep, "/")
        params_INC['B6_loads_data'] = f"INCLUDE '{temp_btl}'"
        # Prepare for the config file B7_functions, B7_dispersion
        params_INC['B7_functions'], params_INC['B7_dispersion'] = '', ''
        # Prepare for the config file B7_parameters
        temp_srf = parameters['srf_path'].replace(os.sep, "/")
        params_INC['B7_parameters'] = f"PARAMETERS\n'Surf'\nALL\nBINARY_FILE '{temp_srf}' ; from horizontal-surfaces-file key in hyd file"
        # Prepare for the config file B7_vdiffusion
        temp_vdf = parameters['vdf_path'].replace(os.sep, "/")
        params_INC['B7_vdiffusion'] = ["CONSTANTS 'ACTIVE_VertDisp' DATA 1.0","SEG_FUNCTIONS","'VertDisper'",
                                        "ALL", f"BINARY_FILE '{temp_vdf}'"]
        # Prepare for the config file B7_numerical_options
        params_INC['B7_numerical_options'] = ["CONSTANTS 'CLOSE_ERR' DATA 1 ; If defined, allow delwaq to correct water volumes to keep concentrations continuous",
            "CONSTANTS 'NOTHREADS' DATA 2 ; Number of threads used by delwaq",
            "CONSTANTS 'DRY_THRESH' DATA 0.001 ; Dry cell threshold",
            f"CONSTANTS 'maxiter' DATA {int(parameters['maxiter'])} ; Maximum number of iterations",
            f"CONSTANTS 'tolerance' DATA {parameters['tolerance']} ; Convergence tolerance",
            "CONSTANTS 'iteration report' DATA 0 ; Write iteration report (when 1) or not (when 0)"
        ]
        # Prepare for the config file B8_initials
        params_INC['B8_initials'], init_dict = ["MASS/M2", "INITIALS"], {}
        for item in parameters['initial_set']:
            if item == '': continue
            temp = item.split(' ')
            init_dict[temp[0]] = temp[1]
        for item in parameters['initial_list']:
            params_INC['B8_initials'].append(f"'{item}'")
        params_INC['B8_initials'].append("DEFAULTS")
        for i in parameters['initial_list']:
            if i in init_dict.keys() and len(init_dict[i]) > 0: params_INC['B8_initials'].append(init_dict[i])
            else: params_INC['B8_initials'].append("0")

        # *************************** Simple oxygen model ***************************
        if key == 'simple-oxygen':
            # Get data for B1_sublist variable
            with open(os.path.normpath(os.path.join(sample_path, 'B1_simple_oxygen.inc')), 'r', encoding="utf-8") as f:
                params_INC['B1_sublist'] = f.read()
            # Prepare for the config file B7_processes
            params_INC['B7_processes'], processes = [], ['Nitrif_NH4', 'BODCOD', 'RearOXY', 'SedOXYDem', 'PosOXY',
                     'DynDepth', 'SaturOXY', 'TotDepth', 'Veloc']
            for item in processes:
                params_INC['B7_processes'].append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            # Prepare for the config file B7_constants
            params_INC['B7_constants'], constants = [], ['RcNit', 'RcBOD ', 'COXBOD', 'OOXBOD', 'CFLBOD',
                     'O2FuncBOD', 'BOD5', 'BODu', 'SWRear', 'KLRear', 'fSOD', 'RcSOD', 'VWind']
            values = ['0.1', '0.3', '1', '5', '0.3', '0', '0', '0', '1', '1', '0', '0.1', '3']
            for i in range(len(constants)):
                params_INC['B7_constants'].append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            # Prepare for the config file B7_segfunctions
            temp_tem = parameters['tem_path'].replace(os.sep, "/")
            params_INC['B7_segfunctions'] = ["SEG_FUNCTIONS", "'Temp'", "ALL", f"BINARY_FILE '{temp_tem}'"]
            # Prepare for the config file B9
            pr = ['DO']
            temp = ["2 ; perform default output and extra parameters listed below", f"{len(pr)} ; number of parameters listed"]
            params_INC['B9_Hisvar'], params_INC['B9_Mapvar'] = temp.copy(), temp.copy()
            for item in pr:
                params_INC['B9_Hisvar'].append(f"'{item}' 'volume'")
                params_INC['B9_Mapvar'].append(f"'{item}'")
        
        # *************************** Trace metals model ***************************
        elif key == 'trace-metals':
            # Get data for B1_sublist variable
            with open(os.path.normpath(os.path.join(sample_path, 'B1_trace_metals.inc')), 'r', encoding="utf-8") as f:
                params_INC['B1_sublist'] = f.read()
            # Prepare for the config file B7_processes
            params_INC['B7_processes'], processes = [], ['HydDuflow', 'Metal']
            for item in processes:
                params_INC['B7_processes'].append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            # Prepare for the config file B7_constants
            params_INC['B7_constants'], constants = [], ['aAs', 'aCu ', 'aNi', 'aPb', 'aZn', 'bAs', 'bCu', 'bNi', 'bPb', 'bZn', 
                'alfa', 'CUSulf', 'DZ1', 'DZ2', 'Ez0', 'fbx', 'fc', 'fwx', 'KAsDOC', 'KAsSS', 'KAsSSW', 'KCuDOC', 'KCuSS', 'KCuSSW',
                'KdAOC', 'KHYDW', 'KHYDB', 'KDMINW', 'KDMINB', 'KNiDOC', 'KNiSS', 'KNiSSW', 'KPbDOC', 'KPbSS', 'KPbSSW', 'KZnDOC',
                'KZnSS', 'KZnSSW', 'NIsulf', 'Pbsulf', 'POR', 'RHOANO', 'RHOORG', 'Vsp', 'Vss', 'Vsn', 'Znsulf', 'Cl', 'pHb', 'PAOC',
                'Fres', 'ASatm', 'CUatm', 'NIatm', 'Pbatm', 'Znatm']
            values = ['0', '1.25', '0', '1.176', '1.358', '0', '-5.39E-05', '0', '-6.59E-05', '-8.06E-05', '0.5', '0.003', '0.01',
                '0.09', '5E-05', '10', '0.52', '30', '1E-05', '0.003', '0.1', '0.5', '0.085', '0.05', '0.5', '0.001', '5E-05',
                '0.04', '0.015', '0.1', '0.01', '0.008', '1.02', '0.231', '0.64', '0.1', '0.02', '0.22', '0.025', '0.003', '0.8',
                '2600000', '1000000', '0.4', '1.5', '0.7', '0.01', '200', '6', '1', '20', '0','0', '0', '0', '0', '0', '0', '0', '0']
            for i in range(len(constants)):
                params_INC['B7_constants'].append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            # Prepare for the config file B7_segfunctions
            params_INC['B7_segfunctions'] = ''
            pr = ['Z', 'Q', 'As', 'dt', 'dx', 'V', 'Wf', 'Wd', 'SSB', 'FCSSW', 'FCSSB', 'FOMW', 'FSSW', 'FOMB', 'FSSB', 'RHOSSW', 'RHOSSB', 'VR', 'VS', 'FSPOC', 'EZ1',
                'EZ2', 'KASSSB', 'KCUSSB', 'KNISSB', 'KPBSSB', 'KZNSSB', 'ASWDIS', 'ASWDOC', 'ASWSS', 'ASSDIS', 'ASSDOC', 'ASSSS', 'ASREDDOC', 'ASREDSS', 'ASREDDIS',
                'ASSUBDIS', 'ASSUBDOC', 'ASSUBSS', 'CUWDIS', 'CUWDOC', 'CUWSS', 'CUSDIS', 'CUSDOC', 'CUSSS', 'CUREDDOC', 'CUREDSS', 'CUREDDIS', 'CUSUBDIS', 'CUSUBDOC',
                'CUSUBSS', 'NIWDIS', 'NIWDOC', 'NIWSS', 'NISDIS', 'NISDOC', 'NISSS', 'NIREDDOC', 'NIREDSS', 'NIREDDIS', 'NISUBDIS', 'NISUBDOC', 'NISUBSS', 'PBWDIS',
                'PBWDOC', 'PBWSS', 'PBSDIS', 'PBSDOC', 'PBSSS', 'PBREDDOC', 'PBREDSS', 'PBREDDIS', 'PBSUBDIS', 'PBSUBDOC', 'PBSUBSS', 'ZNWDIS', 'ZNWDOC', 'ZNWSS',
                'ZNSDIS', 'ZNSDOC', 'ZNSSS', 'ZNREDDOC', 'ZNREDSS', 'ZNREDDIS', 'ZNSUBDIS', 'ZNSUBDOC', 'ZNSUBSS', 'MASATM', 'MASSED', 'MASRES', 'MASDIF1', 'MASDIF2',
                'MASDIF3', 'MASPSAD1', 'MASPSAD2', 'MASPSAD3', 'MCUATM', 'MCUSED', 'MCURES', 'MCUDIF1', 'MCUDIF2', 'MCUDIF3', 'MCUPSAD1', 'MCUPSAD2', 'MCUPSAD3',
                'MNIATM', 'MNISED', 'MNIRES', 'MNIDIF1', 'MNIDIF2', 'MNIDIF3', 'MNIPSAD1', 'MNIPSAD2', 'MNIPSAD3', 'MPBATM', 'MPBSED', 'MPBRES', 'MPBDIF1', 'MPBDIF2',
                'MPBDIF3', 'MPBPSAD1', 'MPBPSAD2', 'MPBPSAD3', 'MZNATM', 'MZNSED', 'MZNRES', 'MZNDIF1', 'MZNDIF2', 'MZNDIF3', 'MZNPSAD1', 'MZNPSAD2', 'MZNPSAD3',
                'ASDISW', 'ASDISS', 'ASDISRED', 'ASSSW', 'ASSSRED', 'CUDISW', 'CUDISS', 'CUDISRED', 'CUSSW', 'CUSSRED', 'NIDISW', 'NIDISS', 'NIDISRED', 'NISSW',
                'NISSRED', 'PBDISW', 'PBDISS', 'PBDISRED', 'PBSSW', 'PBSSRED', 'ZNDISW', 'ZNDISS', 'ZNDISRED', 'ZNSSW', 'ZNSSRED']
            # Prepare for the config file B9
            temp = ["2 ; perform default output and extra parameters listed below", f"{len(pr)} ; number of parameters listed"]
            params_INC['B9_Hisvar'], params_INC['B9_Mapvar'] = temp.copy(), temp.copy()
            for item in pr:
                params_INC['B9_Hisvar'].append(f"'{item}' 'volume'")
                params_INC['B9_Mapvar'].append(f"'{item}'")
        elif key == 'oxygen-bod-water':
            # Get data for B1_sublist variable
            with open(os.path.normpath(os.path.join(sample_path, 'B1_bod_water.inc')), 'r', encoding="utf-8") as f:
                params_INC['B1_sublist'] = f.read()
            # Prepare for the config file B7_processes
            params_INC['B7_processes'], processes = [], ['RearOXY', 'BODCOD', 'DynDepth', 'SaturOXY', 'TotDepth', 'Veloc']
            for item in processes:
                params_INC['B7_processes'].append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            # Prepare for the config file B7_constants
            params_INC['B7_constants'], constants = [], ['VWind', 'SWRear', 'KLRear', 'RcBOD', 'Phyt']
            values = ['3', '1', '1', '0.3', '0']
            for i in range(len(constants)):
                params_INC['B7_constants'].append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            # Prepare for the config file B7_segfunctions
            content1, params_INC['B7_segfunctions'] = ['Salinity', 'Temp'], []
            content2 = [parameters['sal_path'].replace(os.sep, "/"), parameters['tem_path'].replace(os.sep, "/")]
            for i in range(len(content1)):
                params_INC['B7_segfunctions'].append(f"SEG_FUNCTIONS\n'{content1[i]}'\nALL\nBINARY_FILE '{content2[i]}'")
            # Prepare for the config file B9
            pr = ['SaturOXY', 'SatPercOXY', 'BOD5']
            temp = ["2 ; perform default output and extra parameters listed below", f"{len(pr)} ; number of parameters listed"]
            params_INC['B9_Hisvar'], params_INC['B9_Mapvar'] = temp.copy(), temp.copy()
            for item in pr:
                params_INC['B9_Hisvar'].append(f"'{item}' 'volume'")
                params_INC['B9_Mapvar'].append(f"'{item}'")
        elif key == 'cadmium':
            # Get data for B1_sublist variable
            with open(os.path.normpath(os.path.join(sample_path, 'B1_cadmium.inc')), 'r', encoding="utf-8") as f:
                params_INC['B1_sublist'] = f.read()
            # Prepare for the config file B7_processes
            params_INC['B7_processes'], processes = [], ['Compos', 'Sed_IM1', 'S12TraIM1', 'S1_Comp', 'Sed_Cd', 'S12TraCd', 'CalTau', 'DynDepth',
                                                         'Res_DM', 'PartWK_Cd', 'PartS1_Cd', 'Veloc', 'Chezy', 'TotDepth']
            for item in processes:
                params_INC['B7_processes'].append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            # Prepare for the config file B7_constants
            params_INC['B7_constants'], constants = [], ['TaucSIM1', 'ZResDM', 'TaucRS1DM']
            values = ['0.1', '0', '0.2']
            for i in range(len(constants)):
                params_INC['B7_constants'].append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            # Prepare for the config file B7_segfunctions
            params_INC['B7_segfunctions'] = ''
            # Prepare for the config file B9
            pr = []
            temp = ["2 ; perform default output and extra parameters listed below", f"{len(pr)} ; number of parameters listed"]
            params_INC['B9_Hisvar'], params_INC['B9_Mapvar'] = temp.copy(), temp.copy()
            for item in pr:
                params_INC['B9_Hisvar'].append(f"'{item}' 'volume'")
                params_INC['B9_Mapvar'].append(f"'{item}'")
        elif key == 'eutrophication':
            # Get data for B1_sublist variable
            with open(os.path.normpath(os.path.join(sample_path, 'B1_eu_1a.inc')), 'r', encoding="utf-8") as f:
                params_INC['B1_sublist'] = f.read()
            # Prepare for the config file B7_processes
            params_INC['B7_processes'], processes = [], ['HydDuflow', 'Eutr1a']
            for item in processes:
                params_INC['B7_processes'].append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            # Prepare for the config file B7_constants
            params_INC['B7_constants'], constants = [], ['UMAX', 'ALFA', 'IOPT', 'PIOPT', 'ACA', 'KLOSS', 'KMIN', 'KNIT', 'KDEN',
                'KP', 'KN', 'EPS0', 'EPSALG', 'THGA', 'THMIN', 'THNIT', 'THDEN', 'VSO', 'ANC', 'APC', 'ISOM', 'L', 'T', 'NFLUX', 'PFLUX']
            values = ['1', '0.02', '40', '1', '30', '0.1', '0.1', '0.2', '0.05', '0.005', '0.01', '2', '0.016', '1.04', '1.04', '1.06', '1.06',
                      '1', '0.176', '0.024', '100', '12', '20', '0', '0']
            for i in range(len(constants)):
                params_INC['B7_constants'].append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            # Prepare for the config file B7_segfunctions
            params_INC['B7_segfunctions'] = ''
            # Prepare for the config file B9
            pr = ['Z', 'Q', 'As', 'dt', 'dx', 'V', 'Wf', 'Wd', 'FT', 'FN', 'IOMAX', 'CHLA', 'ETOT', 'H1', 'fl2', 'f', 'ALFA1', 'GA',
                  'KMINT', 'KNITT', 'KDENT', 'KJN', 'NTOT', 'PTOT']
            temp = ["2 ; perform default output and extra parameters listed below", f"{len(pr)} ; number of parameters listed"]
            params_INC['B9_Hisvar'], params_INC['B9_Mapvar'] = temp.copy(), temp.copy()
            for item in pr:
                params_INC['B9_Hisvar'].append(f"'{item}' 'volume'")
                params_INC['B9_Mapvar'].append(f"'{item}'")
        elif key == 'conservative-tracers':
            # Get data for B1_sublist variable
            with open(os.path.normpath(os.path.join(sample_path, 'B1_conservative.inc')), 'r', encoding="utf-8") as f:
                params_INC['B1_sublist'] = f.read()
            # Prepare for the config file B7_processes
            params_INC['B7_processes'], processes = [], ['Age1', 'Age2', 'Age3']
            for item in processes:
                params_INC['B7_processes'].append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            # Prepare for the config file B7_constants
            params_INC['B7_constants'], constants = [], ['RcDecTR1', 'RcDecTR3']
            values = ['0.01', '0.01']
            for i in range(len(constants)):
                params_INC['B7_constants'].append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            # Prepare for the config file B7_segfunctions
            params_INC['B7_segfunctions'] = ''
            # Prepare for the config file B9
            pr = []
            temp = ["2 ; perform default output and extra parameters listed below", f"{len(pr)} ; number of parameters listed"]
            params_INC['B9_Hisvar'], params_INC['B9_Mapvar'] = temp.copy(), temp.copy()
            for item in pr:
                params_INC['B9_Hisvar'].append(f"'{item}' 'volume'")
                params_INC['B9_Mapvar'].append(f"'{item}'")
        elif key == 'suspend-sediment':
            # Get data for B1_sublist variable
            with open(os.path.normpath(os.path.join(sample_path, 'B1_suspend_sediment.inc')), 'r', encoding="utf-8") as f:
                params_INC['B1_sublist'] = f.read()
            # Prepare for the config file B7_processes
            params_INC['B7_processes'], processes = [], ['Compos', 'Sed_IM1', 'S12TraIM1', 'S1_Comp', 'Sed_IM2',
                    'S12TraIM2', 'Sed_IM3', 'S12TraIM3', 'CalTau', 'DynDepth', 'Res_DM', 'Veloc', 'Chezy', 'TotDepth']
            for item in processes:
                params_INC['B7_processes'].append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            # Prepare for the config file B7_constants
            params_INC['B7_constants'], constants = [], ['VSedIM1', 'TaucSIM1', 'VSedIM2', 'TaucSIM2', 'VSedIM3', 'TaucSIM3', 'TaucRS1DM']
            values = ['0.1', '0.1', '0.1', '0.1', '0.1', '0.1', '0.2']
            for i in range(len(constants)):
                params_INC['B7_constants'].append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            # Prepare for the config file B7_segfunctions
            params_INC['B7_segfunctions'] = ''
            # Prepare for the config file B9
            pr = []
            temp = ["2 ; perform default output and extra parameters listed below", f"{len(pr)} ; number of parameters listed"]
            params_INC['B9_Hisvar'], params_INC['B9_Mapvar'] = temp.copy(), temp.copy()
            for item in pr:
                params_INC['B9_Hisvar'].append(f"'{item}' 'volume'")
                params_INC['B9_Mapvar'].append(f"'{item}'")
        elif key == 'coliform':
            # Get data for B1_sublist variable
            with open(os.path.normpath(os.path.join(sample_path, 'B1_coliform.inc')), 'r', encoding="utf-8") as f:
                params_INC['B1_sublist'] = f.read()
            # Prepare for the config file B7_processes
            params_INC['B7_processes'], processes = [], ['EColiMrt', 'Salinchlor', 'CalcRadDay', 'DynDepth']
            for item in processes:
                params_INC['B7_processes'].append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            # Prepare for the config file B7_constants
            params_INC['B7_constants'], constants = [], ['RcMrtEColi', 'DayL', 'ExtVl', 'DayRadSurf']
            values = ['0.8', '0.58', '1', '-999']
            for i in range(len(constants)):
                params_INC['B7_constants'].append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            # Prepare for the config file B7_segfunctions
            temp_tem = parameters['tem_path'].replace(os.sep, "/")
            params_INC['B7_segfunctions'] = [f"SEG_FUNCTIONS\n'Temp'\nALL\nBINARY_FILE '{temp_tem}'"]
            # Prepare for the config file B9
            pr = []
            temp = ["2 ; perform default output and extra parameters listed below", f"{len(pr)} ; number of parameters listed"]
            params_INC['B9_Hisvar'], params_INC['B9_Mapvar'] = temp.copy(), temp.copy()
            for item in pr:
                params_INC['B9_Hisvar'].append(f"'{item}' 'volume'")
                params_INC['B9_Mapvar'].append(f"'{item}'")

        # Write .inc files
        # ######################## Block 1 ########################
        # Write file B1_t0.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B1_t0.inc')), 'w', encoding='utf-8') as f:
            f.write(f"'T0: {params_INC['t0']}  (scu= {params_INC['t0_scu']:7d}s)'")
        # Write file B1_sublist.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B1_sublist.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B1_sublist'])
        
        # ######################## Block 2 ########################
        # Write file B2_numsettings.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B2_numsettings.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B2_numsettings'])
        # Write file B2_simtimers.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B2_simtimers.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B2_simtimers']))
        # Write file B2_outlocs.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B2_outlocs.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B2_outlocs'])
        # Write file B2_outputtimers.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B2_outputtimers.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B2_outputtimers']))
        
        # ######################## Block 3 ########################
        # Write file B3_ugrid.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B3_ugrid.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B3_ugrid'])
        # Write file B3_nrofseg.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B3_nrofseg.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B3_nrofseg'])
        # Write file B3_attributes.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B3_attributes.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B3_attributes'])
        # Write file B3_volumes.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B3_volumes.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B3_volumes'])

        # ######################## Block 4 ########################
        # Write file B4_nrofexch.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B4_nrofexch.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B4_nrofexch'])
        # Write file B4_pointers.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B4_pointers.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B4_pointers'])
        # Write file B4_cdispersion.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B4_cdispersion.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B4_cdispersion'])
        # Write file B4_area.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B4_area.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B4_area'])
        # Write file B4_flows.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B4_flows.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B4_flows'])
        # Write file B4_length.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B4_length.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B4_length'])

        # ######################## Block 5 ########################
        # Write file B5_boundlist.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B5_boundlist.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B5_boundlist']))
        # Write file B5_boundaliases.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B5_boundaliases.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B5_boundaliases'])
        # Write file B5_bounddata.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B5_bounddata.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B5_bounddata'])
        
        # ######################## Block 6 ########################
        # Write file B6_loads.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B6_loads.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B6_loads']))
        # Write file B6_loads_aliases.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B6_loads_aliases.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B6_loads_aliases']))
        # Write file B6_loads_data.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B6_loads_data.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B6_loads_data'])

        # ######################## Block 7 ########################
        # Write file B7_processes.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B7_processes.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B7_processes']))
        # Write file B7_constants.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B7_constants.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B7_constants']))
        # Write file B7_functions.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B7_functions.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B7_functions'])
        # Write file B7_parameters.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B7_parameters.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B7_parameters'])
        # Write file B7_dispersion.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B7_dispersion.inc')), 'w', encoding='utf-8') as f:
            f.write(params_INC['B7_dispersion'])
        # Write file B7_vdiffusion.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B7_vdiffusion.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B7_vdiffusion']))
        # Write file B7_segfunctions.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B7_segfunctions.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B7_segfunctions']))
        # Write file B7_numerical_options.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B7_numerical_options.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B7_numerical_options']))

        # ######################## Block 8 ########################
        # Write file B8_initials.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B8_initials.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B8_initials']))

        # ######################## Block 9 ########################
        # Write file B9_Hisvar.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B9_Hisvar.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B9_Hisvar']))
        # Write file B9_Mapvar.inc
        with open(os.path.normpath(os.path.join(includes_folder, 'B9_Mapvar.inc')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(params_INC['B9_Mapvar']))

        # Write file .inp
        time_step = int(86400/params_INC['t0_scu'])
        params_INP['time_step'] = time_step
        # Open the file and read its contents
        with open(os.path.normpath(os.path.join(sample_path, 'INPFile.inp')), 'r', encoding='utf-8') as file:
            content_inp = file.read()
        # Write file to store model type
        with open(os.path.normpath(os.path.join(output_folder, f'{parameters["folder_name"]}.json')), 'w', encoding='utf-8') as f:
            json.dump(model_type, f, indent=4)
        # Replace placeholders with actual values
        for key, value in params_INP.items():
            content_inp = content_inp.replace(f'{{{key}}}', str(value))
        with open(inp_path, 'w', encoding='utf-8') as f:
            f.write(content_inp)
        return inp_path
    except Exception as e: return None, str(e)