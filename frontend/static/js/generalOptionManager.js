import { loadData } from './utils.js';
import { plotChart } from "./chartManager.js";
import { getState, setState } from "./constants.js";
import { startLoading, showLeafletMap, map, L, ZOOM } from "./mapManager.js";

const summaryWindow = () => document.getElementById("summaryWindow");
const summaryHeader = () => document.getElementById("summaryHeader");
const summaryContent = () => document.getElementById("summaryContent");
const projectSummaryOption = () => document.getElementById('projectSummaryOption');
const closeSummaryOption = () => document.getElementById('closeSummaryOption');
const hydStation = () => document.getElementById("hyd-obs-checkbox");
const sourceStation = () => document.getElementById("source-checkbox");
const crossSection = () => document.getElementById("cross-section-checkbox");
const waqObsStation = () => document.getElementById("waq-obs-checkbox");




let Dragging = false;

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
    updateHYDManager(); updateWAQManager();
    
    
    
    
    // updatePointManager(); updatePathManager();
    // queryUpdate();

    
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

// ============================ Observation Points ============================

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




// ============================ Thermocline Plot ============================
function thermoclinePlot(){
    // Set function for plot using Plotly
    document.querySelectorAll('.thermocline').forEach(plot => {
        plot.addEventListener('click', () => {
            const [titleY, chartTitle] = plot.dataset.info.split('|');
            plotChart('', 'thermocline', chartTitle, 'Temperature (°C)', titleY);
        });
    });
}
