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
// const flowDirectionCheckbox = () => document.getElementById('terrain-direction-checkbox');
// const flowAccumulationCheckbox = () => document.getElementById('terrain-accumulation-checkbox');
// const watershedCheckbox = () => document.getElementById('terrain-watershed-checkbox');



const colorbar_container = () => document.getElementById('colorbar-container');
const colorbar_color = () => document.getElementById('colorbar-color');
const colorbar_title = () => document.getElementById('colorbar-title');
const colorbar_label = () => document.getElementById('colorbar-labels');







let map = null, terrainLayer = null, minTerrain = null, maxTerrain = null,
    fillLayer = null, minFill = null, maxFill = null,
    flowDirectionLayer = null, minFlowDirection = null, maxFlowDirection = null,
    flowAccumulationLayer = null, minFlowAccumulation = null, maxFlowAccumulation = null,
    watershedLayer = null, lastLayer = null;

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

function update() {
    if (!map) { createMap(); }; compass().style.display = 'flex';
    terrainBtn().addEventListener('click', () => { 
        terrainInputText().value = ''; terrainInputFile().value = '';
        colorbar_container().style.display = 'none';
        terrainInputFile().click();
    });
    let lastSelectedRadio = document.querySelector('input[name="terrain"]:checked');
    document.querySelectorAll('input[name="terrain"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            [terrainLayer, fillLayer, flowDirectionLayer, 
                flowAccumulationLayer, watershedLayer
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
                    colorbarReset(minFlowDirection, maxFlowDirection, 'Flow direction (°)', 'flow_direction');
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
            } else if (value === 'terrain-watershed') { 
                if (watershedLayer) {
                    layer = watershedLayer;
                    colorbarReset(null, null, 'Watershed', 'watershed');
                } else {
                    alert('Please upload terrain data and run "Watershed" first.'); 
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
            alert(response.message);
        } catch (error) { alert(`Running fill algorithm failed: ${error.message}`); }
        stopLoading();
        const fillRadio = document.querySelector('input[name="terrain"][value="terrain-fill"]');
        if (fillRadio) { fillRadio.checked = true; fillRadio.dispatchEvent(new Event('change')); }
    });
    flowDirectionBtn().addEventListener('click', async () => {
        const layerCheck = terrainInputText().value;
        if (layerCheck === '') { alert('Please upload terrain data first.'); return; }
        // Check if fill terrain has been run
        const fillCheck = await sendQuery('fill_check', { projectName: getState().projectName, filename: layerCheck });
        if (fillCheck.status === 'error') { alert(fillCheck.message); return; }
        startLoading(`Running flow direction algorithm. Please wait ...`);
        try {
            const contents = { projectName: getState().projectName, filename: layerCheck };
            const response = await sendQuery('flow_direction', contents);
            if (response.status === "error") { alert(response.message); return; }
            minFlowDirection = response.content.min, maxFlowDirection = response.content.max;
            flowDirectionLayer = clearMap(flowDirectionLayer, map);
            flowDirectionLayer = L.tileLayer(response.content.tile_url, { tileSize: 256 }).addTo(map);
            alert(response.message);
        } catch (error) { alert(`Running flow direction algorithm failed: ${error.message}`); }
        stopLoading();
        const flowDirectionRadio = document.querySelector('input[name="terrain"][value="terrain-direction"]');
        if (flowDirectionRadio) { flowDirectionRadio.checked = true; flowDirectionRadio.dispatchEvent(new Event('change')); }
    });







}

setupTabs(document); update();