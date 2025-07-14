import shapely, json
from netCDF4 import Dataset, num2date
import geopandas as gpd
import pandas as pd
import numpy as np
import pyvista as pv
from datetime import datetime
from scipy.spatial import cKDTree


CENTER, ZOOM = [62.47541795739599, 6.464416589996501], 13

class Delft3D:
    def __init__(self, his_nc, map_nc, dialog_file):
        self.x, self.y, self.z = False, False, False
        if not his_nc.endswith('.nc') or not map_nc.endswith('.nc'):
            raise ValueError("Both his_nc and map_nc must be NetCDF files with .nc extension.")
        self.his_data = Dataset(his_nc)
        self.map_data = Dataset(map_nc)
        self.read_his()
        self.read_map()
        self.unstructured_grid()
        self.read_dialog(dialog_file)
        # Compute depth
        if self.x and self.y and self.z:
            df = self.unstructured_grid.copy()
            df['value'] = interpolation_Z(df, self.mesh2d_node_x, self.mesh2d_node_y, self.mesh2d_node_z)
            self.depth = df

    def read_dialog(self, dialog_file):
        data = {}
        with open(f'{dialog_file}', 'r') as f:
            content = f.read()
        content = content.split('\n')
        for line in content:
            if "Computation started" in line:
                temp = pd.to_datetime(line.split(': ')[2], format='%H:%M:%S, %d-%m-%Y')
                data["computation_start"] = temp.strftime('%Y-%m-%d %H:%M:%S')
            if "Computation finished" in line:
                temp = pd.to_datetime(line.split(': ')[2], format='%H:%M:%S, %d-%m-%Y')
                data["computation_finish"] = temp.strftime('%Y-%m-%d %H:%M:%S')
            if "my model area" in line:
                temp = line.split(': ')[2]
                data["area"] = float(temp.strip())
            if "my model volume" in line:
                temp = line.split(': ')[2]
                data["volume"] = float(temp.strip())
        self.dialog = data

    def read_his(self):
        his_data = self.his_data
        # Get values
        self.his_dimensions = {key: his_data.dimensions[key].size for key in his_data.dimensions}
        his_variables = {key: his_data.variables[key] for key in his_data.variables}
        self.his_variables = his_variables
        self.his_date_created, self.his_date_modified = pd.to_datetime(his_data.date_created, utc=True), pd.to_datetime(his_data.date_modified, utc=True)
        self.his_time_start, self.his_time_end = pd.to_datetime(his_data.time_coverage_start.replace('*', '0'), utc=True), pd.to_datetime(his_data.time_coverage_end.replace('*', '0'), utc=True)
        self.his_time_duration, self.his_time_resolution = his_data.time_coverage_duration, his_data.time_coverage_resolution
        # Get time stamps
        time_var = his_data.variables['time']
        time_values = num2date(time_var[:], units=time_var.units, calendar=getattr(time_var, 'calendar', 'standard'))
        datetime_list = [datetime(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in time_values[:].data]
        self.his_timestamps = pd.to_datetime(datetime_list, utc=True)
        # Get the coordinates and names of the stations
        if 'station_name' in his_variables.keys():
            stations = {}
            for i in range(len(his_variables['station_name'][:])):
                name = b"".join(char for char in his_variables['station_name'][i]).decode('utf-8').strip()
                id_ = b"".join(char for char in his_variables['station_id'][i]).decode('utf-8').strip()
                x = float(his_variables['station_x_coordinate'][i].data)
                y = float(his_variables['station_y_coordinate'][i].data)
                stations[id_] = {'id': id_, 'name': name, 'x': x, 'y': y}
            self.stations = gpd.GeoDataFrame(stations.values(), crs='EPSG:4326',
                geometry=gpd.points_from_xy([s['x'] for s in stations.values()], [s['y'] for s in stations.values()])).drop(columns=['x', 'y'])
        # Get name of the cross section
        if 'cross_section_name' in his_variables.keys():
            cross_section = {}
            for i in range(len(his_variables['cross_section_name'][:])):
                name = b"".join(char for char in his_variables['cross_section_name'][i]).decode('utf-8').strip()
                x = float(his_variables['cross_section_geom_node_coordx'][i].data)
                y = float(his_variables['cross_section_geom_node_coordy'][i].data)
                cross_section[name] = {'name': name, 'x': x, 'y': y}
            self.cross_section = gpd.GeoDataFrame(cross_section.values(), crs='EPSG:4326',
                geometry=gpd.points_from_xy([s['x'] for s in cross_section.values()], [s['y'] for s in cross_section.values()])).drop(columns=['x', 'y'])
        if len(self.cross_section) > 0:
            # Get cross section discharges
            if 'cross_section_discharge' in his_variables.keys(): 
                self.cross_section_discharges = pd.DataFrame(his_variables['cross_section_discharge'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section cumulative discharges
            if 'cross_section_cumulative_discharge' in his_variables.keys(): 
                self.cross_section_cumulative_discharge = pd.DataFrame(his_variables['cross_section_cumulative_discharge'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section areas
            if 'cross_section_area' in his_variables.keys(): 
                self.cross_section_area = pd.DataFrame(his_variables['cross_section_area'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section velocities
            if 'cross_section_velocity' in his_variables.keys(): 
                self.cross_section_velocity = pd.DataFrame(his_variables['cross_section_velocity'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section cumulative salinity
            if 'cross_section_cumulative_salt' in his_variables.keys(): 
                self.cross_section_cumulative_salinity = pd.DataFrame(his_variables['cross_section_cumulative_salt'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section salinity
            if 'cross_section_salt' in his_variables.keys(): 
                self.cross_section_salinity = pd.DataFrame(his_variables['cross_section_salt'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section cumulative temperatures
            if 'cross_section_cumulative_temperature' in his_variables.keys(): 
                self.cross_section_cumulative_temperature = pd.DataFrame(his_variables['cross_section_cumulative_temperature'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section temperatures
            if 'cross_section_temperature' in his_variables.keys(): 
                self.cross_section_temperature = pd.DataFrame(his_variables['cross_section_temperature'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section contaminant
            if 'cross_section_Contaminant' in his_variables.keys(): 
                self.cross_section_contaminant = pd.DataFrame(his_variables['cross_section_Contaminant'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)
            # Get cross section cumulative contaminant
            if 'cross_section_cumulative_Contaminant' in his_variables.keys(): 
                self.cross_section_cumulative_contaminant = pd.DataFrame(his_variables['cross_section_cumulative_Contaminant'][:].data,
                                    index=self.his_timestamps, columns=self.cross_section['name'].values)

        # Get water level at stations
        if 'waterlevel' in his_variables.keys():
            self.waterlevel = pd.DataFrame(index=self.his_timestamps, data=his_variables['waterlevel'][:], columns=stations.keys())
        # Get bed level at stations
        if 'bedlevel' in his_variables.keys():
            self.bedlevel = pd.DataFrame(his_variables['bedlevel'][:].data).T
            rename = {i: key for i, key in enumerate(stations.keys())}
            self.bedlevel.rename(columns=rename, inplace=True)
        # Get water depth at stations
        if 'waterdepth' in his_variables.keys():
            self.waterdepth = pd.DataFrame(index=self.his_timestamps, data=his_variables['waterdepth'][:], columns=stations.keys())
        # Get velocity at stations
        if 'x_velocity' in his_variables.keys():
            self.x_velocity, self.x_v = his_variables['x_velocity'][:].data, True
        if 'y_velocity' in his_variables.keys():
            self.y_velocity, self.y_v = his_variables['y_velocity'][:].data, True
        if 'z_velocity' in his_variables.keys():
            self.z_velocity, self.z_v = his_variables['z_velocity'][:].data, True
        
        # Get depth-averaged velocity at stations
        if 'depth-averaged_x_velocity' in his_variables.keys():
            self.depth_averaged_x_velocity = pd.DataFrame(index=self.his_timestamps, data=his_variables['depth-averaged_x_velocity'][:], columns=stations.keys())
        if 'depth-averaged_y_velocity' in his_variables.keys():
            self.depth_averaged_y_velocity = pd.DataFrame(index=self.his_timestamps, data=his_variables['depth-averaged_y_velocity'][:], columns=stations.keys())
        # Get richardson number at stations
        if 'rich' in his_variables.keys(): 
            self.richardson_number = his_variables['rich'][:].data
        # Get salinity at stations
        if 'salinity' in his_variables.keys(): 
            self.salinity = his_variables['salinity'][:].data
        # Get velocity magnitude at stations
        if 'velocity_magnitude' in his_variables.keys(): 
            self.velocity_magnitude = his_variables['velocity_magnitude'][:].data
        # Get discharge magnitude at stations
        if 'discharge_magnitude' in his_variables.keys(): 
            self.discharge_magnitude = his_variables['discharge_magnitude'][:].data
        # Get tau_x and tau_y at stations
        if 'tausx' in his_variables.keys():
            self.tausx = pd.DataFrame(index=self.his_timestamps, data=his_variables['tausx'][:], columns=stations.keys())
        if 'tausy' in his_variables.keys(): 
            self.tausy = pd.DataFrame(index=self.his_timestamps, data=his_variables['tausy'][:], columns=stations.keys())
        # Get temperature at stations
        if 'temperature' in his_variables.keys(): 
            self.temperature = his_variables['temperature'][:].data
        # Get wind at stations
        if 'wind' in his_variables.keys(): 
            self.wind = pd.DataFrame(index=self.his_timestamps, data=his_variables['wind'][:], columns=stations.keys())
        # Get air temperature at stations
        if 'Tair' in his_variables.keys(): 
            self.air_temperature = pd.DataFrame(index=self.his_timestamps, data=his_variables['Tair'][:], columns=stations.keys())
        # Get relative humidity at stations
        if 'rhum' in his_variables.keys(): 
            self.relative_humidity = pd.DataFrame(index=self.his_timestamps, data=his_variables['rhum'][:], columns=stations.keys())
        # Get cloud cover at stations
        if 'clou' in his_variables.keys(): 
            self.cloud_cover = pd.DataFrame(index=self.his_timestamps, data=his_variables['clou'][:], columns=stations.keys())
        # Get solar radiation at stations
        if 'Qsun' in his_variables.keys(): 
            self.solar_radiation = pd.DataFrame(index=self.his_timestamps, data=his_variables['Qsun'][:], columns=stations.keys())
        # Get evaporation at stations
        if 'Qeva' in his_variables.keys(): 
            self.evaporation = pd.DataFrame(index=self.his_timestamps, data=his_variables['Qeva'][:], columns=stations.keys())
        # Get convection at stations
        if 'Qcon' in his_variables.keys(): 
            self.convection = pd.DataFrame(index=self.his_timestamps, data=his_variables['Qcon'][:], columns=stations.keys())
        # Get longwave radiation at stations
        if 'Qlong' in his_variables.keys(): 
            self.longwave_radiation = pd.DataFrame(index=self.his_timestamps, data=his_variables['Qlong'][:], columns=stations.keys())
        # Get evaporation frequency at stations
        if 'Qfreva' in his_variables.keys(): 
            self.frequency_evaporation = pd.DataFrame(index=self.his_timestamps, data=his_variables['Qfreva'][:], columns=stations.keys())
        # Get convection frequency at stations
        if 'Qfrcon' in his_variables.keys(): 
            self.frequency_convection = pd.DataFrame(index=self.his_timestamps, data=his_variables['Qfrcon'][:], columns=stations.keys())
        # Get total energy at stations
        if 'Qtot' in his_variables.keys(): 
            self.total_energy = pd.DataFrame(index=self.his_timestamps, data=his_variables['Qtot'][:], columns=stations.keys())
        # Get precipitation at stations
        if 'rain' in his_variables.keys(): 
            self.precipitation = pd.DataFrame(index=self.his_timestamps, data=his_variables['rain'][:], columns=stations.keys())
        # Get zcoordinate_c, zcoordinate_w, zcoordinate_wu
        if 'zcoordinate_c' in his_variables.keys(): 
            self.zcoordinate_c = his_variables['zcoordinate_c'][:].data
        if 'zcoordinate_w' in his_variables.keys(): 
            self.zcoordinate_w = his_variables['zcoordinate_w'][:].data
        if 'zcoordinate_wu' in his_variables.keys(): 
            self.zcoordinate_wu = his_variables['zcoordinate_wu'][:].data
        # Get water balance
        if 'water_balance_total_volume' in his_variables.keys(): 
            self.waterbalance_totalvolume = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_total_volume'][:].data)
        if 'water_balance_storage' in his_variables.keys():
            self.waterbalance_storage = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_storage'][:].data)
        if 'water_balance_volume_error' in his_variables.keys():
            self.waterbalance_volumeerror = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_volume_error'][:].data)
        if 'water_balance_boundaries_in' in his_variables.keys():
            self.waterbalance_boundariesin = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_boundaries_in'][:].data)
        if 'water_balance_boundaries_out' in his_variables.keys():
            self.waterbalance_boundariesout = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_boundaries_out'][:].data)
        if 'water_balance_boundaries_total' in his_variables.keys():
            self.waterbalance_boundariestotal = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_boundaries_total'][:].data)
        if 'water_balance_exchange_with_1D_in' in his_variables.keys():
            self.water_balance_exchange_with_1D_in = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_exchange_with_1D_in'][:].data)
        if 'water_balance_exchange_with_1D_out' in his_variables.keys():
            self.water_balance_exchange_with_1D_out = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_exchange_with_1D_out'][:].data)
        if 'water_balance_exchange_with_1D_total' in his_variables.keys():
            self.water_balance_exchange_with_1D_total = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_exchange_with_1D_total'][:].data)
        if 'water_balance_precipitation_total' in his_variables.keys():
            self.waterbalance_precipitation = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_precipitation_total'][:].data)
        if 'water_balance_evaporation' in his_variables.keys():
            self.waterbalance_evaporation = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_evaporation'][:].data)
        if 'water_balance_source_sink' in his_variables.keys():
            self.waterbalance_sourcesink = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_source_sink'][:].data)
        if 'water_balance_groundwater_in' in his_variables.keys():
            self.waterbalance_groundwaterin = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_groundwater_in'][:].data)
        if 'water_balance_groundwater_out' in his_variables.keys():
            self.waterbalance_groundwaterout = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_groundwater_out'][:].data)
        if 'water_balance_groundwater_total' in his_variables.keys():
            self.waterbalance_groundwatertotal = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_groundwater_total'][:].data)
        if 'water_balance_precipitation_on_ground' in his_variables.keys():
            self.waterbalance_precipitationonground = pd.DataFrame(index=self.his_timestamps, data=his_variables['water_balance_precipitation_on_ground'][:].data)

        # Get checkerboard monitor
        if 'checkerboard_monitor' in his_variables.keys(): 
            self.checkerboard_monitor = pd.DataFrame(index=self.his_timestamps, data=his_variables['checkerboard_monitor'][:].data)
        # Get completed time
        if 'comp_time' in his_variables.keys(): 
            self.completed_time = his_variables['comp_time'][:].data
        # Get contaminat
        if 'Contaminant' in his_variables.keys(): 
            self.contaminant = his_variables['Contaminant'][:].data

    def read_map(self):
        map_data = self.map_data
        # Get values from map_data
        self.points = gpd.GeoDataFrame({ "Point": ['point_min', 'point_max']}, crs='EPSG:4326',
                geometry=gpd.points_from_xy([map_data.geospatial_lon_min, map_data.geospatial_lon_max],
                [map_data.geospatial_lat_min, map_data.geospatial_lat_max]))
        self.map_dimensions = {key: map_data.dimensions[key].size for key in map_data.dimensions}
        map_variables = {key: map_data.variables[key] for key in map_data.variables}
        self.map_variables = map_variables
        self.map_date_created, self.map_date_modified = pd.to_datetime(map_data.date_created, utc=True), pd.to_datetime(map_data.date_modified, utc=True)
        self.map_time_start, self.map_time_end = pd.to_datetime(map_data.time_coverage_start.replace('*', '0'), utc=True), pd.to_datetime(map_data.time_coverage_end.replace('*', '0'), utc=True)
        # Get time stamps
        time_var = map_data.variables['time']
        time_values = num2date(time_var[:], units=time_var.units, calendar=getattr(time_var, 'calendar', 'standard'))
        datetime_list = [datetime(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in time_values[:].data]
        self.map_timestamps = pd.to_datetime(datetime_list, utc=True)
        # Get mesh2d_node_x, mesh2d_node_y, mesh2d_node_z: x, y, z of the nodes
        if 'mesh2d_node_x' in map_variables:
            self.mesh2d_node_x = map_variables['mesh2d_node_x'][:].data # x coordinates of the nodes in the net (nNodes,)
            self.x = True
        if 'mesh2d_node_y' in map_variables:
            self.mesh2d_node_y = map_variables['mesh2d_node_y'][:].data # y coordinates of the nodes in the net (nNodes,)
            self.y = True
        if 'mesh2d_node_z' in map_variables:
            self.mesh2d_node_z = map_variables['mesh2d_node_z'][:].data # bottom elevation (nNodes,)
            self.z = True
        # Get mesh2d_edge_x, mesh2d_edge_y
        if 'mesh2d_edge_x' in map_variables:
            self.mesh2d_edge_x = map_variables['mesh2d_edge_x'][:].data # x coordinates of the edges (nEdges,)
        if 'mesh2d_edge_y' in map_variables:
            self.mesh2d_edge_y = map_variables['mesh2d_edge_y'][:].data # y coordinates of the edges (nEdges,)
        # Get mesh2d_edge_nodes
        if 'mesh2d_edge_nodes' in map_variables: 
            self.mesh2d_edge_nodes = map_variables['mesh2d_edge_nodes'][:].data # connectivity of the edges to the nodes (nEdges, 2)
        # Get mesh2d_face_nodes
        if 'mesh2d_face_nodes' in map_variables: 
            self.mesh2d_face_nodes = map_variables['mesh2d_face_nodes'][:].data # list of nodes making up each face (nFaces, 3)
        # Get mesh2d_edge_faces
        if 'mesh2d_edge_faces' in map_variables: 
            self.mesh2d_edge_faces = map_variables['mesh2d_edge_faces'][:].data # connectivity of the edges to the faces
        # Get mesh2d_face_x, mesh2d_face_y
        if 'mesh2d_face_x' in map_variables: 
            self.mesh2d_face_x = map_variables['mesh2d_face_x'][:].data # x coordinates of the center of the faces
        if 'mesh2d_face_y' in map_variables: 
            self.mesh2d_face_y = map_variables['mesh2d_face_y'][:].data # y coordinates of the center of the faces
        # Get mesh2d_face_x_bnd, mesh2d_face_y_bnd
        if 'mesh2d_face_x_bnd' in map_variables: 
            self.mesh2d_face_x_bnd = map_variables['mesh2d_face_x_bnd'][:].data # x coordinates of the boundary of the faces
        if 'mesh2d_face_y_bnd' in map_variables: 
            self.mesh2d_face_y_bnd = map_variables['mesh2d_face_y_bnd'][:].data # y coordinates of the boundary of the faces
        # Get mesh2d_layer_sigma, mesh2d_interface_sigma
        if 'mesh2d_layer_sigma' in map_variables.keys():
            self.mesh2d_layer_sigma = map_variables['mesh2d_layer_sigma'][:].data # sigma of the layers
        if 'mesh2d_interface_sigma' in map_variables.keys():
             self.mesh2d_interface_sigma = map_variables['mesh2d_interface_sigma'][:].data # sigma of the interfaces
        # Get mesh2d_layer_z, mesh2d_interface_z
        if 'mesh2d_layer_z' in map_variables.keys(): 
            self.mesh2d_layer_z = map_variables['mesh2d_layer_z'][:].data # z of the layers
        if 'mesh2d_interface_z' in map_variables.keys(): 
            self.mesh2d_interface_z = map_variables['mesh2d_interface_z'][:].data # z of the interfaces
        # Get mesh2d_sigmazdepth
        if 'mesh2d_sigmazdepth' in map_variables.keys(): 
            self.mesh2d_sigmazdepth = map_variables['mesh2d_sigmazdepth'][:].data # sigma of the layers
        # Get mesh2d_layer_sigma_z, mesh2d_interface_sigma_z
        if 'mesh2d_layer_sigma_z' in map_variables.keys(): 
            self.mesh2d_layer_sigma_z = map_variables['mesh2d_layer_sigma_z'][:].data  # sigma of the layers
        if 'mesh2d_interface_sigma_z' in map_variables.keys(): 
            self.mesh2d_interface_sigma_z = map_variables['mesh2d_interface_sigma_z'][:].data # sigma of the interfaces
        # Get mesh2d_edge_type
        if 'mesh2d_edge_type' in map_variables.keys(): 
            self.mesh2d_edge_type = map_variables['mesh2d_edge_type'][:].data # type of the edges
        # Get mesh2d_bldepth
        if 'mesh2d_bldepth' in map_variables.keys(): 
            self.mesh2d_bldepth = map_variables['mesh2d_bldepth'][:].data 
        # Get mesh2d_flowelem_ba, mesh2d_flowelem_bl
        if 'mesh2d_flowelem_ba' in map_variables.keys(): 
            self.mesh2d_flowelem_ba = map_variables['mesh2d_flowelem_ba'][:].data # area of the flow elements
        if 'mesh2d_flowelem_bl' in map_variables.keys(): 
            self.mesh2d_flowelem_bl = map_variables['mesh2d_flowelem_bl'][:].data # bottom length of the flow elements
        # Get mesh2d_s1: water level at node
        if 'mesh2d_s1' in map_variables.keys(): 
            self.mesh2d_s1 = map_variables['mesh2d_s1'][:].data # water level at node (timestamps, )
        # Get mesh2d_waterdepth
        if 'mesh2d_waterdepth' in map_variables.keys(): 
            self.mesh2d_waterdepth = map_variables['mesh2d_waterdepth'][:].data # water depth at node
        # Get mesh2d_ucx, mesh2d_ucy, mesh2d_ucz
        if 'mesh2d_ucx' in map_variables.keys(): 
            self.mesh2d_ucx = map_variables['mesh2d_ucx'][:].data # x-axis flow velocity at node
        if 'mesh2d_ucy' in map_variables.keys(): 
            self.mesh2d_ucy = map_variables['mesh2d_ucy'][:].data # y-axis flow velocity at node
        if 'mesh2d_ucz' in map_variables.keys(): 
            self.mesh2d_ucz = map_variables['mesh2d_ucz'][:].data # z-axis flow velocity at node
        # Get mesh2d_ucxa, mesh2d_ucya
        if 'mesh2d_ucxa' in map_variables.keys(): 
            self.mesh2d_ucxa = map_variables['mesh2d_ucxa'][:].data # average x-axis flow velocity at node
        if 'mesh2d_ucya' in map_variables.keys(): 
            self.mesh2d_ucya = map_variables['mesh2d_ucya'][:].data # average y-axis flow velocity at node
        # Get mesh2d_ucmag, mesh2d_ucmaga
        if 'mesh2d_ucmag' in map_variables.keys(): 
            self.mesh2d_ucmag = map_variables['mesh2d_ucmag'][:].data
        if 'mesh2d_ucmaga' in map_variables.keys():
            self.mesh2d_ucmaga = map_variables['mesh2d_ucmaga'][:].data
        # Get mesh2d_ww1
        if 'mesh2d_ww1' in map_variables.keys(): 
            self.mesh2d_ww1 = map_variables['mesh2d_ww1'][:].data
        # Get mesh2d_sa1
        if 'mesh2d_sa1' in map_variables.keys(): 
            self.mesh2d_sa1 = map_variables['mesh2d_sa1'][:].data
        # Get mesh2d_tem1
        if 'mesh2d_tem1' in map_variables.keys(): 
            self.mesh2d_tem1 = map_variables['mesh2d_tem1'][:].data
        # Get contaminants
        if 'mesh2d_Contaminant' in map_variables.keys(): 
            self.mesh2d_contaminant = map_variables['mesh2d_Contaminant'][:].data

    def unstructured_grid(self) -> None:
        """
        Computer the unstructured grid from the mesh2d data
        """
        # Generate a PyVista grid from the mesh2d data
        point_ = np.column_stack((self.mesh2d_node_x, self.mesh2d_node_y, np.zeros_like(self.mesh2d_node_x)))  # Assuming z-coordinates are zero for 2D mesh
        faces, polygons = [], []
        for face in self.mesh2d_face_nodes:
            nodes = face[~np.isnan(face) & (face != -999)].astype(int) - 1
            faces.append(len(nodes))  # Number of nodes in the face
            faces.extend(nodes.flatten())
        # Convert to a PyVista-compatible format
        grid = pv.PolyData(point_, faces)
        # Convert meshes to polydata
        for i in range(grid.n_cells):
            cell = grid.get_cell(i)
            poly = cell.points # Extract points from the cell
            # Use only x and y coordinates for 2D visualization
            polygons.append(shapely.geometry.Polygon(poly[:, :2])) 
        # Create GeoDataFrame from polygons
        self.unstructured_grid = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:4326')

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

def assign_values_to_meshes(grid: gpd.GeoDataFrame, time_stamps: pd.DatetimeIndex, data, stations: gpd.GeoDataFrame=None) -> gpd.GeoDataFrame:
    """
    Interpolate or extrapolate z values for grid from known points
    using Inverse Distance Weighting (IDW) method.

    Parameters:
    ----------
    grid: gpd.GeoDataFrame
        The GeoDataFrame containing the meshes/unstructured grid.
    time_stamps: pd.DatetimeIndex
        The time stamps of simulation.
    data: object
        - DataFrame: The DataFrame containing the data (stations with a column named 'name' as required).
        - 2D array: The 2D array containing the data.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame with interpolated z values (locations are in ).
    """
    result, temp_grid = {}, grid.copy()
    if isinstance(data, gpd.GeoDataFrame):
        # Get location of stations
        x = np.array([stations[stations['name'] == i]['geometry'].x for i in data.columns]).flatten()
        y = np.array([stations[stations['name'] == i]['geometry'].y for i in data.columns]).flatten()
        for t in time_stamps:
            z = np.array(data.loc[t]).flatten()
            result[t] = interpolation_Z(temp_grid, x, y, z, len(stations.index))
    elif isinstance(data, np.ndarray):
        for i in range(time_stamps.shape[0]):
            result[time_stamps[i]] = np.array(data[i,:]).flatten()
    result = pd.DataFrame(result).replace(-999.0, np.nan)
    result = temp_grid.join(result).to_crs(temp_grid.crs)
    result[time_stamps] = result[time_stamps].round(2)
    result = result.rename(columns={i: i.strftime('%Y-%m-%d %H:%M:%S') for i in time_stamps}).reset_index()
    return result

def select_polygon(time_stamps: pd.DatetimeIndex, h_layer: np.ndarray, arr: np.ndarray, idx: int) -> dict:
    """
    Get attributes of a selected polygon during the simulation.

    Parameters:
    ----------
    time_stamps: pd.DatetimeIndex
        The time stamps of simulation.
    h_layer: np.ndarray (1D)
        The array containing the heights of each layer.
    arr: np.ndarray (3D)
        The array containing the attributes of the selected polygons.
    idx: int
        The index of the selected polygon.

    Returns:
    -------
    dict
        A dictionary containing the attributes of the selected polygon.
    """
    result, depth = pd.DataFrame(index=time_stamps), np.round(h_layer, 2)[::-1]
    # Reverse the array
    depth_rev = depth[::-1]
    for i in range(arr.shape[2]):
        i_rev = -(i+1)
        arr_rev = np.round(arr[:, idx, i_rev], 2)
        result[f'Layer {i} - H: {depth_rev[i_rev]} (m)'] = arr_rev
    result = result.replace(-999.0, np.nan)
    temp = result.reset_index().to_json(orient='split', date_format='iso', indent=3)
    return json.loads(temp)

def vector_map(node_x: np.ndarray, node_y: np.ndarray, timestamps: pd.DatetimeIndex,
        v_xaxis: np.ndarray, v_yaxis: np.ndarray, v_value: np.ndarray) -> gpd.GeoDataFrame:
    """
    Create a vector map of the mesh.

    Parameters:  
    ----------
    node_x: np.ndarray
        The array containing the x coordinates of the centroids of the nodes.
    node_y: np.ndarray
        The array containing the y coordinates of the centroids of the nodes.
    timestamps: pd.DatetimeIndex
        The time stamps of simulation (in _map.nc file).
    v_xaxis: np.ndarray
        The array containing the x coordinates of the vectors.
    v_yaxis: np.ndarray
        The array containing the y coordinates of the vectors.
    v_value: np.ndarray
        The array containing the values of the vectors.

    Returns:
    -------
    gpd.GeoDataFrame
        The GeoDataFrame containing the vector map of the mesh.
    """
    result = gpd.GeoDataFrame(geometry=gpd.points_from_xy(node_x, node_y),
                      columns=np.arange(len(timestamps)), crs='epsg:4326')
    for item in range(len(timestamps)):
        result[item] = [(round(x, 7), round(y, 7), round(z, 2)) for x, y, z in zip(v_xaxis[item, :], v_yaxis[item, :], v_value[item, :])]
    result = result.rename(columns={i: timestamps[i].strftime('%Y-%m-%d %H:%M:%S') for i in range(len(timestamps))})
    return result


