import { loadData, getColorFromValue, updateColorbar, getMinMaxFromGeoJSON } from "./utils.js";
import { updateMapByTime, colorbar_container, colorbar_vector_container } from "./utils.js";
import { startLoading, showLeafletMap, L, map } from "./mapManager.js";
import { arrowShape, getState, setState } from "./constants.js";
import { drawChart } from "./chartManager.js";
import { mapPoint } from "./queryManager.js";
import { scaler_value } from "./dynamicMapManager.js";


export const timeControl = () => document.getElementById('time-controls');
const slider = () => document.getElementById("time-slider");
const playBtn = () => document.getElementById("play-btn");


export let layerAbove = null;
let layerMap = null,  currentIndex = 0, playHandlerAttached = false;
let prevPolygon = null, prevColor = null, parsedDataAllFrames = '', txt = '';

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

async function plotMultilayer(id, key, titleY) {
    startLoading();
    try {
        const response = await fetch('/select_polygon', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({key: key, id: id})});
        const data = await response.json();
        if (data.status === "error") {alert(data.message); return; }
        drawChart(data.content, 'Simulated Values at Layers', 'Time', titleY, false);
    } catch (error) {alert(error);}
    showLeafletMap();
}

// Create map layer
function layerCreator(data, key, timestamp, vmin, vmax, colorbarTitle, colorbarKey, colorbarScaler, swap) {
    if (layerMap) map.removeLayer(layerMap);  // Remove previous layer
    colorbar_container().style.display = "block";
    const getColumnName = () => Array.isArray(timestamp) ? timestamp[currentIndex] : timestamp;
    // Remove previous featureMap
    setState({featureMap: {}});
    // Create feature to access quickly
    const featureIds = [];
    setState({lastFeatureColors: {}});
    // Data filter
    const filteredFeatures = data.features.filter(f => {
        const value = f.properties[getColumnName()];
        return value !== null && value !== undefined;
    });
    const filteredData = { ...data, features: filteredFeatures};
    filteredData.features.forEach(f => {
        const value = getState().featureMap;
        value[f.properties.index] = f;
        setState({featureMap: value});
        featureIds.push(f.properties.index);
    });
    // Create map layer
    layerMap = L.vectorGrid.slicer(filteredData, {
        rendererFactory: L.canvas.tile, vectorTileLayerStyles: {
            sliced: function(properties) {
                const value = properties[getColumnName()];
                // Ignore null values
                if (value === null || value === undefined) return { fill: false, weight: 0, opacity: 0 };
                const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey, swap);
                getState().lastFeatureColors[properties.index] = `${r},${g},${b},${a}`;
                setState({lastFeatureColors: getState().lastFeatureColors});
                return {
                    fill: true, fillColor: `rgb(${r},${g},${b})`,
                    fillOpacity: a, weight: 0, opacity: 1
                };
            },
        }, interactive: true, maxZoom: 18, getFeatureId: f => {
            featureIds.push(f.properties.index);
            return f.properties.index;
        }
    });
    if (key.includes('multi')) {
        txt = `<br>Select object to see values in each layer`;
        setState({isMultiLayer: true}); setState({isPathQuery: false});
        setState({isPointQuery: false});
    } else {
        setState({isMultiLayer: false});
        txt = ''; 
        const polygonCentroids = [];
        filteredData.features.forEach(f => {
            const value = f.properties[getColumnName()];
            if (value !== null && value !== undefined){ 
                const center = turf.centroid(f).geometry.coordinates;
                polygonCentroids.push({
                    lat: center[1], lng: center[0], value: value
                });
            }
        });
        setState({polygonCentroids: polygonCentroids});
    }
    const hoverTooltip = L.tooltip({ direction: 'top', sticky: true });
    layerMap.on('mouseover', function(e) {
        if (getState().isPlaying) return;
        const props = e.layer.properties;
        const value = props[getColumnName()];
        // Show tooltip
        const html = `<div style="text-align: center;">
                <b>${colorbarTitle}:</b> ${value ?? 'N/A'}${txt}
            </div>`;
        hoverTooltip.setContent(html).setLatLng(e.latlng)
        map.openTooltip(hoverTooltip);
    }).on('mouseout', function(e) {
        map.closeTooltip(hoverTooltip);
        layerMap.resetFeatureStyle(e.layer._id);
    });
    // Add click event to the layer
    layerMap.on('click', function(e) {
        setState({isClickedInsideLayer: true});
        const props = e.layer.properties;
        mapPoint({ ...e, layerProps: props });
        if (key.includes('multi')) {
            // Reset previous polygon if exists
            if (prevPolygon){
                prevPolygon.setStyle({
                    fillColor: prevColor,
                    fillOpacity: prevPolygon.options.fillOpacity,
                    color: prevPolygon.options.color
                });
            }
            // Store current polygon
            prevPolygon = e.layer;
            prevColor = e.layer.options.fillColor;
            // Get index of the feature
            const selectedFeatureId = props.index;
            // Highlight feature 
            layerMap.resetFeatureStyle(e.layer._id);
            e.layer.setStyle({ fillColor: 'red', color: 'yellow', fillOpacity: 1 });
            // Load data to plot
            plotMultilayer(selectedFeatureId, key, colorbarTitle);
        }
    });
    // Adjust Colorbar Control
    updateColorbar(vmin, vmax, colorbarTitle, colorbarKey, colorbarScaler, swap);
    // Assign values to use later
    setState({mapLayer: featureIds});
    layerMap.getColumnName = getColumnName; setState({storedLayer: layerMap});
    return layerMap;
}

export async function plot2DMapStatic(filename, key, colorbarTitle, colorbarKey, 
                                        colorbarScaler='normal', swap=false,) {
    startLoading();
    const data = await loadData(filename, key);
    if (data.status === 'error') { showLeafletMap(); alert(data.message); return; }
    setState({isPlaying: false});
    // Hide timeslider
    timeControl().style.display = 'none';
    // Get the min and max values of the data
    const values = data.content.features.map(f => f.properties.value)
                    .filter(v => typeof v === 'number' && !isNaN(v));
    const vmin = Math.min(...values), vmax = Math.max(...values);
    layerMap = layerCreator(data.content, key, "value", vmin, vmax, colorbarTitle, colorbarKey, colorbarScaler, swap);
    map.addLayer(layerMap);
    showLeafletMap();
}

function buildFrameData(data, i) {
    const coordsArray = data.coordinates, values = data.values[i];
    const result = [];    
    for (let i = 0; i < coordsArray.length; i++) {
        const coords = coordsArray[i];
        const val = values[i];
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

function vectorCreator(parsedData, vmin, vmax, title, colorbarKey, colorbarScaler, swap) {
    if (layerAbove) map.removeLayer(layerAbove);  // Remove previous layer
    const scale = parseFloat(getState().scalerValue);
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
    updateColorbar(vmin, vmax, title, colorbarKey, colorbarScaler, swap);
    return layer;
}

function initDynamicMap(key, data_below, data_above, colorbarTitleBelow, colorbarTitleAbove,
                        colorbarKeyBelow, colorbarKeyAbove, colorbarScaler, swap) {
    timeControl().style.display = "flex"; // Show time slider
    // Hide colorbar control
    colorbar_container().style.display = "none";
    colorbar_vector_container().style.display = "none";
    let timestamp, currentIndex, vminBelow, vmaxBelow, vminAbove, vmaxAbove;
    // Destroy slider if it exists
    if (slider().noUiSlider) { 
        slider().noUiSlider.destroy();
        clearInterval(getState().isPlaying); setState({isPlaying: null});
        playBtn().textContent = "▶ Play";
    }
    // Process below layer
    if (data_below !== null) {
        colorbar_container().style.display = "block";
        // Get column name
        const allColumns = Object.keys(data_below.features[0].properties);
        timestamp = allColumns.filter(k => !k.includes("index"));
        // Get min and max values
        const minmax = getMinMaxFromGeoJSON(data_below, timestamp);
        vminBelow = minmax.min; vmaxBelow = minmax.max;
        currentIndex = timestamp.length - 1;
        layerMap = layerCreator(data_below, key, timestamp, vminBelow, vmaxBelow, 
                                colorbarTitleBelow, colorbarKeyBelow, colorbarScaler, swap);
        map.addLayer(layerMap);
    }
    // Process above layer
    if (data_above) {
        colorbar_vector_container().style.display = "block";
        // Plot above layer directly
        timestamp = data_above.time;
        // Get min and max values
        vminAbove = data_above.min_max[0], vmaxAbove = data_above.min_max[1];
        currentIndex = timestamp.length - 1;
        parsedDataAllFrames = timestamp.map((_, i) => buildFrameData(data_above, i));
        layerAbove = vectorCreator(parsedDataAllFrames[currentIndex], vminAbove, vmaxAbove, 
                                    colorbarTitleAbove, colorbarKeyAbove, colorbarScaler, swap);
        map.addLayer(layerAbove);
    }
    // Recreate Slider
    noUiSlider.create(slider(), {
        start: currentIndex, step: 1,
        range: { min: 0, max: timestamp.length - 1 },
        tooltips: [{
            to: value => timestamp[Math.round(value)],
            from: value => timestamp.indexOf(value)
        }]
    });
    // Update map by time
    slider().noUiSlider.on('update', (values, handle, unencoded) => {
        currentIndex = Math.round(unencoded[handle]);
        if (data_below && layerMap) updateMapByTime(layerMap, timestamp, currentIndex, 
                                        vminBelow, vmaxBelow, colorbarKeyBelow, swap);
        if (data_above && layerAbove) {
            layerAbove.options.data = parsedDataAllFrames[currentIndex];
            layerAbove._redraw();
        }
    });
    // Play/Pause button
    if (!playHandlerAttached) {
        playBtn().addEventListener("click", () => {
            if (getState().isPlaying) {
                clearInterval(getState().isPlaying); setState({isPlaying: null});
                playBtn().textContent = "▶ Play";
            } else {
                currentIndex = parseInt(Math.floor(slider().noUiSlider.get()));
                const playing = setInterval(() => {
                    currentIndex = (currentIndex + 1) % timestamp.length;
                    slider().noUiSlider.set(currentIndex);
                }, 800);
                setState({isPlaying: playing});
                playBtn().textContent = "⏸ Pause";
            }
        });
        playHandlerAttached = true;
    }
}

export async function plot2DMapDynamic(waterQuality, filename, key, colorbarTitle, colorbarKey, colorbarScaler='normal') {
    startLoading('Preparing Dynamic Map. Please wait...');
    let data_below = null, data_above = null, swap = false;
    let colorbarTitleAbove = null, colorbarKeyAbove = null;
    if (key === 'wd_dynamic') {swap = true;} else {swap = false;}
    // Process below layer
    const dataBelow = await loadData(filename, key);
    if (dataBelow.status === 'error') { showLeafletMap(); alert(dataBelow.message); return; }
    data_below = dataBelow.content;
    // If data is not water quality
    if (!waterQuality && getState().vectorMain) {
        let vectorName = getState().vectorMain, vectorKey = getState().vectorSelected;
        colorbarTitleAbove = vectorName;
        // Process above data
        if (vectorName === 'Velocity' && vectorKey) {
            vectorName = `${vectorKey}_velocity`;
            vectorKey = 'velocity';
        }
        const dataAbove = await loadData(vectorName, vectorKey);
        if (dataAbove.status === 'error') { showLeafletMap(); alert(dataAbove.message); return; }
        data_above = dataAbove.content;
        colorbarKeyAbove = vectorKey;
    }
    initDynamicMap(key, data_below, data_above, colorbarTitle, colorbarTitleAbove, 
                    colorbarKey, colorbarKeyAbove, colorbarScaler, swap);
    showLeafletMap();
}

export async function plot2DVectorMap(filename, key, colorbarTitleAbove, colorbarKey, colorbarScaler='vector') {
    const vectorName = getState().vectorMain, vectorKey = getState().vectorSelected;
    if ((vectorName === 'Velocity' && !vectorKey) || (!vectorName)) return;
    if ((!scaler_value().value)||(parseFloat(scaler_value().value) <= 0)) {
        alert('Wrong scaler value. Please check the scaler value.'); return;
    }
    // Store scaler value
    setState({scalerValue: scaler_value().value});
    startLoading('Preparing Dynamic Map. Please wait...');
    if (layerMap) map.removeLayer(layerMap);
    const data = await loadData(filename, key);
    if (data.status === 'error') { showLeafletMap(); alert(data.message); return; }
    initDynamicMap(key, null, data.content, null, colorbarTitleAbove, 
                    null, colorbarKey, colorbarScaler, false);
    showLeafletMap();
}