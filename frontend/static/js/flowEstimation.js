import { getState, CENTER, ZOOM, L } from "./constants.js";
import { sendQuery } from "./tableManager.js";
import { clearMap, updateColorbar } from "./utils.js";

const loading = () => document.getElementById('loadingOverlay');
const leafletMap = () => document.getElementById('leaflet-map');
const compass = () => document.getElementById('compass');
const terrainInputText = () => document.getElementById('terrain-input-text');
const terrainInputFile = () => document.getElementById('terrain-input-file');
const terrainBtn = () => document.getElementById('terrain-btn');
const fillBtn = () => document.getElementById('terrain-fill-btn');
const flowDirectionBtn = () => document.getElementById('terrain-direction-btn');
const flowAccumulationBtn = () => document.getElementById('terrain-accumulation-btn');
const catchmentExportBtn = () => document.getElementById('export-catchment-btn');
const pourpointContainer = () => document.getElementById('pourpoint-container');
const pourpointCheckbox = () => document.getElementById('pourpoint-checkbox');
const pourpointLat = () => document.getElementById('pourpoint-lat');
const pourpointLon = () => document.getElementById('pourpoint-lon');
const pourpointThreshold = () => document.getElementById('pourpoint-threshold');
const pourpointDist = () => document.getElementById('pourpoint-dist');
const exportContainer = () => document.getElementById('export-container');
const colorbar_container = () => document.getElementById('colorbar-container');
const colorbar_color = () => document.getElementById('colorbar-color');
const colorbar_title = () => document.getElementById('colorbar-title');
const colorbar_label = () => document.getElementById('colorbar-labels');


const catchmentContainer = () => document.getElementById('catchment-container');
const catchmentUploadContainer = () => document.getElementById('catchment-upload-container');
const catchmentInputFile = () => document.getElementById('catchment-input-file');
const catchmentUploadBtn = () => document.getElementById('ccatchment-upload-btn');














let map = null, terrainLayer = null, minTerrain = null, maxTerrain = null,
    fillLayer = null, minFill = null, maxFill = null, markerLayer = null,
    flowDirectionLayer = null, minFlowDirection = null, maxFlowDirection = null,
    flowAccumulationLayer = null, minFlowAccumulation = null, maxFlowAccumulation = null,
    catchmentLayer = null, lastLayer = null, isTooltipActive = false, lat=null, lon=null;

const hoverTooltip = L.tooltip({
    permanent: false, direction: 'bottom',
    sticky: true, offset: [0, 10], className: 'custom-tooltip'
});


function setupTabs(root) {
    const buttonPanels = root.querySelectorAll('.tab-btn');
    const panels = root.querySelectorAll('.main-panel');
    function activateButton(target, selectedPanel){
        const name = target.getAttribute('data-tab');
        const contents = selectedPanel.querySelectorAll('.main-panel');
        // Show corresponding panel and hide others
        contents.forEach(p => {
            const panelNameActive = p.getAttribute('data-panel') === name;
            p.setAttribute('aria-hidden', String(!panelNameActive));
        })
    }
    function activate(target) {
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
        const selectedBtn = Array.from(buttonPanels).find(btn => btn.getAttribute('aria-selected') === "true");
        const firstBtn = selectedBtn || buttonPanels[0];
        // Highlight first sub-button
        buttonPanels.forEach(btn => btn.setAttribute('aria-selected', String(btn === firstBtn)));
        // Show corresponding sub-panel
        activateButton(firstBtn, selectedPanel);
        // Click to change sub-tab
        buttonPanels.forEach(btn => {
            btn.addEventListener('click', () => { activateButton(btn, selectedPanel); });
        });
    }
    // Click to change tab
    if(buttonPanels.length > 0) activate(buttonPanels[0]);
    buttonPanels.forEach(btn => {
        btn.addEventListener('click', () => { activate(btn); });
    });
}

function startLoading(str = '') {
    loading().querySelector('.loading-text').textContent = str;
    loading().style.display = 'flex'; loading().style.pointerEvents = 'auto';
}
function stopLoading() { 
    loading().style.display = "none"; loading().style.pointerEvents = "none";
}

function createMap() {
    map = L.map(leafletMap(), { center: CENTER, zoom: ZOOM, zoomControl: false, attributionControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
    L.control.scale({imperial: false, metric: true, maxWidth: 200}).addTo(map);
    setTimeout(() => { map.invalidateSize(); }, 100);
}

function colorbarReset(vmin, vmax, title, colorKey) {
    colorbar_container().style.display = 'flex';
    updateColorbar(vmin, vmax, title, colorKey, colorbar_color(), colorbar_title(), colorbar_label());
}

async function catchmentDelineation() {
    const layerCheck = terrainInputText().value;
    if (layerCheck === '') { alert('Please upload terrain data first.'); return; }
    // Check if flow direction and flow accumulation have been run
    const contentDir = { projectName: getState().projectName, filename: layerCheck, key: 'flow_direction' };
    const flowDirectionCheck = await sendQuery('raster_check', contentDir);
    if (flowDirectionCheck.status === 'error') { alert(flowDirectionCheck.message); return; }
    const contentAcc = { projectName: getState().projectName, filename: layerCheck, key: 'flow_accumulation' };
    const flowAccumulationCheck = await sendQuery('raster_check', contentAcc);
    if (flowAccumulationCheck.status === 'error') { alert(flowAccumulationCheck.message); return; }
    if (lat === null || lon === null) { alert('Please set the pourpoint coordinates and create a catchment first.'); return; }
    const threshold = pourpointThreshold().value;
    if (threshold === '') { alert('Please set the threshold first.'); return; }
    const snapDistance = pourpointDist().value;
    if (snapDistance === '') { alert('Please set the snap distance first.'); return; }
    startLoading(`Running catchment algorithm. Please wait ...`);
    try {
        const contents = { projectName: getState().projectName, filename: layerCheck,
            lat: lat, lon: lon, threshold: threshold, snapDistance: snapDistance
        };
        const response = await sendQuery('catchment', contents);
        if (response.status === "error") { alert(response.message); return; }
        catchmentLayer = clearMap(catchmentLayer, map);
        catchmentLayer = L.geoJSON(response.content, { 
            style: { color: 'blue', weight: 2, opacity: 1 },
        }).addTo(map);
        const bounds = catchmentLayer.getBounds();
        if (bounds.isValid()) { 
            setTimeout(() => { map.invalidateSize(); map.fitBounds(bounds); }, 0);
        }
        catchmentContainer().style.display = 'flex';
    } catch (error) { 
        alert(`Running catchment algorithm failed: ${error.message}`);
        catchmentContainer().style.display = 'none';
    }
    stopLoading();
    const catchmentRadio = document.querySelector('input[name="terrain"][value="terrain-catchment"]');
    if (catchmentRadio) { catchmentRadio.checked = true; catchmentRadio.dispatchEvent(new Event('change')); }
}

function update() {
    if (!map) { createMap(); }; compass().style.display = 'flex';
    terrainBtn().addEventListener('click', () => { 
        terrainInputText().value = ''; terrainInputFile().value = '';
        colorbar_container().style.display = 'none';
        markerLayer = clearMap(markerLayer, map); terrainInputFile().click();
    });
    let lastSelectedRadio = document.querySelector('input[name="terrain"]:checked');
    document.querySelectorAll('input[name="terrain"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            [terrainLayer, fillLayer, flowDirectionLayer, 
                flowAccumulationLayer, catchmentLayer
            ].forEach(layer => { if (layer) layer.remove(); });
            const value = e.target.value; let ok = true, layer = null;
            if (value === 'hide-all') { 
                colorbar_container().style.display = 'none';
                if (lastLayer) lastLayer.remove(); lastLayer = null;
            } else if (value === 'terrain-raw') { 
                if (terrainLayer) { 
                    layer = terrainLayer;
                    colorbarReset(minTerrain, maxTerrain, 'Raw Terrain (m)', 'terrain');
                } else { 
                    alert('Please upload terrain datafirst.'); 
                    e.target.checked = false; ok = false;
                }
            } else if (value === 'terrain-fill') { 
                if (fillLayer) { 
                    layer = fillLayer;
                    colorbarReset(minFill, maxFill, 'Filled Terrain (m)', 'terrain');
                } else {
                    alert('Please upload terrain data and run "Fill sinks/depressions"  first.');
                    e.target.checked = false; ok = false;
                }
            } else if (value === 'terrain-direction') { 
                if (flowDirectionLayer) {
                    layer = flowDirectionLayer;
                    colorbarReset(minFlowDirection, maxFlowDirection, 'Flow direction (D8 code)', 'flow_direction');
                } else {
                    alert('Please upload terrain data and run "Flow direction" first.'); 
                    e.target.checked = false; ok = false;
                }
            } else if (value === 'terrain-accumulation') { 
                if (flowAccumulationLayer) {
                    layer = flowAccumulationLayer;
                    colorbarReset(minFlowAccumulation, maxFlowAccumulation, 'Flow accumulation', 'flow_accumulation');
                } else {
                    alert('Please upload terrain data and run "Flow accumulation" first.'); 
                    e.target.checked = false; ok = false;
                }
            } else if (value === 'terrain-catchment') { 
                if (catchmentLayer) {
                    layer = catchmentLayer;
                    colorbarReset(null, null, 'Catchment', 'catchment');
                } else {
                    alert('Please upload terrain data and run "Catchment" first.'); 
                    e.target.checked = false; ok = false;
                }
            }
            if (ok) { 
                if (lastLayer) lastLayer.remove();
                if (layer) layer.addTo(map);
                lastLayer = layer; lastSelectedRadio = e.target;
            } else { 
                if (lastSelectedRadio) { lastSelectedRadio.checked = true; }
                if (lastLayer) lastLayer.addTo(map); e.target.checked = false;
            }
        });
    });
    terrainInputFile().addEventListener('change', async (event) => { 
        const file = event.target.files[0]; if (!file) return;
        const formData = new FormData();
        formData.append('file', file); formData.append('projectName', getState().projectName);
        startLoading('Uploading and processing terrain data. Please wait...');
        try {
            const response = await fetch('/terrain_upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.status === 'error') { alert(data.message); return; }
            minTerrain = data.content.min, maxTerrain = data.content.max;
            terrainLayer = clearMap(terrainLayer, map);
            terrainLayer = L.tileLayer(data.content.tile_url, { tileSize: 256 }).addTo(map);
            terrainInputText().value = file.name; event.target.value = '';
        } catch (error) { alert(`Uploading terrain failed: ${error.message}`); }
        stopLoading();
        const terrainRadio = document.querySelector('input[name="terrain"][value="terrain-raw"]');
        if (terrainRadio) { terrainRadio.checked = true; terrainRadio.dispatchEvent(new Event('change')); }
    });
    fillBtn().addEventListener('click', async () => {
        const layerCheck = terrainInputText().value;
        if (layerCheck === '') { alert('Please upload terrain data first.'); return; } 
        startLoading(`Running fill algorithm. Please wait ...`);
        try {
            const contents = { projectName: getState().projectName, filename: layerCheck };
            const response = await sendQuery('fill_terrain', contents); 
            if (response.status === "error") { alert(response.message); return; }
            minFill = response.content.min, maxFill = response.content.max;
            fillLayer = clearMap(fillLayer, map);
            fillLayer = L.tileLayer(response.content.tile_url, { tileSize: 256 }).addTo(map);
        } catch (error) { alert(`Running fill algorithm failed: ${error.message}`); }
        stopLoading();
        const fillRadio = document.querySelector('input[name="terrain"][value="terrain-fill"]');
        if (fillRadio) { fillRadio.checked = true; fillRadio.dispatchEvent(new Event('change')); }
    });
    flowDirectionBtn().addEventListener('click', async () => {
        const layerCheck = terrainInputText().value;
        if (layerCheck === '') { alert('Please upload terrain data first.'); return; }
        // Check if fill terrain has been run
        const content = { projectName: getState().projectName, filename: layerCheck, key: 'fill' };
        const fillCheck = await sendQuery('raster_check', content);
        if (fillCheck.status === 'error') { alert(fillCheck.message); return; }
        startLoading(`Running flow direction algorithm. Please wait ...`);
        try {
            const contents = { projectName: getState().projectName, filename: layerCheck };
            const response = await sendQuery('flow_direction', contents);
            if (response.status === "error") { alert(response.message); return; }
            minFlowDirection = response.content.min, maxFlowDirection = response.content.max;
            flowDirectionLayer = clearMap(flowDirectionLayer, map);
            flowDirectionLayer = L.tileLayer(response.content.tile_url, { tileSize: 256 }).addTo(map);
        } catch (error) { alert(`Running flow direction algorithm failed: ${error.message}`); }
        stopLoading();
        const flowDirectionRadio = document.querySelector('input[name="terrain"][value="terrain-direction"]');
        if (flowDirectionRadio) { flowDirectionRadio.checked = true; flowDirectionRadio.dispatchEvent(new Event('change')); }
    });
    flowAccumulationBtn().addEventListener('click', async () => {
        const layerCheck = terrainInputText().value;
        if (layerCheck === '') { alert('Please upload terrain data first.'); return; }
        // Check if flow direction has been run
        const content = { projectName: getState().projectName, filename: layerCheck, key: 'flow_direction' };
        const flowDirectionCheck = await sendQuery('raster_check', content);
        if (flowDirectionCheck.status === 'error') { alert(flowDirectionCheck.message); return; }
        startLoading(`Running flow accumulation algorithm. Please wait ...`);
        pourpointContainer().style.display = 'none'; exportContainer().style.display = 'none';
        try {
            const contents = { projectName: getState().projectName, filename: layerCheck };
            const response = await sendQuery('flow_accumulation', contents);
            if (response.status === "error") { alert(response.message); return; }
            minFlowAccumulation = response.content.min, maxFlowAccumulation = response.content.max;
            flowAccumulationLayer = clearMap(flowAccumulationLayer, map);
            flowAccumulationLayer = L.tileLayer(response.content.tile_url, { tileSize: 256 }).addTo(map);
            pourpointContainer().style.display = 'flex'; exportContainer().style.display = 'flex';
        } catch (error) { alert(`Running flow accumulation algorithm failed: ${error.message}`); }
        stopLoading();
        const flowAccumulationRadio = document.querySelector('input[name="terrain"][value="terrain-accumulation"]');
        if (flowAccumulationRadio) { flowAccumulationRadio.checked = true; flowAccumulationRadio.dispatchEvent(new Event('change')); }
    });
    pourpointCheckbox().addEventListener('change', (e) => {
        const mapContainer = map.getContainer();
        if (e.target.checked) { 
            mapContainer.style.cursor = 'crosshair'; isTooltipActive = true;
            map.on("click", async function (e) {
                pourpointLat().value = e.latlng.lat.toFixed(8);
                pourpointLon().value = e.latlng.lng.toFixed(8);
                lat = e.latlng.lat; lon = e.latlng.lng;
                if (markerLayer) { map.removeLayer(markerLayer); markerLayer = null; }
                markerLayer = L.circleMarker(e.latlng, {
                    radius: 4, fillColor: 'blue', color: 'red', weight: 2, opacity: 1, fillOpacity: 1
                }).addTo(map); await catchmentDelineation();
            });
            map.on("mousemove", function (e) {
                if (isTooltipActive) { 
                    hoverTooltip.setLatLng(e.latlng).setContent(`Click to set the pourpoint coordinates.`);
                    map.openTooltip(hoverTooltip);
                } else { map.closeTooltip(hoverTooltip); mapContainer.style.cursor = 'grab'; }
            });
        } else { 
            mapContainer.style.cursor = 'grab'; isTooltipActive = false;
            pourpointLat().value = ''; pourpointLon().value = ''; lat = null; lon = null;
        }
    });
    catchmentExportBtn().addEventListener('click', async () => { 
        const layerCheck = terrainInputText().value;
        if (layerCheck === '') { alert('Please upload terrain data first.'); return; }
        if (catchmentLayer === null) { alert('Please run catchment delineation first.'); return; }
        try { 
            const data = JSON.stringify(catchmentLayer.toGeoJSON(), null, 2);
            if ('showSaveFilePicker' in window) {
                // --- Chrome/Edge/Opera ---
                const fileHandle = await window.showSaveFilePicker({
                    suggestedName: 'catchment.geojson',
                    types: [{
                        description: 'GeoJSON',
                        accept: { 'application/json': ['.geojson'] }
                    }]
                });
                const writable = await fileHandle.createWritable();
                await writable.write(data); await writable.close();
            } else {
                // --- Fallback cho Firefox, Safari ---
                const blob = new Blob([data], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'catchment.geojson';
                document.body.appendChild(a); a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
            alert('Catchment delineation exported successfully.');
        } catch (error) { alert(`Exporting catchment delineation failed: ${error.message}`); }
    });
    document.querySelectorAll('input[name="catchment"]').forEach(radio => {
        radio.addEventListener('change', (e) => { 
            if (e.target.value === 'catchment-upload') { 
                catchmentUploadContainer().style.display = 'block';
            } else {
                catchmentUploadContainer().style.display = 'none';
            }
        });
    });
    catchmentUploadBtn().addEventListener('click', () => catchmentInputFile().click());
    catchmentInputFile().addEventListener('change', async (event) => {
        const file = event.target.files[0]; if (!file) return; 
        const formData = new FormData();
        formData.append('file', file);
        startLoading('Uploading catchment data. Please wait...');
        try {
            const response = await fetch('/catchment_upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.status === 'error') { alert(data.message); return; }
            catchmentLayer = clearMap(catchmentLayer, map);
            catchmentLayer = L.geoJSON(data.content).addTo(map);
        } catch (error) { alert(`Uploading catchment failed: ${error.message}`); }
        stopLoading(); event.target.value = '';
    });




    







}

setupTabs(document); update();