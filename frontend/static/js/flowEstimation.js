import { getState, CENTER, ZOOM, L } from "./constants.js";
import { sendQuery } from "./tableManager.js";
import { clearMap, plotGrid } from "./utils.js";

const loading = () => document.getElementById('loadingOverlay');
const leafletMap = () => document.getElementById('leaflet-map');
const compass = () => document.getElementById('compass');
const terrainInputText = () => document.getElementById('terrain-input-text');
const terrainInputFile = () => document.getElementById('terrain-input-file');
const terrainBtn = () => document.getElementById('terrain-btn');
const colorbar_container = () => document.getElementById('colorbar-container');
const colorbar_color = () => document.getElementById('colorbar-color');
const colorbar_title = () => document.getElementById('colorbar-title');
const colorbar_label = () => document.getElementById('colorbar-labels');







let map = null, terrainData = null, terrainLayer = null;

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
        terrainData = clearMap(terrainLayer, map);
        colorbar_container().style.display = 'none';
        terrainInputFile().click();
    });
    terrainInputFile().addEventListener('change', async (event) => { 
        const file = event.target.files[0], formData = new FormData();
        if (!file) return; startLoading('Uploading and processing terrain data. Please wait...');
        formData.append('file', file); formData.append('projectName', getState().projectName);
        const response = await fetch('/terrain_upload', { method: 'POST', body: formData });
        const data = await response.json(); stopLoading();
        if (data.status === 'error') { alert(data.message); return; }
        terrainLayer = clearMap(terrainLayer, map);
        terrainLayer = await plotGrid(data.content, map, 'Terrain (m)', colorbar_container(),
            colorbar_color(), colorbar_title(), colorbar_label(), 'terrain');
        terrainData = data.content.polygon; terrainInputText().value = file.name; terrainInputFile().value = '';
    });






}

setupTabs(document); update();