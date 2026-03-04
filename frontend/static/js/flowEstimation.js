import { getState, CENTER, ZOOM, L } from "./constants.js";
import { sendQuery } from "./tableManager.js";
import { clearMap, updateColorbar } from "./utils.js";

const loading = () => document.getElementById('loadingOverlay');
const leafletMap = () => document.getElementById('leaflet-map');
const compass = () => document.getElementById('compass');
const terrainInputText = () => document.getElementById('terrain-input-text');
const terrainInputFile = () => document.getElementById('terrain-input-file');
const terrainBtn = () => document.getElementById('terrain-btn');
const terrainCheckbox = () => document.getElementById('terrain-checkbox');
const fillBtn = () => document.getElementById('terrain-fill-btn');
const fillCheckbox = () => document.getElementById('terrain-fill-checkbox');
const flowDirectionBtn = () => document.getElementById('terrain-direction-btn');
const flowDirectionCheckbox = () => document.getElementById('terrain-direction-checkbox');
const flowAccumulationCheckbox = () => document.getElementById('terrain-accumulation-checkbox');
const watershedCheckbox = () => document.getElementById('terrain-watershed-checkbox');



const colorbar_container = () => document.getElementById('colorbar-container');
const colorbar_color = () => document.getElementById('colorbar-color');
const colorbar_title = () => document.getElementById('colorbar-title');
const colorbar_label = () => document.getElementById('colorbar-labels');







let map = null, terrainLayer = null, fillLayer = null;

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

function update() {
    if (!map) { createMap(); }; compass().style.display = 'flex';
    terrainBtn().addEventListener('click', () => { 
        terrainInputText().value = ''; terrainInputFile().value = '';
        colorbar_container().style.display = 'none';
        terrainInputFile().click();
    });
    terrainInputFile().addEventListener('change', async (event) => { 
        const file = event.target.files[0]; if (!file) return;
        const formData = new FormData();
        formData.append('file', file); formData.append('projectName', getState().projectName);
        startLoading('Uploading and processing terrain data. Please wait...');
        try {
            const response = await fetch('/terrain_upload', { method: 'POST', body: formData });
            const data = await response.json(); stopLoading();
            if (data.status === 'error') { alert(data.message); return; }
            const vmin = data.content.min, vmax = data.content.max;
            terrainLayer = clearMap(terrainLayer, map);
            terrainLayer = L.tileLayer(data.content.tile_url, { tileSize: 256 }).addTo(map);
            terrainInputText().value = file.name; event.target.value = '';
            colorbar_container().style.display = 'flex'; terrainCheckbox().checked = true;
            updateColorbar(vmin, vmax, 'Raw Terrain (m)', 'terrain',
                colorbar_color(), colorbar_title(), colorbar_label());
            terrainCheckbox().disabled = false;
        } catch (error) {
            stopLoading(); alert(`Uploading terrain failed: ${error.message}`); 
            terrainCheckbox().checked = false; terrainCheckbox().disabled = true;
        }
    });
    terrainCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) {
            if (!terrainLayer) { 
                alert('Please upload terrain data first.'); 
                e.target.checked = false; return;
            }
            terrainLayer.addTo(map);
        } else { terrainLayer.remove(); }
    });
    fillBtn().addEventListener('click', async () => {
        const layerCheck = terrainInputText().value;
        if (layerCheck === '') { 
            alert('Please upload terrain data first.'); 
            fillCheckbox().disabled = true; fillCheckbox().checked = false; return; 
        } 
        startLoading(`Running fill algorithm. Please wait ...`);
        const contents = { projectName: getState().projectName, filename: layerCheck };
        const response = await sendQuery('fill_terrain', contents); stopLoading();
        if (response.status === "error") { alert(response.message); return; }
        terrainCheckbox().checked = false; terrainCheckbox().dispatchEvent(new Event('change'));
        const vmin = response.content.min, vmax = response.content.max;
        fillLayer = clearMap(fillLayer, map);
        fillLayer = L.tileLayer(response.content.tile_url, { tileSize: 256 }).addTo(map);
        colorbar_container().style.display = 'flex';
        updateColorbar(vmin, vmax, 'Filled Terrain (m)', 'terrain',
            colorbar_color(), colorbar_title(), colorbar_label());
        fillCheckbox().disabled = false; fillCheckbox().checked = true; alert(response.message);
    });
    fillCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) {
            if (!fillLayer) { 
                alert('Please upload terrain data and run "Fill sinks/depressions" first.'); 
                e.target.checked = false; return;
            }
            fillLayer.addTo(map);
        } else { fillLayer.remove(); }
    });
    flowDirectionBtn().addEventListener('click', async () => {
        const layerCheck = terrainInputText().value;
        if (layerCheck === '') { alert('Please upload terrain data first.'); return; }
        // Check if fill terrain has been run
        const fillCheck = await sendQuery('fill_check', { projectName: getState().projectName, filename: layerCheck });
        if (fillCheck.status === 'error') { alert(fillCheck.message); return; }
        startLoading(`Running flow direction algorithm. Please wait ...`);
        const contents = { projectName: getState().projectName, filename: layerCheck };
        const response = await sendQuery('flow_direction', contents); stopLoading();
        if (response.status === "error") { alert(response.message); return; }
        terrainCheckbox().checked = false; terrainCheckbox().dispatchEvent(new Event('change'));
        const vmin = response.content.min, vmax = response.content.max;
        flowDirectionLayer = clearMap(flowDirectionLayer, map);
        flowDirectionLayer = L.tileLayer(response.content.tile_url, { tileSize: 256 }).addTo(map);
        colorbar_container().style.display = 'flex';
        updateColorbar(vmin, vmax, 'Flow direction (°)', 'flow_direction',
            colorbar_color(), colorbar_title(), colorbar_label());
        flowDirectionCheckbox().disabled = false; flowDirectionCheckbox().checked = true; alert(response.message);
    });
    flowDirectionCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) {
            if (!flowDirectionLayer) { 
                alert('Please upload terrain data and run "Flow direction" first.'); 
                e.target.checked = false; return;
            }
            flowDirectionLayer.addTo(map);
        } else { flowDirectionLayer.remove(); }
    });






}

setupTabs(document); update();