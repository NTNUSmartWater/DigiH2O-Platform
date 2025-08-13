import { n_decimals, degree_decimals } from "./temp_constants.js";
import { getStationLayer, setStationLayer, getPointContainer, setPointContainer } from "./temp_constants.js";
import { getIsPathQuery, setIsPathQuery, getIsClickedInsideLayer, setIsClickedInsideLayer } from "./temp_constants.js";
import { getPolygonCentroids, getIsPath, setIsPointQuery, getIsPointQuery, getStoredLayer } from "./temp_constants.js";
import { startLoading, showLeafletMap, map, L, ZOOM} from "./temp_mapManager.js";
import { loadData, colorbar_title, interpolateValue } from "./utils.js";
import { closeMenu } from "./temp_uiManager.js";
import { plotChart, drawChart, plotWindow } from './temp_chartManager.js';

let stationLayer = null, mapContainer = null, marker = null, selectedMarkers = [], pathLine = null, currentMarker = null;

const stationOption = () => document.getElementById("stationCheckbox");
const pointQueryCheckbox = () => document.getElementById("pointQuery");
const pathQueryCheckbox = () => document.getElementById("pathQuery");
const infoDetail = () => document.getElementById("infoDetails");
const infoContent = () => document.getElementById("infoDetailsContent");


export function initiateQueryManager() {
    pointQuery(); pathQuery();
    map.on("click", mapPath);
    map.on("contextmenu", mapPath);
    map.on("click", mapPoint);
}

// ================== STATION CHECK ==================
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
                    <hr style="margin: 0;">
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
    setStationLayer(true); // Set the station layer is loaded
    showLeafletMap(); // Hide the spinner and show the map
}

export function stationCheck(filename){
    stationOption().addEventListener('change', () => {
        if (stationOption().checked) { activeStationCheck(filename);
        } else deactiveStationCheck(); closeMenu();
    })
}

// =================== POINT QUERY ===================
export function deactivePointQuery() {
    pointQueryCheckbox().checked = false; // Deselect checkbox
    mapContainer.style.cursor = "grab";
    infoDetail().style.display = "none";
    infoContent().innerHTML = '';
    setIsPointQuery(false); // Set point query is deactivated
    if (currentMarker) { map.removeLayer(currentMarker); }
}

function activePointQuery(){
    infoDetail().style.display = "block"; // Show the info detail
    setIsPointQuery(true); // Set point query is activated

    mapContainer.style.cursor = "help";
}

function pointQuery(){
    mapContainer = map.getContainer();
    pointQueryCheckbox().addEventListener('change', () => {
        if (pointQueryCheckbox().checked) { activePointQuery();
        } else deactivePointQuery(); closeMenu();
    })
    // Add event listener for point query
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('in-situ')) {
            e.preventDefault();
            const [filename, colorbarTitle] = e.target.dataset.info.split('|');
            const chartTitle = colorbarTitle.split('(')[0].trim();
            plotChart(filename, 'in-situ', chartTitle, 'Time', colorbarTitle, 'All', false);
        }
    });
}

// =================== PATH QUERY ===================
export function deactivePathQuery() {
    pathQueryCheckbox().checked = false; // Deselect checkbox
    setIsPathQuery(false); // Set path query is deactivated
    if (pathLine) { map.removeLayer(pathLine); pathLine = null;}
    selectedMarkers.forEach(m => map.removeLayer(m));
    selectedMarkers = []; setPointContainer([]);
    plotWindow().style.display = "none"; // Close the chart if it is open
    setIsClickedInsideLayer(false); // Reset clicked inside layer
    mapContainer.style.cursor = "grab";
}

function activePathQuery(){
    if (!getIsPath()) {
        alert("This type of map does not support path queries.\nOnly static and dynamic (with single layer) maps are supported.");
        // Deselect checkbox
        deactivePathQuery(); return;
    }
    setIsPathQuery(true); // Set path query is activated
    mapContainer.style.cursor = "crosshair";
    closeMenu(); // Close the menu
}

function pathQuery(){
    pathQueryCheckbox().addEventListener('change', () => {
        if (pathQueryCheckbox().checked) { activePathQuery();
        } else deactivePathQuery(); closeMenu();
    })
}

export function mapPath(e) {
    if (!getIsPathQuery()) return;
    // Right-click
    if (e.type === "contextmenu") {
        e.originalEvent.preventDefault(); // Suppress context menu
        if (getPointContainer().length < 2) {
            alert("Not enough points selected. Please select at least two points.");
            return;
        }
        // TODO:
        const title = colorbar_title().textContent;
        plotProfile(getPointContainer(), getPolygonCentroids(), title);
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
            getPointContainer().push({
                lat: e.latlng.lat, lng: e.latlng.lng, value: value
            });
            // Plot line
            const latlngs = getPointContainer().map(p => [p.lat, p.lng]);
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

function plotProfile(pointContainer, polygonCentroids, titleY, titleX='Distance (m)') {
    const subset_dis = 100, interpolatedPoints = [];
    // Convert Lat, Long to x, y
    for (let i = 0; i < pointContainer.length - 1; i++) {
        const p1 = pointContainer[i], p2 = pointContainer[i + 1];
        const pt1 = L.Projection.SphericalMercator.project(L.latLng(p1.lat, p1.lng));
        const pt2 = L.Projection.SphericalMercator.project(L.latLng(p2.lat, p2.lng));
        const dx = pt2.x - pt1.x, dy = pt2.y - pt1.y;
        const segmentDist = Math.sqrt(dx * dx + dy * dy);
        const segments = Math.floor(segmentDist / subset_dis);
        // Add the first point
        const originDist = Number(L.latLng(p1.lat, p1.lng).distanceTo(pointContainer[0]).toFixed(n_decimals));
        interpolatedPoints.push([originDist, p1.value]);
        // Add the intermediate points        
        for (let j = 1; j < segments; j++) {
            const ratio = j / segments;
            const interpX = pt1.x + ratio * dx, interpY = pt1.y + ratio * dy;
            const latlngInterp = L.Projection.SphericalMercator.unproject(L.point(interpX, interpY));
            // Interpolate
            const location = L.latLng(latlngInterp.lat, latlngInterp.lng);
            const interpValue = interpolateValue(location, polygonCentroids);
            // Compute distance            
            const distInterp = Number(L.latLng(latlngInterp.lat, latlngInterp.lng).distanceTo(pointContainer[0])).toFixed(n_decimals);
            if (interpValue !== null) {
                interpolatedPoints.push([distInterp, interpValue]);
            }
        }
        // Add the last point
        const lastPt = pointContainer[pointContainer.length - 1];
        const lastDist = Number(L.latLng(lastPt.lat, lastPt.lng).distanceTo(pointContainer[0])).toFixed(n_decimals);
        interpolatedPoints.push([lastDist, lastPt.value]);
    }
    // Sort by distance
    interpolatedPoints.sort((a, b) => a[0] - b[0]);
    const input = {
        columns: [titleX, titleY], data: interpolatedPoints
    };
    drawChart(input, 'Profile', titleX, titleY, 'All', false);
}

function mapPoint(e) {
    if (!getIsPointQuery()) return;
    const lat = e.latlng.lat.toFixed(degree_decimals), lng = e.latlng.lng.toFixed(degree_decimals);
    if (currentMarker) { map.removeLayer(currentMarker); }
    currentMarker = L.marker(e.latlng).addTo(map);
    let html = `
        <div style="display: flex; justify-content: space-between;">
            <div style="padding-left: 10px;">Location:</div>
            <div style="padding-right: 10px;">${lng}, ${lat}</div>
        </div>`;
    if (getStoredLayer()) {
        const fieldName = getStoredLayer().getColumnName();
        const getValue = new Promise(resolve => {
            getStoredLayer().once('click', function(e) {
                resolve(e.layer.properties[fieldName] || 'N/A');
            });
        });
        getValue.then(value => {
            html += `
            <div style="display: flex; justify-content: space-between;">
                <div style="padding-left: 10px;">${colorbar_title().textContent}:</div>
                <div style="padding-right: 10px;">${value}</div>
            </div>`;
            infoContent().innerHTML = html;
        });
    }
    infoContent().innerHTML = html;
    // Update the height of the info window
    infoDetail().style.height = 'auto';
}






// // Menu panel on bottom-right corner
// export function closeinfoMenu() {
//     infoMenu().style.height = "35px"; arrow().textContent = "▲";
//     setIsInfoOpen(!getIsInfoOpen()); 
// }

// export function openinfoMenu() {
//     // Open the info menu with measured height
//     infoMenu().style.height = infoMenu().scrollHeight + "px";
//     // Asign auto scroll
//     const removeFixedHeight = () => {
//         infoMenu().style.height = "auto";
//         infoMenu().removeEventListener("transitionend", removeFixedHeight);
//     };
//     infoMenu().addEventListener("transitionend", removeFixedHeight);
//     arrow().textContent = "▼";
//     setIsInfoOpen(!getIsInfoOpen()); 
// }