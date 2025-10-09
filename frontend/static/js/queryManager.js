import { startLoading, showLeafletMap, map, L, ZOOM } from "./mapManager.js";
import { degree_decimals, n_decimals, getState, setState } from "./constants.js";
import { loadData, colorbar_title } from "./utils.js";
import { plotChart, plotWindow, plotProfile} from "./chartManager.js";

let currentMarker = null, pathLine = null, marker = null, pointContainer = [], selectedMarkers = [];

const mapContainer = () => map.getContainer();
const stationOption = () => document.getElementById("hyd-obs-checkbox");
const waqObsOption = () => document.getElementById("waq-obs-checkbox");
const waqLoadsOption = () => document.getElementById("waq-loads-checkbox");
const sourceOption = () => document.getElementById("source-checkbox");
const crossSectionOption = () => document.getElementById("cross-section-checkbox");
const pointQueryCheckbox = () => document.getElementById("point-query");
const pathQueryCheckbox = () => document.getElementById("path-query");
const infoDetail = () => document.getElementById("infoDetails");
const infoContent = () => document.getElementById("infoDetailsContent");


function checkUpdater(setLayer, objCheckbox, checkFunction){
    objCheckbox.checked = getState()[setLayer] !== null;
    objCheckbox.addEventListener('change', async () => {
        if (objCheckbox.checked) { 
            const layer = await checkFunction();
            setState({[setLayer]: layer});
        } else { 
            const currentLayer = getState()[setLayer];
            if (currentLayer) { map.removeLayer(currentLayer); }
            setState({[setLayer]: null}); }
    });
}

export function queryUpdate(){
    // checkUpdater("stationLayer", stationOption(), activeStationCheck);
    // checkUpdater("wqObsLayer", waqObsOption(), activeWAQObsCheck);
    checkUpdater("wqLoadsLayer", waqLoadsOption(), activeWAQLoadsCheck);
    // checkUpdater("sourceLayer", sourceOption(), activeSourceCheck);
    // checkUpdater("crosssectionLayer", crossSectionOption(), activeCrossSectionCheck);
}


// ============================ Station Manager ============================
// async function activeStationCheck() {
//     startLoading('Reading Hydrodynamic Observation Points from Database. Please wait...'); // Show spinner
//     const data = await loadData('', 'hyd_station'); // Load data
//     if (data.status === "error") { alert(data.message); return; }
//     if (getState().stationLayer) { map.removeLayer(getState().stationLayer); }
//     // Add station layer to the map
//     const layer = L.geoJSON(data.content, {
//         // Custom marker icon
//         pointToLayer: function (feature, latlng) {
//             const customIcon = L.icon({
//                 iconUrl: `static/images/station.png?v=${Date.now()}`,
//                 iconSize: [20, 20], popupAnchor: [1, -34],
//             });
//             const marker = L.marker(latlng, {icon: customIcon});
//             const stationId = feature.properties.name || 'Unknown';
//             // Add tooltip
//             const value = `<div style="text-align: center; weight: bold;">
//                     <b>${stationId}</b><br>Select object to see more parameters
//                 </div>`;
//             marker.bindTooltip(value, {
//                 permanent: false, direction: 'top', offset: [0, 0]
//             });
//             // Add popup
//             const popupContent = `<div style="font-family: Arial;">
//                 <h3 style="text-align: center;">${stationId}</h3>
//                 <hr style="margin: 5px 0 5px 0;">
//                 <ul style="left: 0; cursor: pointer; padding-left: 0; list-style: none;">
//                     <li><a class="in-situ" data-info="temp*${stationId}*station_name|Temperature (°C)">• Temperature</a></li>
//                     <li><a class="in-situ" data-info="sal*${stationId}*station_name|Salinity (PSU)">• Salinity</a></li>
//                     <li><a class="in-situ" data-info="cont*${stationId}*station_name|Contaminant (g/L)">• Contaminant</a></li>
//                 </ul>
//             </div>`;
//             marker.bindPopup(popupContent, {offset: [0, 40]});
//             return marker;
//         }
//     });
//     map.addLayer(layer);
//     // Zoom to the extent of the station layer
//     map.setView(layer.getBounds().getCenter(), ZOOM);
//     showLeafletMap(); // Hide the spinner and show the map
//     return layer;
// }

// async function activeWAQObsCheck() {
//     startLoading('Loading Water Quality Observation Points from Database. Please wait...');
//     const data = await loadData('', 'wq_obs');
//     if (data.status === "error") { alert(data.message); return; }
//     if (getState().wqObsLayer) { map.removeLayer(getState().wqObsLayer); }
//     const layer = L.geoJSON(data.content, {
//         // Custom marker icon
//         pointToLayer: function (feature, latlng) {
//             const customIcon = L.icon({
//                 iconUrl: `static/images/waq_obs.png?v=${Date.now()}`,
//                 iconSize: [27, 27], popupAnchor: [1, -34],
//             });
//             const marker = L.marker(latlng, {icon: customIcon});
//             const stationId = feature.properties.name || 'Unknown';
//             // Add tooltip
//             const value = `<div style="text-align: center; weight: bold;">
//                     <b>${stationId}</b>
//                 </div>`;
//             marker.bindTooltip(value, {
//                 permanent: false, direction: 'top', offset: [0, 0]
//             });
//             return marker;
//         }
//     });
//     map.addLayer(layer);
//     map.setView(layer.getBounds().getCenter(), ZOOM);
//     showLeafletMap();
//     return layer;
// }

async function activeWAQLoadsCheck() {
    startLoading('Loading Loads of Water Quality Observation Points from Database. Please wait...');
    const data = await loadData('', 'wq_loads');
    if (data.status === "error") { alert(data.message); return; }
    if (getState().wqLoadsLayer) { map.removeLayer(getState().wqLoadsLayer); }
    const layer = L.geoJSON(data.content, {
        // Custom marker icon
        pointToLayer: function (feature, latlng) {
            const customIcon = L.icon({
                iconUrl: `static/images/waq_loads.png?v=${Date.now()}`,
                iconSize: [20, 20], popupAnchor: [1, -34],
            });
            const marker = L.marker(latlng, {icon: customIcon});
            const stationId = feature.properties.name || 'Unknown';
            // Add tooltip
            const value = `<div style="text-align: center; weight: bold;">
                    <b>${stationId}</b>
                </div>`;
            marker.bindTooltip(value, {
                permanent: false, direction: 'top', offset: [0, 0]
            });
            return marker;
        }
    });
    map.addLayer(layer);
    map.setView(layer.getBounds().getCenter(), ZOOM);
    showLeafletMap();
    return layer;
}


// async function activeSourceCheck() {
//     startLoading('Reading Sources from Database. Please wait...');
//     const data = await loadData('', 'sources');
//     if (data.status === "error") { alert(data.message); return; }
//     if (getState().sourceLayer) { map.removeLayer(getState().sourceLayer); }
//     const layer = L.geoJSON(data.content, {
//         pointToLayer: function (feature, latlng) {
//             const customIcon = L.icon({
//                 iconUrl: `static/images/source.png?v=${Date.now()}`,
//                 iconSize: [20, 20], popupAnchor: [1, -34],
//             });
//             const marker = L.marker(latlng, {icon: customIcon});
//             const sourceId = feature.properties.name || 'Unknown';
//             const value = `<div style="text-align: center;"><b>${sourceId}</b></div>`;
//             marker.bindTooltip(value, {
//                 permanent: false, direction: 'top', offset: [0, 0]
//             });
//             return marker;
//         }
//     });
//     map.addLayer(layer);
//     map.setView(layer.getBounds().getCenter(), ZOOM);
//     showLeafletMap();
//     return layer;
// }

// async function activeCrossSectionCheck() {
//     startLoading('Reading Cross Sections from Database. Please wait...');
//     const data = await loadData('', 'crosssections');
//     if (data.status === "error") { alert(data.message); showLeafletMap(); return; }
//     if (getState().crosssectionLayer) { map.removeLayer(getState().crosssectionLayer); }
//     const layer = L.geoJSON(data.content, { color: 'blue', weight: 3 });
//     map.addLayer(layer);
//     map.setView(layer.getBounds().getCenter(), ZOOM);
//     showLeafletMap();
//     return layer;
// }

// ============================ Point Manager ============================
// function checkPoint(){
//     if (getState().isPointQuery) { pointQueryCheckbox().checked = true; 
//     } else { pointQueryCheckbox().checked = false; deactivePointQuery(); }
// }
// export function deactivePointQuery() {
//     setState({isPointQuery: false});
//     if (pointQueryCheckbox()) pointQueryCheckbox().checked = false;
//     mapContainer().style.cursor = "grab";
//     infoDetail().style.display = "none";
//     infoContent().innerHTML = '';
//     plotWindow().style.display = "none";
//     if (currentMarker) { map.removeLayer(currentMarker); }
// }

// export function updatePointManager() {
//     // checkPoint();
//     // Add event listener to the point query checkbox
//     // pointQueryCheckbox().addEventListener('change', () => {
//     //     if (pointQueryCheckbox().checked) { activePointQuery();
//     //     } else deactivePointQuery();
//     // });
//     // Add event listener for point query
//     document.addEventListener('click', function(e) {
//         if (e.target && e.target.classList.contains('in-situ')) {
//             e.preventDefault();
//             const [query, colorbarTitle] = e.target.dataset.info.split('|');
//             const chartTitle = colorbarTitle.split('(')[0].trim();
//             plotChart(query, '_in-situ', chartTitle, 'Time', colorbarTitle, false);
//         }
//     });
// }

// function activePointQuery(){
//     setState({isPointQuery: true});
//     if (!getState().isMultiLayer && getState().mapLayer) { 
//         infoDetail().style.display = "block";
//         deactivePathQuery();
//         mapContainer().style.cursor = "help";
//     } else {
//         alert("This function is not supported. Please check:\n" + 
//             "      1. One map layer must be loaded.\n" +
//             "      2. Only static and dynamic (with single layer) maps are supported.");
//         deactivePointQuery(); return;
//     }
// }

export function mapPoint(e) {
    if (!getState().isPointQuery) return;
    if (currentMarker) { map.removeLayer(currentMarker); }
    if (e.layerProps) {
        const lat = e.latlng.lat.toFixed(degree_decimals);
        const lng = e.latlng.lng.toFixed(degree_decimals);
        currentMarker = L.marker(e.latlng).addTo(map);
        const fieldName = getState().storedLayer.getColumnName();
        const value = e.layerProps[fieldName] ?? 'N/A';
        const html = `<div style="display: flex; justify-content: space-between;">
            <div style="padding-left: 10px;">Location:</div>
            <div style="padding-right: 10px;">${lng}, ${lat}</div>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <div style="padding-left: 10px;">${colorbar_title().textContent}:</div>
            <div style="padding-right: 10px;">${value}</div>
        </div>`;
        infoContent().innerHTML = html;
        infoDetail().style.height = 'auto';
        setState({isClickedInsideLayer: false});
    }
}

// ============================ Path Manager ============================
function checkPath(){
    if (getState().isPathQuery) { pathQueryCheckbox().checked = true; 
    } else { pathQueryCheckbox().checked = false; deactivePathQuery(); }
}

export function updatePathManager() {
    checkPath();
    // Add event listener to the point query checkbox
    pathQueryCheckbox().addEventListener('change', () => {
        if (pathQueryCheckbox().checked) { activePathQuery();
        } else deactivePathQuery();
    });
}

export function deactivePathQuery() {
    setState({isPathQuery: false});
    if (pathQueryCheckbox()) pathQueryCheckbox().checked = false;
    if (pathLine) { map.removeLayer(pathLine); pathLine = null;}
    selectedMarkers.forEach(m => map.removeLayer(m));
    selectedMarkers = []; pointContainer = [];
    plotWindow().style.display = "none";
    setState({isClickedInsideLayer: false});
}

function activePathQuery(){
    if (!getState().isMultiLayer && getState().mapLayer) {
        setState({isPathQuery: true});
        deactivePointQuery();
        mapContainer().style.cursor = "crosshair";
        map.on("click", mapPath);
        map.on("contextmenu", mapPath);
    } else {
        alert("This function is not supported. Please check:\n" + 
            "      1. One map layer must be loaded.\n" +
            "      2. Only static and dynamic (with single layer) maps are supported.");
        deactivePathQuery();
    }
}

export function mapPath(e) {
    if (!getState().isPathQuery) return;
    // Right-click
    if (e.type === "contextmenu") {
        e.originalEvent.preventDefault(); // Suppress context menu
        if (pointContainer.length < 2) {
            alert("Not enough points selected. Please select at least two points.");
            return;
        }
        const title = colorbar_title().textContent;
        plotProfile(pointContainer, getState().polygonCentroids, title, undefined, n_decimals);
    }
    // Left-click
    if (e.type === "click" && e.originalEvent.button === 0) {
        // Check which layer selected
        if (getState().isClickedInsideLayer) {
            // Add marker
            marker = L.circleMarker(e.latlng, {
                radius: 5, color: 'blue', fillColor: 'cyan', fillOpacity: 0.9
            }).addTo(map);
            selectedMarkers.push(marker);
            // Get selected value
            const value = e.layerProps?.[getState().storedLayer?.getColumnName()] ?? null;
            // Add point
            pointContainer.push({
                lat: e.latlng.lat, lng: e.latlng.lng, value: value
            });
            // Plot line
            const latlngs = pointContainer.map(p => [p.lat, p.lng]);
            if (pathLine) {
                pathLine.setLatLngs(latlngs);
            } else {
                pathLine = L.polyline(latlngs, {
                    color: 'orange', weight: 2, dashArray: '5,5'
                }).addTo(map);
            }
        }
        setState({isClickedInsideLayer: false}); // Reset clicked inside layer
    }
}
