export const n_decimals = 2; export const degree_decimals = 8;
export const superscriptMap = {
    '-': '⁻', '0': '⁰', '1': '¹', '2': '²', '3': '³',
    '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
};


export function getProject() { 
    const data = localStorage.getItem("projectData");
    return data ? JSON.parse(data) : null; }
export function setProject(value) { 
    localStorage.setItem("projectData", JSON.stringify(value));}

let stationLayer = false;
export const getStationLayer = () => stationLayer;
export const setStationLayer = (value) => { stationLayer = value;};

let sourceLayer = false;
export const getSourceLayer = () => sourceLayer;
export const setSourceLayer = (value) => { sourceLayer = value;};

let crosssectionLayer = false;
export const getCrosssectionLayer = () => crosssectionLayer;
export const setCrosssectionLayer = (value) => { crosssectionLayer = value;};

let isPointQuery = false;
export const getIsPointQuery = () => isPointQuery;
export const setIsPointQuery = (value) => { isPointQuery = value;};

let isPathQuery = false;
export const getIsPathQuery = () => isPathQuery;
export const setIsPathQuery = (value) => { isPathQuery = value;};

let lastFeatureColors = {};
export const getLastFeatureColors = () => lastFeatureColors;
export const setLastFeatureColors = (value) => { lastFeatureColors = value;};

let featureMap = {};
export const getFeatureMap = () => featureMap;
export const setFeatureMap = (value) => { featureMap = value;};

let mapLayer = null;
export const getMapLayer = () => mapLayer;
export const setMapLayer = (value) => { mapLayer = value;};

let storedLayer = null;
export const getStoredLayer = () => storedLayer;
export const setStoredLayer = (value) => { storedLayer = value;};

let globalChartData = {
    data: null, chartTitle: "", titleX: "", titleY: "", 
    validColumns: [], swap: false
};
export const getGlobalChartData = () => globalChartData;
export const setGlobalChartData = (value) => { globalChartData = value;};

let polygonCentroids = [];
export const getPolygonCentroids = () => polygonCentroids;
export const setPolygonCentroids = (value) => { polygonCentroids = value;};

let isPlaying = null;
export const getIsPlaying = () => isPlaying;
export const setIsPlaying = (value) => { isPlaying = value;};

let isMultiLayer = false;
export const getIsMultiLayer = () => isMultiLayer;
export const setIsMultiLayer = (value) => { isMultiLayer = value;};

let isClickedInsideLayer = false;
export const getIsClickedInsideLayer = () => isClickedInsideLayer;
export const setIsClickedInsideLayer = (value) => { isClickedInsideLayer = value;};

let vectorMain = '';
export const getVectorMain = () => vectorMain;
export const setVectorMain = (value) => { vectorMain = value;};

let vectorSelected = '';
export const getVectorSelected = () => vectorSelected;
export const setVectorSelected = (value) => { vectorSelected = value;};

let scalerValue = null;
export const getScalerValue = () => scalerValue;
export const setScalerValue = (value) => { scalerValue = value;};


export const arrowShape = new Path2D();
arrowShape.moveTo(0, 0);          // Origin
arrowShape.lineTo(1, 0);          // Main length
arrowShape.moveTo(1, 0);
arrowShape.lineTo(0.8, 0.1);      // Left branch
arrowShape.moveTo(1, 0);
arrowShape.lineTo(0.8, -0.1);     // Right branch