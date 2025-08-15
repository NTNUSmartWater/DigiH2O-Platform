export const n_decimals = 2; export const degree_decimals = 8;

let isMenuOpen = true;
export const getIsMenuOpen = () => isMenuOpen;
export const setIsMenuOpen = (value) => { isMenuOpen = value;};

let isInfoOpen = true;
export const getIsInfoOpen = () => isInfoOpen;
export const setIsInfoOpen = (value) => { isInfoOpen = value;};

let globalChartData = {
    data: null, chartTitle: "", titleX: "", titleY: "", 
    validColumns: [], columnIndexMap: {}, swap: false
};
export const getGlobalChartData = () => globalChartData;
export const setGlobalChartData = (value) => { globalChartData = value;};

let stationLayer = false;
export const getStationLayer = () => stationLayer;
export const setStationLayer = (value) => { stationLayer = value;};

let mapLayer = null;
export const getMapLayer = () => mapLayer;
export const setMapLayer = (value) => { mapLayer = value;};

let isPathQuery = false;
export const getIsPathQuery = () => isPathQuery;
export const setIsPathQuery = (value) => { isPathQuery = value;};

let isPointQuery = false;
export const getIsPointQuery = () => isPointQuery;
export const setIsPointQuery = (value) => { isPointQuery = value;};

let polygonCentroids = [];
export const getPolygonCentroids = () => polygonCentroids;
export const setPolygonCentroids = (value) => { polygonCentroids = value;};

let pointContainer = [];
export const getPointContainer = () => pointContainer;
export const setPointContainer = (value) => { pointContainer = value;};

let isPlaying = null;
export const getIsPlaying = () => isPlaying;
export const setIsPlaying = (value) => { isPlaying = value;};

let isClickedInsideLayer = false;
export const getIsClickedInsideLayer = () => isClickedInsideLayer;
export const setIsClickedInsideLayer = (value) => { isClickedInsideLayer = value;};

let isPath = false;
export const getIsPath = () => isPath;
export const setIsPath = (value) => { isPath = value;};

let storedLayer = null;
export const getStoredLayer = () => storedLayer;
export const setStoredLayer = (value) => { storedLayer = value;};








export const arrowShape = new Path2D();
arrowShape.moveTo(0, 0);          // Origin
arrowShape.lineTo(1, 0);          // Main length
arrowShape.moveTo(1, 0);
arrowShape.lineTo(0.8, 0.1);      // Left branch
arrowShape.moveTo(1, 0);
arrowShape.lineTo(0.8, -0.1);     // Right branch

