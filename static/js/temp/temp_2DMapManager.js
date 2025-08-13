import { loadData, getColorFromValue, updateColorbar, updateMapByTime, getMinMaxFromGeoJSON, toNumber } from "./utils.js";
import { startLoading, showLeafletMap, L, map } from "./temp_mapManager.js";
import { setMapLayer, getIsPathQuery, setIsClickedInsideLayer, setStoredLayer } from "./temp_constants.js";
import { setPolygonCentroids, getIsPlaying, setIsPlaying, setIsPath } from "./temp_constants.js";
import { vectorObjectMain, vectorObjectSubMain } from "./temp_uiManager.js";
import { drawChart } from "./temp_chartManager.js";
import { deactivePathQuery, deactivePointQuery, mapPath } from "./temp_queryManager.js";


const timeControl = () => document.getElementById('time-controls');
const slider = () => document.getElementById("time-slider");
const playBtn = () => document.getElementById("play-btn");


let layerMap = null, currentIndex = 0, playHandlerAttached = false, txt = '', swap = false;
let prevPolygon = null, prevColor = null;

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
        if (data.status === "ok") {
            drawChart(data.content, 'Simulated Values at Layers', 'Time', titleY, 'All', false);
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    showLeafletMap();
}

// Create map layer
function layerCreator(data, key, timestamp, vmin, vmax, colorbarTitle, colorbarKey, swap) {
    deactivePathQuery(); deactivePointQuery(); // Deactivate queries
    if (layerMap) map.removeLayer(layerMap);  // Remove previous layer
    const getColumnName = () => Array.isArray(timestamp) ? timestamp[currentIndex] : timestamp;
    const featureIds = [];
    layerMap = L.vectorGrid.slicer(data, {
        rendererFactory: L.canvas.tile, vectorTileLayerStyles: {
            sliced: function(properties) {
                const value = properties[getColumnName()];
                const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey, swap);
                return {
                    fill: true, fillColor: `rgb(${r},${g},${b})`, fillOpacity: a,
                    weight: 0, opacity: 1
                };
            },
        }, interactive: true, maxZoom: 18, getFeatureId: f => {
            featureIds.push(f.properties.index);
            return f.properties.index;
        }
    });
    if (key.includes('multi')) {
        txt = `<br>Select object to see values in each layer`; setIsPath(false);
    } else {
        setIsPath(true); txt = '';
        const polygonCentroids = data.features.map(f => {
            const center = turf.centroid(f).geometry.coordinates;
            return {
                lat: center[1], lng: center[0],
                value: f.properties[getColumnName()],
            };
        });
        setPolygonCentroids(polygonCentroids);
    }
    const hoverTooltip = L.tooltip({ direction: 'top', sticky: true });
    layerMap.on('mouseover', function(e) {
        if (getIsPlaying()) return;
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
        setIsClickedInsideLayer(true);
        const props = e.layer.properties;
        if (getIsPathQuery()) {
            mapPath({ ...e, layerProps: props });
        }
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
    updateColorbar(vmin, vmax, colorbarTitle, colorbarKey, swap);
     // Assign values to use later
    setMapLayer(featureIds);
    layerMap.getColumnName = getColumnName; setStoredLayer(layerMap);
    return layerMap;
}

export async function plot2DMapStatic(filename, key, colorbarTitle, colorbarKey, swap=false) {
    startLoading();
    const data = await loadData(filename, key);
    setIsPlaying(false);
    // Hide timeslider
    timeControl().style.display = 'none';
    // Convert string to number
    data.content.features.forEach(f => {
        Object.keys(f.properties).forEach(k => f.properties[k] = toNumber(f.properties[k]));
    });
    // Get the min and max values of the data
    const values = data.content.features.map(f => f.properties.value)
                    .filter(v => typeof v === 'number' && !isNaN(v));
    const vmin = Math.min(...values), vmax = Math.max(...values);
    const mapLayer = layerCreator(data.content, key, "value", vmin, vmax, colorbarTitle, colorbarKey, swap);
    map.addLayer(mapLayer);
    showLeafletMap();
}

function initDynamicMap(key, data, colorbarTitle, colorbarKey, swap) {
    timeControl().style.display = "flex"; // Show time slider
    // Get column name
    const allColumns = Object.keys(data.features[0].properties);
    const timestamp = allColumns.filter(k => !k.includes("index"));
    // Get min and max values
    const { min: vmin, max: vmax } = getMinMaxFromGeoJSON(data, timestamp);
    currentIndex = timestamp.length - 1;
    // Destroy slider if it exists
    if (slider().noUiSlider) { 
        slider().noUiSlider.destroy();
        clearInterval(getIsPlaying()); setIsPlaying(null);
        playBtn().textContent = "▶ Play";
    }
    const layer = layerCreator(data, key, timestamp, vmin, vmax, colorbarTitle, colorbarKey, swap);
    map.addLayer(layer);
    // Recreate Slider
    noUiSlider.create(slider(), {
        start: currentIndex, step: 1,
        range: { min: 0, max: timestamp.length - 1 },
        tooltips: {
            to: value => timestamp[Math.round(value)],
            from: value => timestamp.indexOf(value)
        }
    });
    // Update map by time
    slider().noUiSlider.on('update', (values, handle, unencoded) => {
        currentIndex = Math.round(unencoded[handle]);
        updateMapByTime(data, layer, timestamp, currentIndex, vmin, vmax, colorbarKey, swap);
    });
    // Play/Pause button
    if (!playHandlerAttached) {
        playBtn().addEventListener("click", () => {
            if (getIsPlaying()) {
                clearInterval(getIsPlaying()); setIsPlaying(null);
                playBtn().textContent = "▶ Play";
            } else {
                currentIndex = parseInt(Math.floor(slider().noUiSlider.get()));
                const isPlaying = setInterval(() => {
                    currentIndex = (currentIndex + 1) % timestamp.length;
                    slider().noUiSlider.set(currentIndex);
                }, 800);
                setIsPlaying(isPlaying);
                playBtn().textContent = "⏸ Pause";
            }
        });
        playHandlerAttached = true;
    }
}


export async function plot2DMapDynamic(filename, key, colorbarTitle, colorbarKey) {
    startLoading();
    const vectorMainIndex = vectorObjectMain().selectedIndex;
    // Process vector data
    if (vectorMainIndex === 1) {
        const vectorSubMainIndex = vectorObjectSubMain().selectedIndex;
        console.log(vectorMainIndex, vectorSubMainIndex);



    } else if (vectorMainIndex > 2) {
        
    }
    // Process dynamic map
    const data = await loadData(filename, key);
    // Convert string to number
    data.content.features.forEach(f => {
        Object.keys(f.properties).forEach(k => f.properties[k] = toNumber(f.properties[k]));
    });
    if (key === 'wd_dynamic') {swap = true;} else {swap = false;}
    initDynamicMap(key, data.content, colorbarTitle, colorbarKey, swap);
    showLeafletMap();
}





// export function vectorCreator(parsedData, vmin, vmax, title, colorbarKey, key='velocity') {
//     // if (layerStatic && map.hasLayer(layerStatic)) {
//     //     map.removeLayer(layerStatic); layerStatic = null;
//     // };
//     // if (layerDynamic && map.hasLayer(layerDynamic)) {
//     //     map.removeLayer(layerDynamic); layerDynamic = null;
//     // };
//     const scale = 400, arrowLength = 1;
//     const layer = new L.CanvasLayer({ data: parsedData,
//         drawLayer: function () {
//             const ctx = this._ctx, map = this._map;
//             const canvas = ctx.canvas, data = this.options.data;
//             ctx.clearRect(0, 0, canvas.width, canvas.height);
//             for (let i = 0; i < data.length; i++) {
//                 const pt = data[i];
//                 const p = map.latLngToContainerPoint([pt.y, pt.x]);
//                 if (p.x < 0 || p.x > canvas.width || p.y < 0 || p.y > canvas.height) continue;
//                 const dx = pt.a * scale, dy = -pt.b * scale;
//                 const length = Math.sqrt(dx * dx + dy * dy);
//                 if (length < 0.1) continue;
//                 const angle = Math.atan2(dy, dx);
//                 ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(angle);
//                 ctx.scale(length / arrowLength, length / arrowLength);
//                 if (key === "velocity") {
//                     const color = getColorFromValue(pt.c, vmin, vmax, colorbarKey);
//                     ctx.strokeStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
//                 } else {
//                     ctx.strokeStyle = "rgba(255, 255, 255, 1)";
//                 }
//                 ctx.lineWidth = 1 / (length / arrowLength);
//                 ctx.stroke(arrowShape); ctx.restore();
//             }
//         }
//     });
//     // Adjust Colorbar Control
//     updateColorbar(vmin, vmax, title, colorbarKey);
//     return layer;
// }



