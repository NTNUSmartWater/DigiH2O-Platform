export const n_decimals = 2; export const degree_decimals = 8;
export const superscriptMap = {
    '-': '⁻', '0': '⁰', '1': '¹', '2': '²', '3': '³',
    '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
};

const defaultState = {
    stationLayer: false, sourceLayer: false, crosssectionLayer: false, isPointQuery: false, isPathQuery: false,
    lastFeatureColors: {}, featureMap: {}, mapLayer: null, storedLayer: null, polygonCentroids: [],
    globalChartData: {data: null, chartTitle: "", titleX: "", titleY: "", validColumns: [], swap: false},
    isPlaying: null, isMultiLayer: false, isClickedInsideLayer: false, vectorMain: '', vectorSelected: '', scalerValue: null
}
let state = structuredClone(defaultState);
export const getState = () => state;
export const setState = (newState) => { state = { ...state, ...newState }; };
// Reset state
export const resetState = () => { state = structuredClone(defaultState); };

export const arrowShape = new Path2D();
arrowShape.moveTo(0, 0);          // Origin
arrowShape.lineTo(1, 0);          // Main length
arrowShape.moveTo(1, 0);
arrowShape.lineTo(0.8, 0.1);      // Left branch
arrowShape.moveTo(1, 0);
arrowShape.lineTo(0.8, -0.1);     // Right branch