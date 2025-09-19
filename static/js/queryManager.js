import { startLoading, showLeafletMap, map, L, ZOOM } from "./mapManager.js";
import { degree_decimals, n_decimals, getState, setState } from "./constants.js";
import { loadData, colorbar_title } from "./utils.js";
import { plotChart, plotWindow, plotProfile} from "./chartManager.js";

let stationLayer = null, sourceLayer = null, crosssectionLayer = null, currentMarker = null;
let pathLine = null, marker = null, pointContainer = [], selectedMarkers = [];

const mapContainer = () => map.getContainer();
const stationOption = () => document.getElementById("stationCheckbox");
const sourceOption = () => document.getElementById("sourceCheckbox");
const crossSectionOption = () => document.getElementById("crossSectionCheckbox");
const pointQueryCheckbox = () => document.getElementById("pointQuery");
const pathQueryCheckbox = () => document.getElementById("pathQuery");
const infoDetail = () => document.getElementById("infoDetails");
const infoContent = () => document.getElementById("infoDetailsContent");

// ============================ Station Manager ============================
async function activeStationCheck(filename) {
    startLoading('Reading Stations from Database. Please wait...'); // Show spinner
    const data = await loadData(filename, 'stations'); // Load data
    if (data.status === "error") { alert(data.message); return; }
    if (getState().stationLayer && stationLayer) { map.removeLayer(stationLayer); stationLayer = null; }
    // Add station layer to the map
    stationLayer = L.geoJSON(data.content, {
        // Custom marker icon
        pointToLayer: function (feature, latlng) {
            const customIcon = L.icon({
                iconUrl: `static/images/station.png?v=${Date.now()}`,
                iconSize: [20, 20], popupAnchor: [1, -34],
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
            const popupContent = `<div style="font-family: Arial;">
                <h3 style="text-align: center;">${stationId}</h3>
                <hr style="margin: 5px 0 5px 0;">
                <ul style="left: 0; cursor: pointer; padding-left: 0; list-style: none;">
                    <li><a class="in-situ" data-info="temp*${stationId}*station_name|Temperature (°C)">• Temperature</a></li>
                    <li><a class="in-situ" data-info="sal*${stationId}*station_name|Salinity (PSU)">• Salinity</a></li>
                    <li><a class="in-situ" data-info="cont*${stationId}*station_name|Contaminant (g/L)">• Contaminant</a></li>
                </ul>
            </div>`;
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
    setState({stationLayer: true});
    showLeafletMap(); // Hide the spinner and show the map
}

async function activeSourceCheck(filename) {
    startLoading('Reading Sources from Database. Please wait...');
    const data = await loadData(filename, 'sources');
    if (data.status === "error") { alert(data.message); return; }
    if (getState().sourceLayer && sourceLayer) { map.removeLayer(sourceLayer); sourceLayer = null; }
    sourceLayer = L.geoJSON(data.content, {
        pointToLayer: function (feature, latlng) {
            const customIcon = L.icon({
                iconUrl: `static/images/source.png?v=${Date.now()}`,
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
    map.addLayer(sourceLayer);
    if (sourceLayer && sourceLayer.getBounds().isValid()) {
        const center = sourceLayer.getBounds().getCenter();
        map.setView(center, ZOOM);
    }
    setState({sourceLayer: true});
    showLeafletMap();
}

async function activeCrossSectionCheck(filename) {
    startLoading('Reading Cross Sections from Database. Please wait...');
    const data = await loadData(filename, 'crosssections');
    if (data.status === "error") { alert(data.message); showLeafletMap(); return; }
    if (getState().crosssectionLayer && crosssectionLayer) { map.removeLayer(crosssectionLayer); crosssectionLayer = null; }
    crosssectionLayer = L.geoJSON(data.content, { color: 'blue', weight: 3 });
    map.addLayer(crosssectionLayer);
    if (crosssectionLayer && crosssectionLayer.getBounds().isValid()) {
        const center = crosssectionLayer.getBounds().getCenter();
        map.setView(center, ZOOM);
    }
    setState({crosssectionLayer: true});
    showLeafletMap();
}

export function updateStationManager(filename) {
    // Check status of the station checkbox
    if (getState().stationLayer) { stationOption().checked = true; 
    } else { stationOption().checked = false; }
    // Add event listener to the station checkbox
    stationOption().addEventListener('change', () => {
        if (stationOption().checked) { activeStationCheck(filename); setState({stationLayer: true});
        } else {
            map.removeLayer(stationLayer); stationLayer = null; setState({stationLayer: false});  
        }
    });
}

export function updateSourceManager(filename) {
    if (getState().sourceLayer) { sourceOption().checked = true; 
    } else { sourceOption().checked = false; }
    sourceOption().addEventListener('change', () => {
        if (sourceOption().checked) { activeSourceCheck(filename); setState({sourceLayer: true});
        } else {
            map.removeLayer(sourceLayer); sourceLayer = null; setState({sourceLayer: false});  
        }
    })
}

export function updateCrossSectionManager(filename) {
    if (getState().crosssectionLayer) { crossSectionOption().checked = true; 
    } else { crossSectionOption().checked = false; }
    crossSectionOption().addEventListener('change', () => {
        if (crossSectionOption().checked) { activeCrossSectionCheck(filename); setState({crosssectionLayer: true});
        } else {
            map.removeLayer(crosssectionLayer); crosssectionLayer = null; setState({crosssectionLayer: false});  
        }
    })
}

// ============================ Point Manager ============================
function checkPoint(){
    if (getState().isPointQuery) { pointQueryCheckbox().checked = true; 
    } else { pointQueryCheckbox().checked = false; deactivePointQuery(); }
}
export function deactivePointQuery() {
    setState({isPointQuery: false});
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
    setState({isPointQuery: true});
    if (!getState().isMultiLayer && getState().mapLayer) { 
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
