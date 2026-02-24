import { getState } from "./constants.js";
import { L, CENTER, ZOOM } from "./mapManager.js";
import { sendQuery, fillTable, getDataFromTable, deleteTable } from "./tableManager.js";
import { plotTimeSeries, viewDatafromPlot, saveToExcelFromPlot, moveWindow } from "./utils.js";


const compass = () => document.getElementById('custom_compass_btn');
const loading = () => document.getElementById('loadingOverlay');
const waterFlowCheckbox = () => document.getElementById('water-flow-checkbox');
const waterLevelCheckbox = () => document.getElementById('water-level-checkbox');
const overFlowCheckbox = () => document.getElementById('overflow-checkbox');
const temperatureCheckbox = () => document.getElementById('temperature-checkbox');
const rainfallCheckbox = () => document.getElementById('rainfall-checkbox');
const evaporationCheckbox = () => document.getElementById('evaporation-checkbox');
const weirCheckbox = () => document.getElementById('weir-checkbox');
const stationTable = () => document.getElementById('station-table');
const plotContainer = () => document.getElementById('plot-container');
const plotStart = () => document.getElementById('start-plot');
const plotEnd = () => document.getElementById('end-plot');
const plotInterval = () => document.getElementById('interval-plot');
const plotStationWindow = () => document.getElementById('plot-station-window');
const plotStationWindowHeader = () => document.getElementById('plot-station-header');
const plotClose = () => document.getElementById('close-station-plot');
const plotDiv = () => document.getElementById('station-chart');
const dropdown = () => document.getElementById("select-object");
const selectBox = () => dropdown().querySelector('.select-box');
const checkboxList = () => dropdown().querySelector('.checkbox-list');
const plotTitle = () => document.getElementById('plot-title');
const viewDataBtn = () => document.getElementById('view-station-btn');
const downloadExcel = () => document.getElementById('download-station-excel');
const downloadStart = () => document.getElementById('start-download');
const downloadEnd = () => document.getElementById('end-download');
const downloadInterval = () => document.getElementById('interval-download');
const stationSelectedTable = () => document.getElementById('station-selected-table');
const typeDownload = () => document.getElementById('type-download');
const typeSelector = () => document.getElementById('type-download');
const intervalSelector = () => document.getElementById('interval-download');
const stationSelectedLabel = () => document.getElementById('station-selected-label');


const downloadBtn = () => document.getElementById('download-btn');



const hoverTooltip = L.tooltip({
    permanent: false, direction: 'top', sticky: true, offset: [0, -15], className: 'custom-tooltip'
});

let map = null, waterFlowLayer = null, waterLevelLayer = null,
    overFlowLayer = null, tempLayer = null, preLayer = null,
    weirLayer = null, evaLayer = null, plotChecked = true;

function setupTabs(root) {
    const buttonPanels = root.querySelectorAll('#main-tabs button');
    const panels = root.querySelectorAll('.main-panel');
    const radioBtns = root.querySelectorAll('.row-radio');
    const radioPanels = root.querySelectorAll('.radio-panel');
    const checkboxBtns = root.querySelectorAll('.row-checkbox');    
    function activateSubButton(target, selectedPanel){
        const name = target.getAttribute('data-tab');
        const contents = selectedPanel.querySelectorAll('.tabpanel');
        const subButtons = selectedPanel.querySelectorAll('.tab-btn');
        // Show corresponding panel and hide others
        contents.forEach(p => {
            const panelNameActive = p.getAttribute('data-panel') === name;
            p.setAttribute('aria-hidden', String(!panelNameActive));
        })
        subButtons.forEach(btn => {
            btn.setAttribute('aria-selected', String(btn === target));
        });
    }
    function activate(target){
        const name = target.getAttribute('data-tab');
        // Set button aria-selected (highlighted)
        buttonPanels.forEach(btn => btn.setAttribute('aria-selected', String(btn === target)));
        // Show corresponding panel and hide others
        panels.forEach(p => {
            const panelNameActive = p.getAttribute('data-panel') === name;
            p.setAttribute('aria-hidden', String(!panelNameActive));
        })
        // Get sub-buttons in the selected panel
        const selectedPanel = root.querySelector(`[data-panel="${name}"]`);
        if(!selectedPanel) return;
        // Process radio
        const radios = selectedPanel.querySelectorAll('input[type="radio"]');
        if (radios.length > 0) {
            const checkedRadio = Array.from(radios).find(r => r.checked);
            if (checkedRadio) {
                // Select the checked radio
                radioSelector(checkedRadio.closest('.row-radio'));
            } else {
                // fallback: Select the first radio
                radios[0].checked = true;
                radioSelector(radios[0].closest('.row-radio'));
            }
        }
        const subButtonPanels = selectedPanel.querySelectorAll('.tab-btn');
        if(subButtonPanels.length === 0) return;
        const selectedSubBtn = Array.from(subButtonPanels).find(btn => btn.getAttribute('aria-selected') === "true");
        const firstSubBtn = selectedSubBtn || subButtonPanels[0];
        // Highlight first sub-button
        subButtonPanels.forEach(btn => btn.setAttribute('aria-selected', String(btn === firstSubBtn)));
        // Show corresponding sub-panel
        activateSubButton(firstSubBtn, selectedPanel);
        // Click to change sub-tab
        subButtonPanels.forEach(btn => {
            btn.addEventListener('click', () => { activateSubButton(btn, selectedPanel); });
        });
    }
    function radioSelector(target){
      const name = target.getAttribute('data-tab');
      // Show corresponding panel and hide others
      radioPanels.forEach(p => {
        p.style.display = (p.getAttribute('data-panel')!==name)?'none':'block';
      })
    }
    function checkboxSelector(target){
        const name = target.getAttribute('data-tab');
        const checkObj = target.querySelector('input');
        const panel = root.querySelectorAll(`[data-panel="${name}"]`);
        if(panel.length === 0) return;
        panel.forEach(p => {
            p.style.display = checkObj.checked ? 'flex' : 'none';
        })
    }
    // Show Simulator panel
    if(buttonPanels.length > 0) activate(buttonPanels[0]);
    // Click to change tab
    buttonPanels.forEach(btn => {
        btn.addEventListener('click', () => { activate(btn); });
    });
    // Change Radio button
    radioBtns.forEach(btn => {
        btn.addEventListener('click', () => { radioSelector(btn); });
    });
    // Change checkbox button
    checkboxBtns.forEach(box => {
        box.addEventListener('change', () => { checkboxSelector(box); });
    });
}

function startLoading(str = '') {
    loading().querySelector('.loading-text').textContent = str;
    loading().style.display = 'flex'; loading().style.pointerEvents = 'auto';
}
function stopLoading() { 
    loading().style.display = "none"; loading().style.pointerEvents = "none";
}
function formatDate(date) {
    const pad = (n) => String(n).padStart(2, '0');
    const Y = date.getFullYear();
    const M = pad(date.getMonth() + 1);
    const D = pad(date.getDate());
    const h = pad(date.getHours());
    const m = pad(date.getMinutes());
    const s = pad(date.getSeconds());
    return `${Y}-${M}-${D} ${h}:${m}:${s}`;
}

function updateLayerTooltips(layerGroup) {
    if (!layerGroup) return;
    layerGroup.eachLayer(layer => {
        if (!layer.feature) return;
        const feature = layer.feature;
        let note = '';
        if (plotChecked) {
            note = `<hr style="border-top: 1px solid #0414f5; margin: 5px 0;">
                <span style="display:block;font-weight:bold;text-align:center;">
                Click to plot raw data</span>`;
        }
        const content = `
            <div style="font-size:14px;border-radius:10px;">
                <span style="display:block;text-align:center;font-weight:bold;">
                    ${feature.properties.name || 'No name'}
                </span>
                <hr style="border-top:1px solid #0414f5;margin:5px 0;">
                ${Object.entries(feature.properties).filter(([key]) => key !== 'name')
                    .map(([key, value]) => `• ${key}: ${value}<br>`).join('')}
                ${note}
            </div>`;
        layer.setTooltipContent(content);
    });
}

async function loadStations(target, table, label, type, layer) {
    const data = getDataFromTable(table, true); let filter = [];
    if (type === 'rain') { filter = ['permanent', 'permanentTemp']; }
    else if (type === 'flow') { filter = ['flow']; }
    else if (type === 'level') { filter = ['overflow']; }
    const fillter = data.rows.filter(row => !filter.includes(row[1])); layer = clearMap(layer);
    if (target.checked) {
        startLoading(`Getting ${label} stations.\nThis takes a while (especially the first time). Please wait...`);
        const contents = { projectName: getState().currentProject, key: type };
        const response = await sendQuery('init_station', contents); stopLoading();
        if (response.status === "error") { alert(response.message); target.checked = false; return; }
        const stationNames = response.content.name, stationLocations = response.content.point;
        layer = await pointPloter(stationLocations, type);
        stationNames.forEach(item => fillter.push(item));
    }
    deleteTable(table); fillTable(fillter, table, true);
    if (fillter.length > 0) { plotContainer().style.display = 'flex';} else { plotContainer().style.display = 'none'; }
    return layer;
}

async function pointPloter(points, pointType) {
    let inconUrl = `/static_backend/images/station.png?v=${Date.now()}`, note = '';
    if (pointType === 'flow') { inconUrl = `/static_backend/images/water_flow.png?v=${Date.now()}`; }
    else if (pointType === 'level') { inconUrl = `/static_backend/images/water_level.png?v=${Date.now()}`; }
    else if (pointType === 'rain') { inconUrl = `/static_backend/images/rain.png?v=${Date.now()}`; }
    // else if (pointType === 'overflow') { inconUrl = `/static_backend/images/overflow.png?v=${Date.now()}`; }
    // else if (pointType === 'temperature') { inconUrl = `/static_backend/images/temperature.png?v=${Date.now()}`; }
    // else if (pointType === 'evaporation') { `/static_backend/images/evaporation.png?v=${Date.now()}`; }
    // else if (pointType === 'weir') { `/static_backend/images/weir.png?v=${Date.now()}`; }
    const tempLayer = L.geoJSON(points, {
        pointToLayer: (_, latlng) => {
            const marker = L.marker(latlng, {
                icon: L.icon({
                    iconUrl: inconUrl, iconSize: [20, 20], iconAnchor: [10, 10]
                }),
            });
            return marker;
        },
        onEachFeature: (feature, layer) => {
            layer.on('click', async () => { 
                const id = feature.properties.id, name = feature.properties.name, type = feature.properties.type;
                if (plotChecked) {
                    const startTime = plotStart().value, endTime = plotEnd().value, interval = plotInterval().value;
                    const titleY = plotInterval().selectedOptions[0].text;
                    startLoading(`Getting raw data for station '${name}'.\nThis takes a while. Please wait...`);
                    const contents = { id: [id], name: name, mode: type, startTime: startTime, endTime: endTime, interval: interval };
                    const response = await sendQuery('plot_station', contents); stopLoading();
                    if (response.status === "error") { alert(response.message); return; }
                    const chartTitle = `Station: ${name}`, titleX = 'Time';
                    await plotTimeSeries(plotStationWindow(), plotDiv(), checkboxList(), selectBox(), plotTitle(),
                        response.content, chartTitle, titleX, titleY);
                } else {
                    const data = [name, String(id), type], tableData = getDataFromTable(stationSelectedTable(), true);
                    const exitCheck = tableData.rows.some(row => row.length === data.length &&
                        row.every((value, index) => value === data[index]));
                    if (!exitCheck) { fillTable([data], stationSelectedTable(), false); }
                    selectStations(typeSelector().value, stationSelectedTable(), stationSelectedLabel());
                }
            });
            if (plotChecked) {
                note = `<hr style="border-top: 1px solid #5d5d61ff; margin: 5px 0 5px 0;">
                    <span style="display: block; font-weight: bold; text-align: center; line-height: 1.0;">Click to plot time-series data</span>`
            } else { note = ''; }
            const content = `<div style="font-size: 14px; border-radius: 10px;">
                <span style="display: block; text-align: center; font-weight: bold; line-height: 1.0;">${feature.properties.name || 'No name'}</span>
                <hr style="border-top: 1px solid #5d5d61ff; margin: 5px 0 5px 0;">
                ${Object.entries(feature.properties).filter(([key]) => key !== 'name')
                .map(([key, value]) => `<span>• ${key}: ${value}</span><br>`).join('')}${note}
            </div>`;
            layer.bindTooltip(content, { sticky: true, permanent: false, direction: 'bottom', opacity: 1, offset: [0, 10] });
        }
    }).addTo(map);
    const bounds = tempLayer.getBounds();
    if (bounds.isValid()) { 
        setTimeout(() => { map.invalidateSize(); map.fitBounds(bounds); }, 0);
    }
    return tempLayer;
}

function clearMap(layer) {
    if (layer) { map.removeLayer(layer); }
    return null;
}

function createMap() {
    if (map) return;
    const mapDiv = document.getElementById("leaflet-map");
    if (!mapDiv) { alert("Map container not found"); return; }
    map = L.map(mapDiv, { center: CENTER, zoom: ZOOM, zoomControl: false, attributionControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
    L.control.scale({imperial: false, metric: true, maxWidth: 200}).addTo(map);
    setTimeout(() => { map.invalidateSize(); }, 0);
    map.on('mousemove', function (e) { 
        if (!plotChecked && (waterFlowLayer || waterLevelLayer || overFlowLayer || tempLayer || preLayer || weirLayer || evaLayer)) {
            hoverTooltip.setLatLng(e.latlng).setContent("Left click to select station to add the download list.<br>Right click to remove the last station.");
            map.openTooltip(hoverTooltip);
        } else { if (hoverTooltip) map.closeTooltip(hoverTooltip); }
    });
    map.on('contextmenu', async function (e) { 
        e.originalEvent.preventDefault();
        if (!plotChecked) { 
            const tableData = getDataFromTable(stationSelectedTable(), true);
            if (!tableData || !tableData.rows || tableData.rows.length === 0) return;
            // Remove the last station
            const newRows = tableData.rows.slice(0, -1);
            fillTable(newRows, stationSelectedTable(), true);
        }
    });
}

function hightlightRows(table) {
    const tbody = table.querySelector('tbody');
    const trList = Array.from(tbody.querySelectorAll('tr'));
    let lastSelectedIndex = null;
    tbody.addEventListener('click', (event) => {
        const tr = event.target.closest('tr');
        if (!tr) return;
        const index = trList.indexOf(tr);
        if (event.shiftKey && lastSelectedIndex !== null) { // Shift click
            const [start, end] = [lastSelectedIndex, index].sort((a, b) => a - b);
            for (let i = start; i <= end; i++) {
                trList[i].classList.add('selected');
            }
        } else if (event.ctrlKey || event.metaKey) { // Ctrl/Cmd click
            tr.classList.toggle('selected');
        } else { // Single click
            if (tr.classList.contains('selected')) { tr.classList.remove('selected'); }
            else { tr.classList.add('selected'); }
        }
        lastSelectedIndex = index;
        const n = stationSelectedTable().querySelectorAll('tr.selected').length;
        stationSelectedLabel().innerHTML = `Station(s) selected: ${n}`;
    });
}

function selectStations(dataType, table, label) {
    const checkList = [dataType];
    if (dataType === 'permanent') { checkList.push('permanentTemp'); }
    const checkSet = new Set(checkList);
    const rows = table.querySelectorAll('tbody tr');
    let selectedCount = 0;
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length < 3) return;
        const input = cells[2].querySelector('input');
        if (!input) return;
        const value = input.value.trim();
        if (checkSet.has(value)) { selectedCount++; row.classList.add('selected');
        } else { row.classList.remove('selected'); }
    });
    if (label.style.display === 'none') { label.style.display = 'flex'; }
    label.innerHTML = `Station(s) selected: ${selectedCount}`;
}

function updateManager() {
    if (!map) { createMap(); }; compass().style.display = 'flex';
    const startOfDay = new Date(), now = new Date();
    startOfDay.setHours(0, 0, 0, 0);
    moveWindow(plotStationWindow, plotStationWindowHeader);
    hightlightRows(stationSelectedTable());
    plotStart().value = formatDate(startOfDay); plotEnd().value = formatDate(now);
    downloadStart().value = formatDate(startOfDay); downloadEnd().value = formatDate(now);
    plotClose().addEventListener('click', () => { plotStationWindow().style.display = 'none'; });
    selectBox().addEventListener("click", () => {
        checkboxList().style.display = checkboxList().style.display === 'block' ? 'none' : 'block';
    });
    document.addEventListener('click', (event) => {
        if (!dropdown().contains(event.target)) checkboxList().style.display = 'none';
    });
    // Toggle tabs
    document.querySelectorAll('[data-tab="regnbyge-tab-1"], [data-tab="regnbyge-tab-2"]').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            if (tabName === 'regnbyge-tab-1') { plotChecked = true; deleteTable(stationSelectedTable()); }
            else { plotChecked = false; }
            stationSelectedLabel().style.display = 'none';
            updateLayerTooltips(waterFlowLayer); updateLayerTooltips(waterLevelLayer);
            updateLayerTooltips(overFlowLayer); updateLayerTooltips(tempLayer);
            updateLayerTooltips(preLayer); updateLayerTooltips(evaLayer); updateLayerTooltips(weirLayer);
        }); 
    });

    waterFlowCheckbox().addEventListener('change', async (e) => { 
        waterFlowLayer = await loadStations(e.target, stationTable(), 'water flow', 'flow', waterFlowLayer);
    });
    waterLevelCheckbox().addEventListener('change', async (e) => {
        waterLevelLayer = await loadStations(e.target, stationTable(), 'water level', 'level', waterLevelLayer);
    });
    rainfallCheckbox().addEventListener('change', async (e) => {
        preLayer = await loadStations(e.target, stationTable(), 'rainfall', 'rain', preLayer);
    });
    // overFlowCheckbox().addEventListener('change', async (e) => {
    //     overFlowLayer = await loadStations(e.target, stationTable(), 'water overflow', 'overflow', overFlowLayer);
    // });
    // temperatureCheckbox().addEventListener('change', async (e) => {
    //     tempLayer = await loadStations(e.target, stationTable(), 'temperature', 'temperature', tempLayer);
    // });
    // evaporationCheckbox().addEventListener('change', async (e) => {
    //     evaLayer = await loadStations(e.target, stationTable(), 'evaporation', 'evaporation', evaLayer);
    // });
    // weirCheckbox().addEventListener('change', async (e) => {
    //     weirLayer = await loadStations(e.target, stationTable(), 'weir', 'weir', weirLayer);
    // });
    viewDataBtn().addEventListener('click', () => { viewDatafromPlot(plotDiv()) });
    downloadExcel().addEventListener('click', () => { saveToExcelFromPlot(plotDiv()) });
    typeSelector().addEventListener('change', () => {
        selectStations(typeDownload().value, stationSelectedTable(), stationSelectedLabel());
    });
    downloadBtn().addEventListener('click', async () => { 
        // e.preventDefault(); downloadBtn().blur();
        const tableData = getDataFromTable(stationSelectedTable(), true);
        const n = stationSelectedTable().querySelectorAll('tr.selected').length;
        if (tableData.rows.length === 0 || n === 0) { alert('No stations to download.'); return; }
        const startTime = downloadStart().value, endTime = downloadEnd().value;
        const downloadType = typeDownload().value, interval = downloadInterval().value;
        const stations = stationSelectedTable().querySelectorAll('tr.selected');
        startLoading(`Downloading data.\nThis takes a while. Please wait...`);
        const contents = { projectName: getState().currentProject,
            downloadType: downloadType, downloadInterval: interval,
            startTime: startTime, endTime: endTime, stations: stations };
        const response = await sendQuery('download_station', contents); stopLoading();
        alert(response.message);
    });
}

setupTabs(document); updateManager();