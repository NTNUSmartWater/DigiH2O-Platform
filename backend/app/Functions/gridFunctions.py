import os, warnings, pickle
import geopandas as gpd, numpy as np
from config import STATIC_DIR_BACKEND
from shapely.geometry import Polygon
from meshkernel import MeshKernel
from Functions import functions
import xarray as xr, dfm_tools as dfmt
import dask.array as da
warnings.filterwarnings("ignore")


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
    if geom.geom_type != "Polygon": return geom
    kept_interiors = [ ring for ring in geom.interiors
        if Polygon(ring).area >= cell_size
    ]
    return Polygon(geom.exterior, kept_interiors)

def sort_face_ccw(nodes, x, y):
    xs = x[nodes]
    ys = y[nodes]
    cx, cy = xs.mean(), ys.mean()
    angles = np.arctan2(ys - cy, xs - cx)
    return nodes[np.argsort(angles)]

def netCDF_creator(mk: MeshKernel, depth: gpd.GeoDataFrame):
    mesh = mk.mesh2d_get()
    node_x, node_y = mesh.node_x, mesh.node_y
    temp_grid = gpd.GeoDataFrame(geometry=gpd.points_from_xy(node_x, node_y), crs=depth.crs)
    node_z = functions.interpolation_Z(temp_grid, depth["geometry"].x, depth["geometry"].y, depth["depth"].values, n_neighbors=2, geo_type='point')
    # Convert to Ugrid
    grid_uds = dfmt.meshkernel_to_UgridDataset(mk, crs=depth.crs)
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

# from hyperopt import STATUS_OK, Trials, fmin, hp, tpe

# tuning_folder = 'Tuning_Process'
# if os.path.exists(tuning_folder) == False:
#     os.mkdir('Tuning_Process')
# if os.path.exists('Models') == False:
#     os.mkdir( 'Models')

# files, input_columns = [], {}
# data_folder, threshold = 'Merge_Data', {}
# for i in os.listdir(data_folder):
#     if i.endswith('.csv'):
#         files.append(i)
#         data_df = pd.read_csv(os.path.join(data_folder, i), parse_dates=True, index_col=0)
#         input_columns[i.split('.')[0].replace('merge_','')] = data_df.columns.to_list()
# with open(os.path.join('Models','model_inputs.json'), 'w') as convert_file:
#     convert_file.write(json.dumps(input_columns))

# files = ['merge_GOSFST.csv']
# # best_model_dict = {} 
# for file in files:
#     folder = file.split('.')[0].split('_')[1]
#     if os.path.exists(os.path.join(tuning_folder,folder)) == False:
#         os.mkdir(os.path.join(tuning_folder,folder))
#     data_df = pd.read_csv(os.path.join(data_folder, file), parse_dates=True, index_col=0)
#     biofilters, previous_steps = [], [6] #3, 6, 12, 24, 48
#     df = data_df.resample('60Min').mean()#.dropna()
#     # # Interpolate
#     # df = df.interpolate(method='time')
#     for i in data_df.columns.to_list():
#         if "Biofilter" in i:
#             biofilters.append(i)
#     dict_threshold = {}
#     for n_biofilter in biofilters:
#         number = pow(10, 10)
#         for pre_step in previous_steps:
#             print(f'Working with: {n_biofilter} - Window size: {pre_step}')
#             df['Seconds'] = df.index.map(pd.Timestamp.timestamp)
#             df['Day sin'] = np.sin(df['Seconds']*(2*np.pi/(3600*24)))
#             df['Day cos'] = np.cos(df['Seconds']*(2*np.pi/(3600*24)))
#             df = df.drop('Seconds', axis=1)

#             df_X, df_y = df.drop(columns=n_biofilter), df[[n_biofilter]]
#             X, y, timestamp = createData(df_X=df_X, df_y=df_y, pre_step=pre_step, next_step=pre_step)
#             X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False, random_state=42)
#             scaler = StandardScaler()
#             X_train = scaler.fit_transform(X_train)
#             X_test = scaler.transform(X_test)
#             max_depth = np.arange(1,15,1,dtype=int)
#             tree_method = ['auto','exact','approx','hist','gpu_hist']
#             params = {"subsample": hp.uniform("subsample", 0.0, 1.0),
#                       "eta": hp.uniform("eta", 0.0, 1.0),
#                       "gamma": hp.uniform("gamma", 0.0, 10.0),
#                       'max_depth': hp.choice('max_depth', max_depth),
#                       'tree_method': hp.choice('tree_method', tree_method),
#                       }
#             def Bayesian_Optimization(param, X_train, y_train, X_test, y_test):
#                 def objective_function(param):
#                     model = XGBRegressor(subsample=param["subsample"], objective="reg:squarederror",
#                                         max_depth=param["max_depth"], tree_method=param["tree_method"],
#                                         eta=param["eta"], gamma=param["gamma"],
#                                         verbosity=0, random_state=42)
#                     model.fit(X_train, y_train, eval_metric="rmse", verbose=False)
#                     pred = model.predict(X_test)
#                     # actual, pred = y_test.flatten(), pred.flatten()
#                     actual = np.append(y_test[:-1][:,0], y_test[-1:][0])
#                     pred = np.append(pred[:-1][:,0], pred[-1:][0])
#                     loss = math.sqrt(mean_squared_error(y_true=actual, y_pred=pred))
#                     return {'loss': loss, 'status': STATUS_OK}
#                 trials, rstate = Trials(), np.random.default_rng(42)
#                 best_hyperparams = fmin(fn=objective_function, space=param, algo=tpe.suggest,
#                                         max_evals=50, trials=trials, rstate=rstate)
#                 return best_hyperparams
#             param = Bayesian_Optimization(params, X_train, y_train, X_test, y_test)
#             param['max_depth']= max_depth[param['max_depth']]
#             param['tree_method']= tree_method[param['tree_method']]
#             model = XGBRegressor(**param, random_state=42, verbosity=0).fit(
#                 X_train, y_train, eval_metric="rmse", verbose=False)
#             pred = model.predict(X_test)
#             actual, pred = np.append(y_test[:-1][:,0], y_test[-1:][0]), np.append(pred[:-1][:,0], pred[-1:][0])
#             loss = math.sqrt(mean_squared_error(y_true=actual, y_pred=pred))
#             if loss < number:
#                 number, best_params, best_step = loss, param, pre_step
#                 best_scaler, best_model = scaler, model
#         # best_model_dict.update(txt)
#         if os.path.exists(os.path.join('Models', folder)) == False:
#             os.mkdir(os.path.join('Models', folder))
#         # save the scaler and model
#         dump(best_scaler, open(os.path.join('Models', folder,f'SCALER_{n_biofilter}.pkl'), 'wb'))
#         dump(best_model, open(os.path.join('Models', folder,f'MODEL_{n_biofilter}.pkl'), 'wb'))
#         # best_step= pre_step
#         df_X, df_y = df.drop(columns=n_biofilter), df[[n_biofilter]]
#         X, y, timestamp = createData(df_X=df_X, df_y=df_y, pre_step=best_step, next_step=best_step)
#         X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False, random_state=42)
#         # Load scaler and model
#         best_scaler = load(open(os.path.join('Models', folder,f'SCALER_{n_biofilter}.pkl'), 'rb'))
#         best_model = load(open(os.path.join('Models', folder,f'MODEL_{n_biofilter}.pkl'), 'rb'))
#         score_mean = cross_val_score(best_model, X, y, cv=5, scoring='neg_root_mean_squared_error')
#         X_train = best_scaler.transform(X_train)
#         X_test = best_scaler.transform(X_test)
#         pred = best_model.predict(X_test)
#         # actual, pred = y_test.flatten(), pred.flatten()
#         actual = np.append(y_test[:-1][:,0], y_test[-1:][0])
#         pred = np.append(pred[:-1][:,0], pred[-1:][0])
#         timestamp = timestamp[y_train.shape[0]:]
#         xtick = np.append(timestamp[:-1][:,0], timestamp[-1:][0])
#         loss =math.sqrt(mean_squared_error(y_true=actual, y_pred=pred))
#         fig = plt.figure(figsize=(10, 6))
#         plt.plot(xtick, actual, label='Actual')
#         plt.plot(xtick, pred, label='Predicted')
#         plt.title(n_biofilter + '\n Window size: {} (hours)(RMSE = 'f"{loss:.3f}"
#                 .format(best_step) + ')', fontsize=12)
#         plt.ylabel('Rotation', fontsize=12)
#         plt.xlabel('Time', fontsize=12)
#         plt.tick_params(axis='both', which='major', labelsize=12)
#         plt.legend(loc='best', prop={'size': 10})
#         plt.tight_layout()
#         # plt.show()
#         plt.savefig(os.path.join(tuning_folder, folder,f'{n_biofilter}_{best_step}_hours.png'), dpi=300)
#         plt.close()
#         dict_threshold[n_biofilter] = round(-score_mean.mean(),3)
#     threshold[folder] = dict_threshold

# with open(os.path.join('Models','threshold.json'), 'w') as convert_file:
#     convert_file.write(json.dumps(threshold))
# print('Done')