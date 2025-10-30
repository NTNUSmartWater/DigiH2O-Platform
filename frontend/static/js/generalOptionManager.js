import { loadData } from './utils.js';
import { colorbar_title } from './map2DManager.js';
import { plotChart, plotProfileSingleLayer, plotProfileMultiLayer } from "./chartManager.js";
import { n_decimals, getState, setState } from "./constants.js";
import { startLoading, showLeafletMap, map, L, ZOOM } from "./mapManager.js";

export const summaryWindow = () => document.getElementById("summaryWindow");
const summaryHeader = () => document.getElementById("summaryHeader");
const summaryContent = () => document.getElementById("summaryContent");
const projectSummaryOption = () => document.getElementById('projectSummaryOption');
const closeSummaryOption = () => document.getElementById('closeSummaryOption');
const hydStation = () => document.getElementById("hyd-obs-checkbox");
const sourceStation = () => document.getElementById("source-checkbox");
const crossSection = () => document.getElementById("cross-section-checkbox");
const waqObsStation = () => document.getElementById("waq-obs-checkbox");
const waqLoadsStation = () => document.getElementById("waq-loads-checkbox");
const pathQuery = () => document.getElementById("path-query-checkbox");
const mapContainer = () => map.getContainer();
const profileWindow = () => document.getElementById('profileWindow');
const profileWindowHeader = () => document.getElementById('profileWindowHeader');
const profileCloseBtn = () => document.getElementById('closeProfileWindow');

let Dragging = false, pathLine = null, selectedMarkers = [], pointContainer = [], marker = null;

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

export function generalOptionsManager(){
    projectSummaryEvents(); thermoclinePlot();
    updateHYDManager(); updateWAQManager(); updatePathManager();
}

// ============================ Project Summary ============================
function projectSummaryEvents(){
    projectSummaryOption().addEventListener('click', () => { openProjectSummary(); });
    closeSummaryOption().addEventListener('click', () => { summaryWindow().style.display = "none"; });
    // Move summary window
    let offsetX = 0, offsetY = 0;
    summaryHeader().addEventListener("mousedown", function(e) {
        Dragging = true;
        offsetX = e.clientX - summaryWindow().offsetLeft;
        offsetY = e.clientY - summaryWindow().offsetTop;
    });
    summaryHeader().addEventListener("mouseup", function() { Dragging = false; });
    document.addEventListener("mousemove", function(e) {
        if (Dragging) {
            summaryWindow().style.left = (e.clientX - offsetX) + "px";
            summaryWindow().style.top = (e.clientY - offsetY) + "px";
        }
    });
}

async function openProjectSummary() {
    const data = await loadData('', 'summary');
    if (data.status === 'error') { alert(data.message); return; }
    const currentDisplay = window.getComputedStyle(summaryWindow()).display;
    if (currentDisplay === "none") {
        // Create a table to display the summary
        let html = `<table><thead>
            <tr>
            <th style="text-align: center;">Parameter</th>
            <th style="text-align: center;">Value</th>
            </tr>
        </thead><tbody>`;
        data.content.forEach(item => {
            html += `
                <tr>
                    <td>${item.parameter}</td>
                    <td>${item.value}</td>
                </tr>
            `;
        });
        html += `</tbody></table>`;
        summaryContent().innerHTML = html;
        // Open the summary window
        summaryWindow().style.display = "flex";
    } else { summaryWindow().style.display = "none";}
}

// ============================ Points Manager ============================
function updateHYDManager(){
    // 1. Hydrodynamic Observations
    checkUpdater("hydLayer", hydStation(), loadHYDStations);
    // 2. Sources/Sinks Observations
    checkUpdater("sourceLayer", sourceStation(), loadSourceStations);
    // 3. Cross-Section Observations
    checkUpdater("crosssectionLayer", crossSection(), loadCrossSection);
    // Add event when user clicks on the popup
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('in-situ')) {
            e.preventDefault();
            const [query, colorbarTitle] = e.target.dataset.info.split('|');
            const chartTitle = query.split('*')[1] + ' (' + colorbarTitle.split('(')[0].trim() + ')';
            plotChart(query, '_in-situ', chartTitle, 'Time', colorbarTitle);
        }
        if (e.target && e.target.classList.contains('function')) {
            e.preventDefault();
            const [key, colorbarTitle] = e.target.dataset.info.split('|');
            const chartTitle = colorbarTitle.split('(')[0].trim();
            plotChart('', key, chartTitle, 'Time', colorbarTitle);
        }
    })
}
// Load hydrodynamic observation points
async function loadHYDStations() {
    startLoading('Reading Hydrodynamic Observation Points from Database. Please wait...'); // Show spinner
    const data = await loadData('', 'hyd_station'); // Load data
    if (data.status === "error") { alert(data.message); return; }
    if (getState().hydLayer) { map.removeLayer(getState().hydLayer); }
    // Add station layer to the map
    const indx = data.message;
    const layer = L.geoJSON(data.content, {
        // Custom marker icon
        pointToLayer: function (feature, latlng) {
            const customIcon = L.icon({
                iconUrl: `static_backend/images/station.png?v=${Date.now()}`,
                iconSize: [20, 20], popupAnchor: [1, -34],
            });
            const marker = L.marker(latlng, {icon: customIcon});
            const stationId = feature.properties.name || 'Unknown';
            // Add tooltip
            const info = indx.length > 0 ? '<br>Select object to see values at each layer' : '';
            const value = `<div style="text-align: center; weight: bold;"> <b>${stationId}</b>${info}</div>`;
            marker.bindTooltip(value, { permanent: false, direction: 'top', offset: [0, 0] });
            // Get name of the station
            const name = indx.find(item => item[stationId]);
            let popupContent = `<div style="font-family: Arial;max-height: 200px; overflow-y: auto;">
                <h3 style="text-align: center;">${stationId}</h3>
                <hr style="margin: 5px 0 5px 0;"><ul style="left: 0; cursor: pointer; padding-left: 0;">`;
            if (name && Array.isArray(name[stationId])) {
                name[stationId].forEach(item => {
                    const [key, value] = Object.entries(item)[0];
                    popupContent += `<li style="margin-bottom:5px; line-height:1.2;">
                        <a class="in-situ" data-info="${key}*${stationId}*station_name|${value}">• ${value}</a></li>`;
                })
            } else popupContent += `<li><em>No data available</em></li>`;
            popupContent += `</ul></div>`;
            marker.bindPopup(popupContent, {offset: [0, 40]});
            return marker;
        }
    });
    map.addLayer(layer);
    // Zoom to the extent of the station layer
    map.setView(layer.getBounds().getCenter(), ZOOM);
    showLeafletMap(); // Hide the spinner and show the map
    return layer;
}
// Load sources/sinks observation points
async function loadSourceStations() {
    startLoading('Reading Sources/Sinks from Database. Please wait...');
    const data = await loadData('', 'sources');
    if (data.status === "error") { alert(data.message); return; }
    if (getState().sourceLayer) { map.removeLayer(getState().sourceLayer); }
    const layer = L.geoJSON(data.content, {
        pointToLayer: function (feature, latlng) {
            const customIcon = L.icon({
                iconUrl: `static_backend/images/source.png?v=${Date.now()}`,
                iconSize: [20, 20], popupAnchor: [1, -34],
            });
            const marker = L.marker(latlng, {icon: customIcon});
            const sourceId = feature.properties.name || 'Unknown';
            const value = `<div style="text-align: center;"><b>${sourceId}</b></div>`;
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
// Load cross-section observation path
async function loadCrossSection() {
    startLoading('Reading Cross-Sections from Database. Please wait...');
    const data = await loadData('', 'crosssections');
    if (data.status === "error") { alert(data.message); showLeafletMap(); return; }
    if (getState().crosssectionLayer) { map.removeLayer(getState().crosssectionLayer); }
    const indx = data.message;
    const layer = L.geoJSON(data.content, { 
        color: 'blue', weight: 3,
        onEachFeature: function (feature, layer) {
            const name = feature.properties.name || 'Unknown';
            // Add tooltip
            const info = indx.length > 0 ? '<br>Select object to see more information.' : '';
            const value = `<div style="text-align: center; weight: bold;"> <b>${name}</b>${info}</div>`;
            layer.bindTooltip(value, { permanent: false, direction: 'top', offset: [0, 0] });
            let popupContent = `<div style="font-family: Arial;max-height: 200px; overflow-y: auto;">
                <h3 style="text-align: center;">${name}</h3>
                <hr style="margin: 5px 0 5px 0;"><ul style="left: 0; cursor: pointer; padding-left: 0;">`;
            if (Array.isArray(indx) && indx.length > 0) {
                indx.forEach(item => {
                    const [key, value] = Object.entries(item)[0];
                    popupContent += `<li style="margin-bottom:5px; line-height:1.2;">
                        <a class="function" data-info="${key}_crs|${value}">• ${value}</a></li>`;
                })
            } else popupContent += `<li><em>No data available</em></li>`;
            popupContent += `</ul></div>`;
            layer.bindPopup(popupContent, {offset: [0, 40]});      
        }
    });
    map.addLayer(layer);
    map.setView(layer.getBounds().getCenter(), ZOOM);
    showLeafletMap();
    return layer;
}

function updateWAQManager() {
    // 1. Update Water Quality Observation Points
    checkUpdater("wqObsLayer", waqObsStation(), loadWAQStations);
    // 2. Update water quality observation points
    checkUpdater("wqLoadsLayer", waqLoadsStation(), loadWAQLoads);
}

async function loadWAQStations() {
    startLoading('Loading Water Quality Observation Points from Database. Please wait...');
    const data = await loadData('', 'wq_obs');
    if (data.status === "error") { alert(data.message); return; }
    if (getState().wqObsLayer) { map.removeLayer(getState().wqObsLayer); }
    const layer = L.geoJSON(data.content, {
        // Custom marker icon
        pointToLayer: function (feature, latlng) {
            const customIcon = L.icon({
                iconUrl: `static_backend/images/waq_obs.png?v=${Date.now()}`,
                iconSize: [27, 27], popupAnchor: [1, -34],
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
async function loadWAQLoads() {
    startLoading('Loading Loads of Water Quality Observation Points from Database. Please wait...');
    const data = await loadData('', 'wq_loads');
    if (data.status === "error") { alert(data.message); return; }
    if (getState().wqLoadsLayer) { map.removeLayer(getState().wqLoadsLayer); }
    const layer = L.geoJSON(data.content, {
        // Custom marker icon
        pointToLayer: function (feature, latlng) {
            const customIcon = L.icon({
                iconUrl: `static_backend/images/waq_loads.png?v=${Date.now()}`,
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

// ============================ Path Manager ============================
function moveWindow(window, header){
    let dragging = false, offsetX = 0, offsetY = 0;
    header().addEventListener("mousedown", function(e) {
        dragging = true;
        offsetX = e.clientX - window().offsetLeft;
        offsetY = e.clientY - window().offsetTop;
        e.preventDefault();
    });
    header().addEventListener("mouseup", function() { dragging = false; });
    document.addEventListener("mousemove", function(e) {
        if (dragging) {
            window().style.left = (e.clientX - offsetX) + "px";
            window().style.top = (e.clientY - offsetY) + "px";
        }
    });
}

export function updatePathManager() {
    pathQuery().checked = getState().isPathQuery;
    if (getState().isPathQuery === false) deActivePathQuery();
    pathQuery().addEventListener('change', () => { 
        if (pathQuery().checked) { 
            if (getState().mapLayer === null){
                alert("No map layer available"); deActivePathQuery();
            } else {
                mapContainer().style.cursor = "crosshair";
                map.on("click", mapPath); map.on("contextmenu", mapPath);
            }
        } else deActivePathQuery();
        setState({isPathQuery: pathQuery().checked});
    });
    profileCloseBtn().addEventListener('click', () => { profileWindow().style.display = 'none'; });
    moveWindow(profileWindow, profileWindowHeader); 
}

function deActivePathQuery() {
    pathQuery().checked = false; setState({isPathQuery: false});
    if (pathLine) { map.removeLayer(pathLine); pathLine = null;}
    selectedMarkers.forEach(m => map.removeLayer(m));
    selectedMarkers = []; pointContainer = [];
    mapContainer().style.cursor = "default";
}

async function mapPath(e) {
    if (!getState().isPathQuery) return;
    // Right-click
    if (e.type === "contextmenu") {
        e.originalEvent.preventDefault(); // Suppress context menu
        if (pointContainer.length < 2) { alert("Please select at least two points"); return; }
        if (!getState().isMultiLayer){
            const titleY = colorbar_title().textContent;
            const title = 'Profile - Single Layer';
            plotProfileSingleLayer(pointContainer, getState().polygonCentroids, title, titleY, undefined, n_decimals);
        } else {
            const coords = pathLine.toGeoJSON().geometry.coordinates;
            const featureMap = getState().featureMap;
            const orderedPolygons = [], ordered = [], seen = new Set();
            for (let i = 0; i < coords.length-1; i++) {
                const start = coords[i], end = coords[i+1];
                const segment = turf.lineString([start, end]);
                const segLength = turf.length(segment, { units: 'meters' });
                const segmentPolys = [];
                Object.values(featureMap).forEach(f => {
                    if (!f || !f.geometry) return;
                    // Check if start point is inside the polygon
                    const startPt = turf.point(start);
                    if (turf.booleanPointInPolygon(startPt, f)) {
                        segmentPolys.push({id: f.properties.index, t: 0});
                        return;
                    }
                    // Check if end point is inside the polygon
                    const endPt = turf.point(end);
                    if (turf.booleanPointInPolygon(endPt, f)) {
                        segmentPolys.push({id: f.properties.index, t: 1});
                        return;
                    }
                    // Check if the segment intersects with the polygon
                    const intersects = turf.lineIntersect(segment, f);
                    if (intersects.features && intersects.features.length > 0) {
                        let minT = Infinity;
                        intersects.features.forEach(ptFeature => {
                            const pt = ptFeature.geometry.coordinates;
                            const distance = turf.distance(turf.point(start), turf.point(pt), {units: 'meters'});
                            const t = segLength > 0 ? distance / segLength : 0;
                            segmentPolys.push({id: f.properties.index, t: t});
                            if (t < minT) minT = t;
                        });
                        // Make sure t is in [0, 1]
                        if (minT === Infinity) minT = 0;
                        minT = Math.max(0, Math.min(1, minT));
                        segmentPolys.push({id: f.properties.index, t: minT});
                    }
                });
                // Sort by distance along the segment 
                segmentPolys.sort((a, b) => a.t - b.t);
                segmentPolys.forEach(p => ordered.push(p.id));
                // Remove duplicates while preserving order
                for (const id of ordered) {
                    if (!seen.has(id)) {
                        orderedPolygons.push(id); seen.add(id);
                    }
                }
            }
            if (orderedPolygons.length === 0) { alert("No intersected mesh found"); return; }
            startLoading('Acquiring selected meshes from Database. Please wait...');
            const key = !getState().isHYD ? 'hyd' : 'waq';
            const unit = colorbar_title().textContent.split('(')[1].trim().replace(')', '');
            const title = `Profile - ${colorbar_title().textContent.split('(')[0].trim()}`;
            const response = await fetch('/select_meshes', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({key: key, query: getState().showedQuery, ids: orderedPolygons})});
            const data = await response.json();
            if (data.status === "error") { alert(data.message); return; }
            plotProfileMultiLayer(profileWindow, data.content, title, unit, 4);
            showLeafletMap();
        }
    }
    // Left-click
    if (e.type === "click" && e.originalEvent.button === 0) {
        // Check if clicked inside layer
        if (getState().isClickedInsideLayer) {
            // Add marker
            marker = L.circleMarker(e.latlng, {
                radius: 5, color: 'blue', fillColor: 'cyan', fillOpacity: 0.9
            }).addTo(map);
            selectedMarkers.push(marker);
            // Add point
            pointContainer.push({
                lat: e.latlng.lat, lng: e.latlng.lng
            });
            // Plot line
            const latlngs = pointContainer.map(p => [p.lat, p.lng]);
            if (pathLine) { pathLine.setLatLngs(latlngs);
            } else {
                pathLine = L.polyline(latlngs, {
                    color: 'orange', weight: 2, dashArray: '5,5'
                }).addTo(map);
            }
        }
        setState({isClickedInsideLayer: false}); // Reset clicked inside layer
    }
}

// ============================ Thermocline Plot ============================
function thermoclinePlot(){
    // Set function for plot using Plotly
    document.querySelectorAll('.thermocline').forEach(plot => {
        plot.addEventListener('click', () => {
            const [titleY, titleX, chartTitle] = plot.dataset.info.split('|');
            console.log(titleX, titleY, chartTitle);
            // plotChart('', 'thermocline', chartTitle, titleX, titleY);
        });
    });
}
