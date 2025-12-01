import { loadData, getColorFromValue, updateColorbar, updateMapByTime, decodeArray } from "./utils.js";
import { startLoading, showLeafletMap, L, map } from "./mapManager.js";
import { arrowShape, getState, setState } from "./constants.js";
import { layerSelector, substanceWindow } from "./spatialMapManager.js";
import { sendQuery } from "./tableManager.js";

export const timeControl = () => document.getElementById('time-controls');
export const colorbar_container = () => document.getElementById("custom-colorbar");
export const colorbar_vector_container = () => document.getElementById("custom-colorbar-vector");
export const colorbar_title = () => document.getElementById("colorbar-title");
const scaler_value = () => document.getElementById("scaler-value");
const slider = () => document.getElementById("time-slider");
const timeSpeed = () => document.getElementById("time-slider-speed");
const playBtn = () => document.getElementById("play-btn");
const colorbar_color = () => document.getElementById("colorbar-gradient");
const colorbar_label = () => document.getElementById("colorbar-labels");
const colorbar_vector_title = () => document.getElementById("colorbar-title-vector");
const colorbar_vector_color = () => document.getElementById("colorbar-gradient-vector");
const colorbar_vector_label = () => document.getElementById("colorbar-labels-vector");
const colorbar_vector_scaler = () => document.getElementById("custom-colorbar-scaler");

let layerAbove = null, layerMap = null, playHandlerAttached = false, 
    playHandlerRef = null, parsedFrame = null, scale = null;

// Define CanvasLayer
L.CanvasLayer = L.Layer.extend({
    initialize: function (options) { L.setOptions(this, options);},
    onAdd: function (map) {
        this._map = map;
        this._canvas = L.DomUtil.create('canvas', 'leaflet-layer');
        const size = map.getSize();
        this._canvas.width = size.x;
        this._canvas.height = size.y;
        const pane = map.getPane(this.options.pane || 'overlayPane');
        pane.appendChild(this._canvas);
        this._ctx = this._canvas.getContext('2d');
        map.on('moveend zoomend resize', this._reset, this);
        this._reset();
    },
    onRemove: function (map) {
        const pane = map.getPane(this.options.pane || 'overlayPane');
        if (this._canvas) pane.removeChild(this._canvas);
        map.off('moveend zoomend resize', this._reset, this);
    },
    _reset: function () {
        const size = this._map.getSize();
        this._canvas.width = size.x;
        this._canvas.height = size.y;
        const topLeft = this._map.containerPointToLayerPoint([0, 0]);
        L.DomUtil.setPosition(this._canvas, topLeft);
        this._redraw();
    },
    _redraw: function () {
        if (!this._map) return;
        if (typeof this.options.drawLayer === 'function') {
            this.options.drawLayer.call(this);
        }
    }
});

function update(){
    timeSpeed().addEventListener("change", () => {
        clearInterval(getState().isPlaying); setState({isPlaying: null});
        playBtn().textContent = "▶ Play";
    });
}
update();    

// Create map layer
function layerCreator(meshes, values, key, vmin, vmax, colorbarTitle, colorbarKey) {
    colorbar_container().style.display = "block";
    // Filter features
    const filteredFeatures = meshes.features.filter(f => {
        const idx = f.properties.index;
        return values[idx] !== null && values[idx] !== undefined;
    });
    const filteredData = { ...meshes, features: filteredFeatures};
    // Reset variables
    setState({lastFeatureColors: {}}); setState({featureMap: {}});
    const featureIds = [];
    filteredData.features.forEach(f => {
        const idx = f.properties.index, fmap = getState().featureMap;
        fmap[idx] = f; featureIds.push(idx);
        setState({featureMap: fmap});
    });
    // Create map layer
    if (layerMap) map.removeLayer(layerMap); layerMap = null;
    layerMap = L.vectorGrid.slicer(filteredData, {
        rendererFactory: L.canvas.tile, vectorTileLayerStyles: {
            sliced: function(properties) {
                const idx = properties.index, value = values[idx];
                // Ignore null values
                if (value === null || value === undefined) return { fill: false, weight: 0, opacity: 0 };
                const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey);
                getState().lastFeatureColors[idx] = `${r},${g},${b},${a}`;
                setState({lastFeatureColors: getState().lastFeatureColors});
                return {
                    fill: true, fillColor: `rgb(${r},${g},${b})`,
                    fillOpacity: a, weight: 0, opacity: 1
                };
            },
        }, interactive: true, maxZoom: 18, getFeatureId: f => f.properties.index
    });
    // Tooltip
    const hoverTooltip = L.tooltip({ direction: 'top', sticky: true });
    layerMap.on('mouseover', function(e) {
        if (getState().isPlaying) return;
        const idx = e.layer.properties.index;
        // Show tooltip
        const html = `<div style="text-align: center;">
                <b>${colorbarTitle.split('\n')[0]}:</b> ${values[idx] ?? 'N/A'}
            </div>`;
        hoverTooltip.setContent(html).setLatLng(e.latlng)
        map.openTooltip(hoverTooltip);
    }).on('mouseout', () => {
        map.closeTooltip(hoverTooltip);        
    });
    if (key.includes('multi')) { setState({isMultiLayer: true});
    } else { setState({isMultiLayer: false}); }
    const polygonCentroids = [];
    filteredData.features.forEach(f => {
        const value = values[f.properties.index];
        if (value !== null && value !== undefined){ 
            const center = turf.centroid(f).geometry.coordinates;
            polygonCentroids.push({ lat: center[1], lng: center[0], value: value });
        }
    });
    setState({polygonCentroids: polygonCentroids});
    // Add click event to the layer
    layerMap.on('click', () => { setState({isClickedInsideLayer: true}); });
    // Adjust Colorbar Control
    updateColorbar(vmin, vmax, colorbarTitle, colorbarKey, colorbar_color(), colorbar_title(), colorbar_label());
    // Save layer
    setState({mapLayer: featureIds});
    return layerMap;
}

export async function plot2DMapStatic(key, colorbarTitle, colorbarKey) {
    startLoading();
    const data = await loadData(key, 'static', getState().projectName);
    if (data.status === 'error') { showLeafletMap(); alert(data.message); return; }
    setState({isPlaying: false});
    // Hide timeslider
    timeControl().style.display = 'none'; substanceWindow().style.display = 'none';
    // Get the min and max values of the data
    const vmin = data.content.min_max[0], vmax = data.content.min_max[1];
    const meshes = data.content.meshes, values = data.content.values;
    layerMap = layerCreator(meshes, values, key, vmin, vmax, colorbarTitle, colorbarKey);
    map.addLayer(layerMap);
    showLeafletMap();
}

function buildFrameData(data) {
    const coordsArray = data.coordinates, result = [], values = data.values;
    for (let i = 0; i < coordsArray.length; i++) {
        const coords = coordsArray[i], val = values[i];
        let parts = [];
        if (typeof val === 'string') {
            const temp = val.replace(/[()]/g, '');
            parts = temp.split(',').map(s => parseFloat(s.trim()));
        } else if (Array.isArray(val)) { parts = val.map(Number); }
        if (!isNaN(parts[0]) && !isNaN(parts[1]) && !isNaN(parts[2])) {
            result.push({
                x: coords[0], y: coords[1], a: parts[0], b: parts[1], c: parts[2]
            });
        }
    }
    return result;
}

function vectorCreator(parsedData, vmin, vmax, title, colorbarKey, scale) {
    const layer = new L.CanvasLayer({ data: parsedData,
        drawLayer: function () {
            const ctx = this._ctx, map = this._map;
            const canvas = ctx.canvas, data = this.options.data;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (let i = 0; i < data.length; i++) {
                const pt = data[i];
                const p = map.latLngToContainerPoint([pt.y, pt.x]);
                if (p.x < 0 || p.x > canvas.width || p.y < 0 || p.y > canvas.height) continue;
                const dx = pt.a * scale, dy = -pt.b * scale;
                const length = Math.sqrt(dx * dx + dy * dy);
                if (length < 0.1) continue;
                const angle = Math.atan2(dy, dx);
                ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(angle);
                ctx.scale(length, length);
                const color = getColorFromValue(pt.c, vmin, vmax, colorbarKey);
                ctx.strokeStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
                ctx.lineWidth = 1 / length;
                ctx.stroke(arrowShape); ctx.restore();
            }
        }
    });
    // Adjust Colorbar Control
    colorbar_vector_scaler().innerHTML = `Scaler: ${scale}`;
    updateColorbar(vmin, vmax, title, colorbarKey, colorbar_vector_color(), 
                    colorbar_vector_title(), colorbar_vector_label());
    return layer;
}

function initDynamicMap(query, key_below, key_above, data_below, data_above, 
    colorbarTitleBelow, colorbarTitleAbove, colorbarKeyBelow, colorbarKeyAbove, scale) {
    // Clear map
    map.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) map.removeLayer(layer); });
    timeControl().style.display = "flex"; // Show time slider
    // Hide colorbar control
    colorbar_container().style.display = "none"; colorbar_vector_container().style.display = "none";
    // Destroy slider if it exists
    if (slider().noUiSlider) slider().noUiSlider.destroy();
    // Stop animation if running
    if (getState().isPlaying) {
        clearInterval(getState().isPlaying); setState({isPlaying: null});
        playBtn().textContent = "▶ Play";
    }
    let timestamp = null, currentIndex, vminBelow, vmaxBelow, vminAbove, vmaxAbove,
        lastRequestId = 0, debounceTimer = null;
    // Process below layer
    if (data_below !== null) {
        // Get min and max values
        vminBelow = data_below.min_max[0]; vmaxBelow = data_below.min_max[1];
        timestamp = data_below.timestamps; currentIndex = timestamp.length - 1;
        const meshes = data_below.meshes, values = data_below.values;
        if (layerMap) map.removeLayer(layerMap);
        layerMap = layerCreator(meshes, values, key_below, vminBelow,
            vmaxBelow, colorbarTitleBelow, colorbarKeyBelow);
        map.addLayer(layerMap);
        colorbar_container().style.display = "block";
    }
    // Process above layer
    if (data_above !== null) {
        // Get min and max values
        vminAbove = data_above.min_max[0], vmaxAbove = data_above.min_max[1];
        timestamp = data_above.timestamps; currentIndex = timestamp.length - 1;
        if (layerAbove) map.removeLayer(layerAbove); // Remove previous layer
        parsedFrame = buildFrameData(data_above);
        layerAbove = vectorCreator(parsedFrame, vminAbove, vmaxAbove,
            colorbarTitleAbove, colorbarKeyAbove, scale);
        map.addLayer(layerAbove);
        colorbar_vector_container().style.display = "block";
    }
    // Create Slider
    const maxIndex = timestamp.length - 1;
    noUiSlider.create(slider(), {
        start: currentIndex, step: 1,
        range: { min: 0, max: maxIndex },
        tooltips: [{
            to: value => timestamp[Math.round(value)],
            from: value => timestamp.indexOf(value)
        }]
    });
    // Slider update event (with debounce to avoid multiple requests)
    const handleSliderUpdate = async (values, handle, unencoded) => {
        const rawIndex = unencoded[handle];
        const newIndex = Math.round(rawIndex);
        const safeIndex = Math.max(0, Math.min(newIndex, maxIndex));
        currentIndex = safeIndex;
        // Token to avoid race conditions
        const requestId = ++lastRequestId;
        if (data_below && layerMap) {
            const frame_below = await sendQuery('load_general_dynamic', {query: `${query}|${currentIndex}`, 
                key: key_below, projectName: getState().projectName});
            if (requestId !== lastRequestId) return;
            if (frame_below.status === 'error') return alert(frame_below.message);
            let parsedFrame = decodeArray(frame_below.content.values, 3);
            if (key_below === 'wd_single_dynamic') parsedFrame = parsedFrame.map(v => -v);
            updateMapByTime(layerMap, parsedFrame, vminBelow, vmaxBelow, colorbarKeyBelow);
        }
        if (data_above && layerAbove) {
            const frame_above = await sendQuery('load_vector_dynamic', {query: currentIndex, 
                key: key_above, projectName: getState().projectName});
            if (frame_above.status === 'error') return alert(frame_above.message);
            parsedFrame = buildFrameData(frame_above.content);
            layerAbove.options.data = parsedFrame; layerAbove._redraw();
        }
    };
    // Debounce wrapper
    slider().noUiSlider.on('update', async (values, handle, unencoded) => {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => { handleSliderUpdate(values, handle, unencoded); }, 80);
    });
    // Play/Pause button
    if (playHandlerAttached && playHandlerRef) {
        // Remove previous handler
        playBtn().removeEventListener("click", playHandlerRef);
        playHandlerAttached = false;
    }
    playHandlerRef = () => {
        if (getState().isPlaying) {
            clearInterval(getState().isPlaying); setState({isPlaying: null});
            playBtn().textContent = "▶ Play"; return;
        }
        // Get current index
        let idx = Math.round(slider().noUiSlider.get());
        const len = maxIndex + 1;
        const speed = 1000/parseFloat(timeSpeed().value || 1);
        const interval = setInterval(() => {
            idx = (idx + 1) % len;
            slider().noUiSlider.set(idx);
        }, speed);
        setState({isPlaying: interval});
        playBtn().textContent = "⏸ Pause";
    };
    playBtn().addEventListener("click", playHandlerRef);
    playHandlerAttached = true;
}

function initScaler() {
    // Initialize vector scale
    if (scaler_value() === null) {
        setState({scalerValue: 1000});
        return getState().scalerValue;
    };
    if (parseFloat(scaler_value().value) <= 0) {
        alert('Wrong scaler value. Please check the scaler object.'); return;
    }
    getState().scalerValue = scaler_value().value;
    // Store scaler value
    setState({scalerValue: scaler_value().value}); 
    return parseFloat(getState().scalerValue);
}

export async function plot2DMapDynamic(waterQuality, query, key, colorbarTitle, colorbarKey) {
    startLoading('Preparing Dynamic Map. Please wait...'); scale = initScaler();
    let data_below = null, data_above = null, colorbarTitleAbove = null, colorbarKeyAbove = null, key_below = key, key_above = null;
    setState({showedQuery: key}); setState({isHYD: waterQuality});  // Set HYD flag
    // Process below layer
    const dataBelow = await sendQuery('load_general_dynamic', {query: `${query}|load`, key: key, projectName: getState().projectName});
    if (dataBelow.status === 'error') { showLeafletMap(); alert(dataBelow.message); return; }
    data_below = dataBelow.content; data_below.values = decodeArray(data_below.values, 3);
    // If data is water depth, reverse values in below layer    
    if (key === 'wd_single_dynamic') {
        data_below.values = data_below.values.map(v => -v);
        data_below.min_max = [-data_below.min_max[1], -data_below.min_max[0]];
    }
    if (waterQuality) {getState().vectorSelected = '';}
    if (getState().vectorSelected !== '' && key.includes('multi')) {
        const vectorSelector = document.getElementById("vector-selector");
        const layerSelector = document.getElementById("layer-selector");
        if (vectorSelector.selectedOptions[0].text === 'Velocity') { // Process above data for velocity
            const title = layerSelector.value==='-1' ? `Layer: ${layerSelector.selectedOptions[0].text}` 
                : `${layerSelector.selectedOptions[0].text}`;
            colorbarTitleAbove = `${vectorSelector.selectedOptions[0].text} (m/s)\n${title}`; colorbarKeyAbove = 'vector';
        }
        key_above = layerSelector.value;
        const dataAbove = await sendQuery('load_vector_dynamic', {query: 'load', key: key_above, projectName: getState().projectName});
        data_above = dataAbove.content; data_above.values = decodeArray(data_above.values, 3);
    }
    initDynamicMap(query, key_below, key_above, data_below, data_above, colorbarTitle, colorbarTitleAbove, colorbarKey, colorbarKeyAbove, scale);
    showLeafletMap();
}

export async function plot2DVectorMap(query, key, colorbarTitleAbove, colorbarKey) {
    startLoading('Preparing Dynamic Vector Map. Please wait...'); scale = initScaler();
    const data = await sendQuery('load_vector_dynamic', {query: query, key: key, projectName: getState().projectName});
    if (data.status === 'error') { showLeafletMap(); alert(data.message); return; }
    if (layerMap) map.removeLayer(layerMap); layerMap = null;
    if (layerAbove) map.removeLayer(layerAbove); layerAbove = null;
    const colorbarTitle = layerSelector().value==='-1' ? `${colorbarTitleAbove}\nLayer: ${layerSelector().selectedOptions[0].text}` 
        : `${colorbarTitleAbove}\n${layerSelector().selectedOptions[0].text}`;
    initDynamicMap(query, null, key, null, data.content, null, colorbarTitle, null, colorbarKey, scale);
    showLeafletMap();
}