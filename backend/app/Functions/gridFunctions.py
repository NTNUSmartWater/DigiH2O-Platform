import os, warnings, pickle, optuna
import geopandas as gpd, numpy as np
from config import STATIC_DIR_BACKEND
from shapely.geometry import Polygon, MultiPolygon
from meshkernel import MeshKernel, GeometryList, OrthogonalizationParameters
from meshkernel.errors import MeshKernelError
from Functions import functions
import xarray as xr, dfm_tools as dfmt, dask.array as da
warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.ERROR)


def loadLakes(lake_path=None, depth_path=None):
    # Load lake database
    lake_dir = os.path.join(STATIC_DIR_BACKEND, 'lakes_database')
    if lake_path is not None:
        lake_db_path = os.path.normpath(os.path.join(lake_dir, 'lakes.shp'))
        if os.path.exists(lake_db_path):
            lake_db = gpd.read_file(lake_db_path)
            if lake_db.crs != 'EPSG:4326': lake_db = lake_db.to_crs(crs='EPSG:4326')
            lake_db = lake_db.dropna(subset=['Name', 'Region', 'geometry'])
            lake_db['Name'] = lake_db['Name'].fillna('Unnamed Lake')
            lake_db['Region'] = lake_db['Region'].where(lake_db['Region'].notna(), 
                'Unknown Region' + lake_db["id"].fillna(-1).astype(str))
            lake_db['id'] = lake_db['id'].astype('int64')
        with open(lake_path, 'wb') as f: pickle.dump(lake_db, f)
    if depth_path is not None:
        depth_db_path = os.path.normpath(os.path.join(lake_dir, 'depth.shp'))
        depth_db = gpd.read_file(depth_db_path)
        depth_db['id'] = depth_db['id'].astype('int64')
        depth_db.set_index('id', inplace=True)
        if depth_db.crs != 'EPSG:4326': depth_db = depth_db.to_crs(crs='EPSG:4326')
        depth_db['depth'] = depth_db['depth'].astype(float)
        with open(depth_path, 'wb') as f: pickle.dump(depth_db, f)

def remove_holes(geom, cell_size=0):
    geom = geom.buffer(0)
    if (cell_size == None): cell_size = geom.area
    if geom.geom_type == "Polygon":
        kept_interiors = [ring for ring in geom.interiors if Polygon(ring).area >= cell_size]
        return Polygon(geom.exterior, kept_interiors)
    elif geom.geom_type == "MultiPolygon":
        polygons = []
        for poly in geom.geoms:
            kept_interiors = [ring for ring in poly.interiors if Polygon(ring).area >= cell_size]
            polygons.append(Polygon(poly.exterior, kept_interiors))
        return MultiPolygon(polygons)
    else: return geom

def sort_face_ccw(nodes, x, y):
    xs = x[nodes]
    ys = y[nodes]
    cx, cy = xs.mean(), ys.mean()
    angles = np.arctan2(ys - cy, xs - cx)
    return nodes[np.argsort(angles)]

def netCDF_creator(mk: MeshKernel, depth: gpd.GeoDataFrame=None, crs=None):
    mesh = mk.mesh2d_get()
    node_x, node_y = mesh.node_x, mesh.node_y
    if depth is not None:
        if depth.crs == 'EPSG:4326': depth = depth.to_crs(depth.estimate_utm_crs())
        temp_grid = gpd.GeoDataFrame(geometry=gpd.points_from_xy(node_x, node_y), crs=depth.crs)
        node_z = functions.interpolation_Z(temp_grid, depth["geometry"].x, depth["geometry"].y, depth["depth"].values, n_neighbors=2, geo_type='point')
    else: node_z = np.zeros(len(node_x))
    # Convert to Ugrid
    grid_uds = dfmt.meshkernel_to_UgridDataset(mk, crs=crs)
    grid_uds['mesh2d'] = xr.DataArray(0,
        attrs={
            "cf_role": "mesh_topology", "long_name": "Topology data of 2D mesh",
            "topology_dimension": 2, "node_coordinates": "mesh2d_node_x mesh2d_node_y",
            "node dimensions": "mesh2d_nNodes", "max_face_nodes_dimension": "mesh2d_nMax_face_nodes",
            "edge_node_connectivity": "mesh2d_edge_nodes", "edge_dimensions": "mesh2d_nEdges",
            "edge_coordinates": "mesh2d_edge_x mesh2d_edge_y", "face_node_connectivity": "mesh2d_face_nodes",
            "face_dimension": "mesh2d_nFaces", "edge_face_connectivity": "mesh2d_edge_faces",
            "face_coordinates": "mesh2d_face_x mesh2d_face_y"
        }
    )
    grid_uds['mesh2d_node_z'] = (("mesh2d_nNodes",), da.from_array(node_z.astype('float64')))
    grid_uds['mesh2d_edge_x'] = (("mesh2d_nEdges",), da.from_array(mesh.edge_x))
    grid_uds['mesh2d_edge_y'] = (("mesh2d_nEdges",), da.from_array(mesh.edge_y))
    # Make mesh2d_edge_nodes
    edge_nodes = mesh.edge_nodes.reshape((-1, 2)).astype(np.int32)
    grid_uds['mesh2d_edge_nodes'] = (("mesh2d_nEdges", "Two"), da.from_array(edge_nodes))
    # Make mesh2d_face_nodes
    max_n, nfaces = int(mesh.nodes_per_face.max()), mesh.nodes_per_face.size
    face_nodes = np.full((nfaces, max_n), np.nan, dtype=np.float64)
    offset = np.zeros_like(mesh.nodes_per_face, dtype=int)
    offset[1:] = np.cumsum(mesh.nodes_per_face[:-1])
    for i, n in enumerate(mesh.nodes_per_face):
        if n < 3: continue
        nodes = mesh.face_nodes[offset[i]: offset[i] + n]
        _, idx = np.unique(nodes, return_index=True)
        nodes = nodes[np.sort(idx)]
        if nodes.size < 3: continue
        nodes = sort_face_ccw(nodes, mesh.node_x, mesh.node_y)
        face_nodes[i, :nodes.size] = nodes + 1
    grid_uds['mesh2d_face_nodes'] = (("mesh2d_nFaces", "mesh2d_nMax_face_nodes"), da.from_array(face_nodes))
    # Make mesh2d_edge_faces
    nEdges, nfaces = mesh.edge_x.size, mesh.nodes_per_face.size
    edge_faces = np.full((nEdges, 2), -1, dtype=np.int32)
    edges = mesh.edge_nodes.reshape((-1, 2))
    edge_dict = {tuple(sorted(edges[i])): i for i in range(edges.shape[0])}
    for fidx in range(nfaces):
        n = mesh.nodes_per_face[fidx]
        nodes = mesh.face_nodes[offset[fidx]: offset[fidx]+n]
        # iterate over edges of face
        for i in range(n):
            n1, n2 = nodes[i], nodes[(i+1)%n]
            edge_key = tuple(sorted([n1, n2]))
            eidx = edge_dict[edge_key]
            if edge_faces[eidx, 0] == -1: edge_faces[eidx, 0] = fidx
            elif edge_faces[eidx, 1] == -1: edge_faces[eidx, 1] = fidx
            else: raise ValueError(f"Edge {eidx} shared by >2 faces")
    grid_uds['mesh2d_edge_faces'] = (("mesh2d_nEdges", "Two"), da.from_array(edge_faces))
    grid_uds['mesh2d_face_x'] = (("mesh2d_nFaces",), da.from_array(mesh.face_x))
    grid_uds['mesh2d_face_y'] = (("mesh2d_nFaces",), da.from_array(mesh.face_y))
    # Make mesh2d_face_x_bnd, mesh2d_face_y_bnd
    x_bnd = np.full((nfaces, max_n), np.nan, dtype=np.float64)
    y_bnd = np.full((nfaces, max_n), np.nan, dtype=np.float64)
    for i in range(nfaces):
        fn = face_nodes[i]
        valid = ~np.isnan(fn)
        if valid.sum() < 3: continue
        idx = fn[valid].astype(int) - 1
        x_bnd[i, valid] = mesh.node_x[idx]
        y_bnd[i, valid] = mesh.node_y[idx]
    grid_uds['mesh2d_face_x_bnd'] = (("mesh2d_nFaces", "mesh2d_nMax_face_nodes"), da.from_array(x_bnd))
    grid_uds['mesh2d_face_y_bnd'] = (("mesh2d_nFaces", "mesh2d_nMax_face_nodes"), da.from_array(y_bnd))
    grid_uds.attrs.update({ "institution": 'Private', "references": 'vanlnNTNU@gmail.com'})
    return grid_uds

def mk_from_params(params, polygon):
    mk = MeshKernel()
    if params['mode'] == 'auto': mk.mesh2d_make_triangular_mesh_from_polygon(polygon)
    else: mk.mesh2d_make_triangular_mesh_from_polygon(polygon, scale_factor=float(params['level']))
    ortho_params = OrthogonalizationParameters(
        outer_iterations=params['outer_iterations'],
        boundary_iterations=params['boundary_iterations'],
        inner_iterations=params['inner_iterations'],
        orthogonalization_to_smoothing_factor=params['smoothing_factor']
    )
    mk.mesh2d_compute_orthogonalization(
        project_to_land_boundary_option=False,
        orthogonalization_parameters=ortho_params,
        land_boundaries=polygon
    )
    return mk

def Bayesian_Optimization(polygon:GeometryList, space: dict, iterations: int=500,
                          progress_callback=None, stop_checker=None):
    """
    Bayesian Optimization using Optuna to minimize the maximum orthogonality.
    """
    best_value, best_type, best_level = float('inf'), "", float('inf')
    def objective_function(trial: optuna.trial.Trial):
        try:
            type_choice = trial.suggest_categorical("mode", space['mode'])
            level = trial.suggest_float("level", space['level'][0], space['level'][1])
            outer_iterations = trial.suggest_int(
                "outer_iterations", space['outer_iterations'][0], 
                space['outer_iterations'][1]
            )
            boundary_iterations = trial.suggest_int(
                "boundary_iterations", space['boundary_iterations'][0], 
                space['boundary_iterations'][1]
            )
            inner_iterations = trial.suggest_int(
                "inner_iterations", space['inner_iterations'][0], 
                space['inner_iterations'][1]
            )
            smoothing_factor = trial.suggest_float(
                "smoothing_factor", space['smoothing_factor'][0], 
                space['smoothing_factor'][1]
            )
            mk, iteration = MeshKernel(), trial.number + 1
            if type_choice == 'auto': mk.mesh2d_make_triangular_mesh_from_polygon(polygon)
            else: mk.mesh2d_make_triangular_mesh_from_polygon(polygon, scale_factor=float(level))        
            ortho_params = OrthogonalizationParameters(
                outer_iterations=outer_iterations, boundary_iterations=boundary_iterations,
                inner_iterations=inner_iterations,
                orthogonalization_to_smoothing_factor=smoothing_factor
            )        
            mk.mesh2d_compute_orthogonalization(
                project_to_land_boundary_option=False,
                orthogonalization_parameters=ortho_params, land_boundaries=polygon
            )        
            orth = mk.mesh2d_get_orthogonality().values
            orth_valid = orth[orth != -999]
            if len(orth_valid) == 0: return 1e6
            min_value, mean_value, max_value = np.min(orth_valid), np.mean(orth_valid), np.max(orth_valid)
            nonlocal best_value, best_type, best_level
            if max_value < best_value:
                best_type, best_level, best_value = type_choice, level, max_value
            # Update progress
            if progress_callback:
                progress_callback(
                    iteration=iteration, min_value=min_value, mean_value=mean_value,
                    best_type=best_type, best_level=best_level,
                    current_ortho=max_value, best_ortho=best_value
                )
            if stop_checker and stop_checker():
                trial.study.stop()
                return best_value
        except MeshKernelError: return 1e6
        except Exception: return 1e6
        if max_value <= 0.01 or trial.number >= iterations: trial.study.stop()
        return max_value
    sampler = optuna.samplers.TPESampler(seed=42, multivariate=True)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(objective_function, n_trials=iterations, show_progress_bar=False)
    return study.best_params
