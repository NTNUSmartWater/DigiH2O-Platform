import os
from config import ROOT_DIR
from Functions import functions
import xarray as xr
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
    with open(hyd_path, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if "number-hydrodynamic-layers" in line: data['n_layers'] = line.split()[1]
        if "reference-time" in line:
            temp = line.split()[1].replace("'", "")
            dt = datetime.strptime(temp, '%Y%m%d%H%M%S')
            data['ref_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
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
            data['parameters_path'] = line.split()[1].replace("'", "")
        if "vert-diffusion-file" in line:
            data['vdf_path'] = line.split()[1].replace("'", "")
        if "temperature-file" in line:
            data['tem_path'] = line.split()[1].replace("'", "")

    data['sink_sources'] = sinks
    if 'n_layer' in data and isinstance(data['n_layer'], int):
        data['n_segments'] = data['n_segments'] * data['n_layer']
    else: data['n_layer'] = 0
    return data
    
def segmentFinder(lat:float, lon:float, grid:xr.Dataset) -> int:
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
    # Convert the grid to WGS84 if not already
    if grid.crs != '4326': grid = grid.to_crs(epsg=4326)
    # Find the segment that the point is in
    pt = Point(lon, lat)
    mash = grid.contains(pt)
    polygon = grid.loc[mash]
    if polygon.empty: return 0
    idx = int(polygon.index[0])
    return idx + 1

def wqPreparation(parameters, key, output_folder, includes_folder) -> str:
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
        inp_path = os.path.join(output_folder, f'{parameters["folder_name"]}.inp')
        sample_path = os.path.join(ROOT_DIR, 'static', 'samples')
        params = {}
        if key == 'simple-oxygen':
            path = os.path.join(sample_path, 'simple_oxygen')
            grid_path = os.path.join(os.path.dirname(parameters['hyd_path']), 'FlowFM_waqgeom.nc')
            grid = functions.unstructuredGridCreator(xr.open_dataset(grid_path))
            
            ######################## Block 1 ########################
            # Write file B1_t0.inc
            t0, t0_scu = parameters['t_ref'].strftime('%Y.%m.%d %H:%M:%S'), 1
            with open(os.path.join(includes_folder, 'B1_t0.inc'), 'w', encoding='ascii') as f:
                f.write(f"'T0: {t0}  (scu= {t0_scu:7d}s)'")
            # Write file B1_sublist.inc
            with open(os.path.join(path, 'B1.inc'), 'r') as f:
                content = f.read()
            with open(os.path.join(includes_folder, 'B1_sublist.inc'), 'w', encoding='ascii') as f:
                f.write(content)
            
            ######################## Block 2 ########################
            # Write file B2_numsettings.inc
            with open(os.path.join(includes_folder, 'B2_numsettings.inc'), 'w', encoding='ascii') as f:
                f.write('15.70 ; integration option\n; detailed balance options')
            # Write file B2_simtimers.inc
            start = parameters['t_start'].strftime('%Y/%m/%d-%H:%M:%S')
            stop = parameters['t_stop'].strftime('%Y/%m/%d-%H:%M:%S')
            content = [f"{start} ; start time", f"{stop} ; stop time", 
                f"{parameters['t_step1']} ; timestep constant", f"{parameters['t_step2']} ; timestep"
            ]
            with open(os.path.join(includes_folder, 'B2_simtimers.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B2_outlocs.inc
            obs_point = list(parameters['obs_data'])
            if len(obs_point) > 0:
                content, points = f'{len(obs_point)} ; nr of monitor locations', []
                for point in obs_point:
                    segment = segmentFinder(point[1], point[2], grid)
                    if segment == 0: continue
                    points.append(f'{point[0]} 1\n{segment}')
                with open(os.path.join(includes_folder, 'B2_outlocs.inc'), 'w', encoding='ascii') as f:
                    f.write(f"{content}\n{'\n'.join(points)}")
            else:
                with open(os.path.join(includes_folder, 'B2_outlocs.inc'), 'w', encoding='ascii') as f:
                    f.write('0 ; nr of monitor locations')
            # Write file B2_outputtimers.inc
            content = [';  output control (see DELWAQ-manual)', ';  yyyy/mm/dd-hh:mm:ss  yyyy/mm/dd-hh:mm:ss  dddhhmmss',
                f'{start} {stop} {parameters["t_step2"]} ;  start, stop and step for balance output',
                f'{start} {stop} {parameters["t_step2"]} ;  start, stop and step for map output',
                f'{start} {stop} {parameters["t_step2"]} ;  start, stop and step for his output'
            ]
            with open(os.path.join(includes_folder, 'B2_outputtimers.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))

            ######################## Block 3 ########################
            # Write file B3_ugrid.inc
            ugrid_path = os.path.join(os.path.dirname(parameters['hyd_path']), 'FlowFM_waqgeom.nc')
            with open(os.path.join(includes_folder, 'B3_ugrid.inc'), 'w', encoding='ascii') as f:
                f.write(f"UGRID '{ugrid_path.replace("\\", "/")}'")
            # Write file B3_nrofseg.inc
            with open(os.path.join(includes_folder, 'B3_nrofseg.inc'), 'w', encoding='ascii') as f:
                f.write(f"{parameters['n_segments']} ; number of segments")
            # Write file B3_attributes.inc
            with open(os.path.join(includes_folder, 'B3_attributes.inc'), 'w', encoding='ascii') as f:
                f.write(f"INCLUDE '{parameters['attr_path'].replace("\\", "/")}' ; attributes file")
            # Write file B3_volumes.inc
            with open(os.path.join(includes_folder, 'B3_volumes.inc'), 'w', encoding='ascii') as f:
                f.write(f"-2 ; volumes will be interpolated from a binary file\n'{parameters['vol_path'].replace("\\", "/")}' ; volumes file from hyd file")

            ######################## Block 4 ########################
            # Write file B4_nrofexch.inc
            with open(os.path.join(includes_folder, 'B4_nrofexch.inc'), 'w', encoding='ascii') as f:
                f.write(f"{parameters['exchange_x']} {parameters['exchange_y']} {parameters['exchange_z']} ; number of exchanges in three directions")
            # Write file B4_pointers.inc
            with open(os.path.join(includes_folder, 'B4_pointers.inc'), 'w', encoding='ascii') as f:
                f.write(f"0 ; pointers from binary file.\n'{parameters['ptr_path'].replace("\\", "/")}' ; pointers file")
            # Write file B4_cdispersion.inc
            with open(os.path.join(includes_folder, 'B4_cdispersion.inc'), 'w', encoding='ascii') as f:
                f.write("1 0.0 1E-07 ; constant dispersion")
            # Write file B4_area.inc
            with open(os.path.join(includes_folder, 'B4_area.inc'), 'w', encoding='ascii') as f:
                f.write(f"-2 ; areas will be interpolated from a binary file\n'{parameters['area_path'].replace("\\", "/")}' ; areas file")
            # Write file B4_flows.inc
            with open(os.path.join(includes_folder, 'B4_flows.inc'), 'w', encoding='ascii') as f:
                f.write(f"-2 ; flows from binary file\n'{parameters['flow_path'].replace("\\", "/")}' ; flows file")
            # Write file B4_length.inc
            with open(os.path.join(includes_folder, 'B4_length.inc'), 'w', encoding='ascii') as f:
                f.write(f"0 ; Lengths from binary file\n'{parameters['length_path'].replace("\\", "/")}' ; lengths file")

            ######################## Block 5 ########################
            # Write file B5_boundlist.inc
            content = [";'NodeID' 'Comment field' 'Boundary name used for data grouping'"]
            n_layers, points = int(parameters['n_layers']), parameters['sources']
            if (n_layers > 0) and (len(points) > 0):
                count = 0
                for i in range(n_layers):
                    content.append(f"; Boundaries for layer {i+1}")
                    for point in points:
                        count += 1
                        content.append(f"'{count}' '' '{point[0]}'")
            with open(os.path.join(includes_folder, 'B5_boundlist.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B5_boundaliases.inc
            with open(os.path.join(includes_folder, 'B5_boundaliases.inc'), 'w', encoding='ascii') as f:
                f.write('\n')
            # Write file B5_bounddata.inc
            with open(os.path.join(includes_folder, 'B5_bounddata.inc'), 'w', encoding='ascii') as f:
                f.write('\n')
            
            ######################## Block 6 ########################
            # Write file B6_loads.inc
            n_loads = parameters["loads_data"]
            content = [f'{len(n_loads)} ; number of loads']
            content.append(';SegmentID  Load-name  Comment  Load-type')
            for load in n_loads:
                segment = segmentFinder(load[1], load[2], grid)
                if segment == 0: continue
                content.append(f"{segment} '{load[0]}' '' ''")
            with open(os.path.join(includes_folder, 'B6_loads.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B6_loads_aliases.inc
            content = []
            for load in n_loads:
                content.append(f"USEDATA_ITEM '{load[0]}' FORITEM\n'{load[0]}'")
            with open(os.path.join(includes_folder, 'B6_loads_aliases.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B6_loads_data.inc
            tbl_path = f'includes_deltashell/load_data_tables/{parameters["folder_name"]}.tbl'
            with open(os.path.join(includes_folder, 'B6_loads_data.inc'), 'w', encoding='ascii') as f:
                f.write(f"INCLUDE '{tbl_path}'")

            ######################## Block 7 ########################
            # Write file B7_processes.inc
            content, processes = [], ['Nitrif_NH4', 'BODCOD', 'RearOXY', 'SedOXYDem', 'PosOXY',
                         'DynDepth', 'SaturOXY', 'TotDepth', 'Veloc']
            for item in processes:
                content.append(f"CONSTANTS 'ACTIVE_{item}' DATA 0")
            with open(os.path.join(includes_folder, 'B7_processes.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B7_constants.inc
            content, constants = [], ['RcNit', 'RcBOD ', 'COXBOD', 'OOXBOD', 'CFLBOD',
                         'O2FuncBOD', 'BOD5', 'BODu', 'SWRear', 'KLRear', 'fSOD', 'RcSOD', 'VWind']
            values = [0.1, 0.3, 1, 5, 0.3, 0, 0, 0, 1, 1, 0, 0.1, 3]
            for i in range(len(constants)):
                content.append(f"CONSTANTS '{constants[i]}' DATA {values[i]}")
            with open(os.path.join(includes_folder, 'B7_constants.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B7_functions.inc
            with open(os.path.join(includes_folder, 'B7_functions.inc'), 'w', encoding='ascii') as f:
                f.write('\n')
            # Write file B7_parameters.inc
            with open(os.path.join(includes_folder, 'B7_parameters.inc'), 'w', encoding='ascii') as f:
                f.write(f"PARAMETERS\n'Surf'\nALL\nBINARY_FILE '{parameters['parameters_path'].replace("\\", "/")}' ; from horizontal-surfaces-file key in hyd file")
            # Write file B7_dispersion.inc
            with open(os.path.join(includes_folder, 'B7_dispersion.inc'), 'w', encoding='ascii') as f:
                f.write('\n')
            # Write file B7_vdiffusion.inc
            content = ["CONSTANTS 'ACTIVE_VertDisp' DATA 1.0","SEG_FUNCTIONS","'VertDisper'",
                       "ALL", f"BINARY_FILE '{parameters['vdf_path'].replace("\\", "/")}'"]
            with open(os.path.join(includes_folder, 'B7_vdiffusion.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B7_segfunctions.inc
            content = ["SEG_FUNCTIONS", "'Temp'", "ALL", f"BINARY_FILE '{parameters['tem_path'].replace("\\", "/")}'"]
            with open(os.path.join(includes_folder, 'B7_segfunctions.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B7_numerical_options.inc
            content = ["CONSTANTS 'CLOSE_ERR' DATA 1 ; If defined, allow delwaq to correct water volumes to keep concentrations continuous",
                "CONSTANTS 'NOTHREADS' DATA 2 ; Number of threads used by delwaq",
                "CONSTANTS 'DRY_THRESH' DATA 0.001 ; Dry cell threshold",
                "CONSTANTS 'maxiter' DATA 100 ; Maximum number of iterations",
                "CONSTANTS 'tolerance' DATA 1E-07 ; Convergence tolerance",
                "CONSTANTS 'iteration report' DATA 0 ; Write iteration report (when 1) or not (when 0)"
            ]
            with open(os.path.join(includes_folder, 'B7_numerical_options.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))

            ######################## Block 8 ########################
            # Write file B8_initials.inc
            content, init_dict = ["MASS/M2", "INITIALS"], {}
            for item in parameters['initial_set']:
                if item == '': continue
                temp = item.split(' ')
                init_dict[temp[0]] = temp[1]
            for item in parameters['initial_list']:
                content.append(f"'{item}'")
            content.append("DEFAULTS")
            for i in parameters['initial_list']:
                if i in init_dict.keys() and len(init_dict[i]) > 0: content.append(init_dict[i])
                else: content.append("0")
            with open(os.path.join(includes_folder, 'B8_initials.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))

            ######################## Block 9 ########################
            # Write file B9_Hisvar.inc
            content = ["2 ; perform default output and extra parameters listed below",
                "1 ; number of parameters listed", "'DO' 'volume'"
            ]
            with open(os.path.join(includes_folder, 'B9_Hisvar.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))
            # Write file B9_Mapvar.inc
            content = ["2 ; perform default output and extra parameters listed below",
                "1 ; number of parameters listed", "'DO'"
            ]
            with open(os.path.join(includes_folder, 'B9_Mapvar.inc'), 'w', encoding='ascii') as f:
                f.write('\n'.join(content))

            # Write file .inp
            time_step = int(86400/t0_scu)
            params['time_step'] = time_step
            # Open the file and read its contents
            with open(os.path.join(path, 'INPFile.inp'), 'r') as file:
                content_inp = file.read()
            # Replace placeholders with actual values
            for key, value in params.items():
                content_inp = content_inp.replace(f'{{{key}}}', str(value))
            with open(inp_path, 'w', encoding='ascii') as f:
                f.write(content_inp)
        # elif key == 'oxygen-bod-water':
        #     path = os.path.join(sample_path, 'oxygen_bod_water')
        
        # elif key == 'cadmium':
        #     path = os.path.join(sample_path, 'cadmium')

        # elif key == 'eutrophication':
        #     path = os.path.join(sample_path, 'eutrophication')

        # elif key == 'tracer-metals':
        #     path = os.path.join(sample_path, 'tracer_metals')

        # elif key == 'conservative-tracers':
        #     path = os.path.join(sample_path, 'conservative_tracers')

        # elif key == 'suspend-sediment':
        #     path = os.path.join(sample_path, 'suspend_sediment')

        # elif key == 'coliform':
        #     path = os.path.join(sample_path, 'coliform')
        
        
        
        return inp_path, ''
    except Exception as e:
        return None, str(e)