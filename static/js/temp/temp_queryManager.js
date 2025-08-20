import { startLoading, showLeafletMap, map, L, ZOOM } from "./temp_mapManager.js";
import { setStationLayer, getStationLayer, degree_decimals } from "./temp_constants.js";
import { setIsPointQuery, getIsMultiLayer } from "./temp_constants.js";
import { getPolygonCentroids, getStoredLayer, getIsPointQuery } from "./temp_constants.js";
import { setIsClickedInsideLayer, getIsClickedInsideLayer } from "./temp_constants.js";
import { getMapLayer, setIsPathQuery, getIsPathQuery, n_decimals } from "./temp_constants.js";
import { loadData, colorbar_title } from "./utils.js";
import { plotChart, plotWindow, plotProfile} from "./temp_chartManager.js";

let stationLayer = null, currentMarker = null, selectedMarkers = [];
let pathLine = null, marker = null, pointContainer = [];

const mapContainer = () => map.getContainer();
const stationOption = () => document.getElementById("stationCheckbox");
const pointQueryCheckbox = () => document.getElementById("pointQuery");
const pathQueryCheckbox = () => document.getElementById("pathQuery");
const infoDetail = () => document.getElementById("infoDetails");
const infoContent = () => document.getElementById("infoDetailsContent");

// ============================ Station Manager ============================
function deactiveStationCheck() {
    map.removeLayer(stationLayer); stationLayer = null;
    setStationLayer(false);    
}

async function activeStationCheck(filename) {
    startLoading(); // Show spinner
    const data = await loadData(filename, 'stations'); // Load data
    if (getStationLayer()) { map.removeLayer(stationLayer); stationLayer = null; }
    // Add station layer to the map
    stationLayer = L.geoJSON(data.content, {
        // Custom marker icon
        pointToLayer: function (feature, latlng) {
            const customIcon = L.icon({
                iconUrl: 'images/station.png?v=${Date.now()}',
                iconSize: [30, 30], popupAnchor: [1, -34],
            });
            const marker = L.marker(latlng, {icon: customIcon});
            const stationId = feature.properties.name || 'Unknown';
            // Add tooltip
            const value = `<div style="text-align: center;">
                    <b>${stationId}</b><br>Select object to see more parameters
                </div>`;
            marker.bindTooltip(value, {
                permanent: false, direction: 'top', offset: [0, 0]
            });
            // Add popup
            const popupContent = `
                <div style="font-family: Arial;">
                    <h3 style="text-align: center;">${stationId}</h3>
                    <hr style="margin: 5px 0 5px 0;">
                    <ul style="left: 0; cursor: pointer; padding-left: 0; list-style: none;">
                        <li><a class="in-situ" data-info="temp_in-situ*${stationId}|Temperature (°C)">• Temperature</a></li>
                        <li><a class="in-situ" data-info="sal_in-situ*${stationId}|Salinity (PSU)">• Salinity</a></li>
                        <li><a class="in-situ" data-info="cont_in-situ*${stationId}|Contaminant (g/L)">• Contaminant</a></li>
                    </ul>
                </div>
            `;
            marker.bindPopup(popupContent, {offset: [0, 40]});
            return marker;
        }
    });
    map.addLayer(stationLayer);
    // Zoom to the extent of the station layer
    if (stationLayer && stationLayer.getBounds().isValid()) {
        const center = stationLayer.getBounds().getCenter();
        map.setView(center, ZOOM);
    }
    setStationLayer(true);
    showLeafletMap(); // Hide the spinner and show the map
}

export function updateStationManager(filename) {
    // Check status of the station checkbox
    if (getStationLayer()) { stationOption().checked = true; 
    } else { stationOption().checked = false; }
    // Add event listener to the station checkbox
    stationOption().addEventListener('change', () => {
        if (stationOption().checked) { activeStationCheck(filename);
        } else deactiveStationCheck();
    });
}
// ============================ Point Manager ============================
function checkPoint(){
    if (getIsPointQuery()) { pointQueryCheckbox().checked = true; 
    } else { pointQueryCheckbox().checked = false; deactivePointQuery(); }
}
export function deactivePointQuery() {
    setIsPointQuery(false);
    if (pointQueryCheckbox()) pointQueryCheckbox().checked = false;
    mapContainer().style.cursor = "grab";
    infoDetail().style.display = "none";
    infoContent().innerHTML = '';
    plotWindow().style.display = "none";
    if (currentMarker) { map.removeLayer(currentMarker); }
}

export function updatePointManager() {
    checkPoint();
    // Add event listener to the point query checkbox
    pointQueryCheckbox().addEventListener('change', () => {
        if (pointQueryCheckbox().checked) { activePointQuery();
        } else deactivePointQuery();
    });
    // Add event listener for point query
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('in-situ')) {
            e.preventDefault();
            const [filename, colorbarTitle] = e.target.dataset.info.split('|');
            const chartTitle = colorbarTitle.split('(')[0].trim();
            plotChart(filename, '_in-situ', chartTitle, 'Time', colorbarTitle, false);
        }
    });
}

function activePointQuery(){
    setIsPointQuery(true);
    if (!getIsMultiLayer() && getMapLayer()) { 
        infoDetail().style.display = "block";
        deactivePathQuery();
        mapContainer().style.cursor = "help";
    } else {
        alert("This function is not supported. Please check:\n" + 
            "      1. One map layer must be loaded.\n" +
            "      2. Only static and dynamic (with single layer) maps are supported.");
        deactivePointQuery(); return;
    }
}

export function mapPoint(e) {
    if (!getIsPointQuery()) return;
    if (currentMarker) { map.removeLayer(currentMarker); }
    if (e.layerProps) {
        const lat = e.latlng.lat.toFixed(degree_decimals);
        const lng = e.latlng.lng.toFixed(degree_decimals);
        currentMarker = L.marker(e.latlng).addTo(map);
        const fieldName = getStoredLayer().getColumnName();
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
        setIsClickedInsideLayer(false);
    }
}

// ============================ Path Manager ============================
function checkPath(){
    if (getIsPathQuery()) { pathQueryCheckbox().checked = true; 
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
    setIsPathQuery(false);
    if (pathQueryCheckbox()) pathQueryCheckbox().checked = false;
    if (pathLine) { map.removeLayer(pathLine); pathLine = null;}
    selectedMarkers.forEach(m => map.removeLayer(m));
    selectedMarkers = []; pointContainer = [];
    plotWindow().style.display = "none";
    setIsClickedInsideLayer(false);
}

function activePathQuery(){
    if (!getIsMultiLayer() && getMapLayer()) {
        setIsPathQuery(true);
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
    if (!getIsPathQuery()) return;
    // Right-click
    if (e.type === "contextmenu") {
        e.originalEvent.preventDefault(); // Suppress context menu
        if (pointContainer.length < 2) {
            alert("Not enough points selected. Please select at least two points.");
            return;
        }
        // TODO:
        const title = colorbar_title().textContent;
        plotProfile(pointContainer, getPolygonCentroids(), title, undefined, n_decimals);
    }
    // Left-click
    if (e.type === "click" && e.originalEvent.button === 0) {
        // Check which layer selected
        if (getIsClickedInsideLayer()) {
            // Add marker
            marker = L.circleMarker(e.latlng, {
                radius: 5, color: 'blue', fillColor: 'cyan', fillOpacity: 0.9
            }).addTo(map);
            selectedMarkers.push(marker);
            // Get selected value
            const value = e.layerProps?.[getStoredLayer()?.getColumnName()] ?? null;
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
        setIsClickedInsideLayer(false); // Reset clicked inside layer
    }
}
