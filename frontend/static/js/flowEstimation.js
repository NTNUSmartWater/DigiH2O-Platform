import { getState, CENTER, ZOOM, L } from "./constants.js";
import { sendQuery, fillTable, getDataFromTable, deleteTable } from "./tableManager.js";
import { clearMap, updateColorbar, getColor } from "./utils.js";

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
const catchmentUploadContainer = () => document.getElementById('catchment-upload-container');
const catchmentInputFile = () => document.getElementById('catchment-input-file');
const catchmentUploadBtn = () => document.getElementById('catchment-upload-btn');
const soilInputText = () => document.getElementById('soil-input-text');
const soilInputFile = () => document.getElementById('soil-input-file');
const soilBtn = () => document.getElementById('soil-btn');
const soilCheckbox = () => document.getElementById('soil-checker-checkbox');
const soilInvalidCheckerBtn = () => document.getElementById('soil-invalid-checker-btn');
const soilIds = () => document.getElementById('soil-id');
const soilTypes = () => document.getElementById('soil-type');
const soilClipBtn = () => document.getElementById('soil-clip-btn');
const assignSoilBtn = () => document.getElementById('assign-soil-btn');
const saveSoilBtn = () => document.getElementById('save-soil-btn');
const soilAttributesTable = () => document.getElementById('soil-attributes-table');

const landInputFile = () => document.getElementById('land-input-file');
const landInputText = () => document.getElementById('land-input-text');
const landBtn = () => document.getElementById('land-btn');
const landCheckbox = () => document.getElementById('land-checker-checkbox');
const landInvalidCheckerBtn = () => document.getElementById('land-invalid-checker-btn');












let map = null, terrainLayer = null, minTerrain = null, maxTerrain = null,
    fillLayer = null, minFill = null, maxFill = null, markerLayer = null,
    flowDirectionLayer = null, minFlowDirection = null, maxFlowDirection = null,
    flowAccumulationLayer = null, minFlowAccumulation = null, maxFlowAccumulation = null,
    catchmentLayer = null, lastLayer = null, lat=null, lon=null,
    soilLayer = null, isPourpointActive = false, isSoilActive = false,
    landLayer = null, isLandActive = false;

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
    map.on("mousemove", function (e) {
        if (isPourpointActive) { 
            hoverTooltip.setLatLng(e.latlng).setContent("Click to set the pourpoint coordinates.");
            map.openTooltip(hoverTooltip); return;
        }
        map.closeTooltip(hoverTooltip); map.getContainer().style.cursor = 'grab';
    });
    map.on('click', async function (e) {
        if (isPourpointActive) {
            pourpointLat().value = e.latlng.lat.toFixed(8);
            pourpointLon().value = e.latlng.lng.toFixed(8);
            lat = e.latlng.lat; lon = e.latlng.lng;
            markerLayer = clearMap(markerLayer, map);
            markerLayer = L.circleMarker(e.latlng, {
                radius: 4, fillColor: 'blue', color: 'red', weight: 2, opacity: 1, fillOpacity: 1
            }).addTo(map); await catchmentDelineation(); 
        }
    });
}

function colorbarReset(vmin, vmax, title, colorKey) {
    colorbar_container().style.display = 'flex';
    updateColorbar(vmin, vmax, title, colorKey, colorbar_color(), colorbar_title(), colorbar_label());
}

async function catchmentDelineation() {
    const layerCheck = terrainInputText().value;
    if (layerCheck === '') { alert('Please upload terrain data first.'); return; }
    // Check if flow direction and flow accumulation have been run
    const contentDir = { projectName: getState().currentProject, filename: layerCheck, key: 'flow_direction' };
    const flowDirectionCheck = await sendQuery('raster_check', contentDir);
    if (flowDirectionCheck.status === 'error') { alert(flowDirectionCheck.message); return; }
    const contentAcc = { projectName: getState().currentProject, filename: layerCheck, key: 'flow_accumulation' };
    const flowAccumulationCheck = await sendQuery('raster_check', contentAcc);
    if (flowAccumulationCheck.status === 'error') { alert(flowAccumulationCheck.message); return; }
    if (lat === null || lon === null) { alert('Please set the pourpoint coordinates and create a catchment first.'); return; }
    const threshold = pourpointThreshold().value;
    if (threshold === '') { alert('Please set the threshold first.'); return; }
    const snapDistance = pourpointDist().value;
    if (snapDistance === '') { alert('Please set the snap distance first.'); return; }
    startLoading(`Running catchment algorithm. Please wait ...`);
    const currentCatchment = document.querySelector('input[name="catchment"][value="catchment-current"]');
    try {
        const contents = { projectName: getState().currentProject, filename: layerCheck,
            lat: lat, lon: lon, threshold: threshold, snapDistance: snapDistance
        };
        const response = await sendQuery('catchment', contents);
        if (response.status === "error") { alert(response.message); return; }
        catchmentLayer = clearMap(catchmentLayer, map);
        catchmentLayer = L.geoJSON(response.content, { style: { color: 'red', weight: 2, opacity: 1 }}).addTo(map);
        const bounds = catchmentLayer.getBounds();
        if (bounds.isValid()) { 
            setTimeout(() => { map.invalidateSize(); map.fitBounds(bounds); }, 0);
        }
        if (currentCatchment) { currentCatchment.checked = true; }
    } catch (error) { 
        alert(`Running catchment algorithm failed: ${error.message}`);
        if (currentCatchment) { currentCatchment.checked = false; }
    }
    stopLoading();
    const catchmentRadio = document.querySelector('input[name="terrain"][value="terrain-catchment"]');
    if (catchmentRadio) { catchmentRadio.checked = true; catchmentRadio.dispatchEvent(new Event('change')); }
}

function setActiveMode() { 
    isPourpointActive = false; isSoilActive = false;
    markerLayer = clearMap(markerLayer, map);
    const mapContainer = map.getContainer();
    mapContainer.style.cursor = "grab";
    if (pourpointCheckbox().checked) { pourpointCheckbox().checked = false; }
    pourpointCheckbox().dispatchEvent(new Event("change"));
    if (map) { map.closeTooltip(hoverTooltip); }
}

function buildTooltip(props, key) {
    if (key === 'soil') {
        return `
            <div style="font-weight: bold; text-align: center;">ID: ${props._id || 'Unknown'}</div>
            <hr style="margin: 5px 0 5px 0;">
            <strong>• Type:</strong> ${props.soil}<br>
            <strong>• θS (m³/m³):</strong> ${props.theta_s ?? 'Unknown'}<br>
            <strong>• θR (m³/m³):</strong> ${props.theta_r ?? 'Unknown'}<br>
            <strong>• KsatVer (mm/day):</strong> ${props.k_sat_ver ?? 0}<br>
            <strong>• SoilDepth (mm):</strong> ${props.soil_depth ?? 0}<br>
            <strong>• Conductivity decay:</strong> ${props.conductivity_decay ?? 0}<br>
            <strong>• Brooks-Corey:</strong> ${props.brooks_corey ?? 'Unknown'}<br>
            <hr style="margin: 5px 0 5px 0;">
            <strong>Click to change attributes</strong>
        `;
    } else if (key === 'land') {
        return `
            <div style="font-weight: bold; text-align: center;">ID: ${props._id || 'Unknown'}</div>
            <hr style="margin: 5px 0 5px 0;">
            <strong>• Type:</strong> ${props.land}<br>
            <strong>• Leaf Area Index (ha):</strong> ${props.LAI ?? 0}<br>
            <strong>• Root Depth (m):</strong> ${props.root_depth ?? 0}<br>
            <strong>• Interception (mm):</strong> ${props.interception ?? 'Unknown'}<br>
            <strong>• Manning roughness:</strong> ${props.manning_n ?? 'Unknown'}<br>
            <strong>• Albedo:</strong> ${props.albedo ?? 'Unknown'}<br>
            <strong>• Crop coefficient:</strong> ${props.kc ?? 'Unknown'}<br>
            <hr style="margin: 5px 0 5px 0;">
            <strong>Click to change attributes</strong>
        `;
    }
}

async function mapPlotter(data, map, key) {
    const layer = L.geoJSON(data, { 
        pointToLayer: (feature, latlng)  => { return null; }, 
        style: feature => { 
            const id = feature.properties._id;
            return { 
                color: 'black', weight: 1, opacity: 1, 
                fillOpacity: 0.8, fillColor: getColor(id) 
            }; 
        },
        onEachFeature: (feature, featureLayer) => { 
            featureLayer.on('click', () => { 
                // Reset the color of all features
                layer.eachLayer(l => { 
                    const id = l.feature.properties._id;
                    l.setStyle({
                        color: 'black', weight: 1, opacity: 1, 
                        fillOpacity: 0.8, fillColor: getColor(id) 
                    }); 
                });
                // Highlight the clicked feature
                featureLayer.setStyle({ color: 'yellow', weight: 3 }); 
                if (key === 'soil') { soilModifier(feature.properties); }
                if (key === 'land') { landUseModifier(feature.properties); }
            });
            featureLayer.bindTooltip(`${buildTooltip(feature.properties, key)}`, {sticky: true});
        }
    }).addTo(map);
    return layer;
}

function soilModifier(props) { 
    soilIds().textContent = '';
    var option = document.createElement('option');
    option.value = props._id; option.textContent = props._id;
    soilIds().appendChild(option);
    const values = [
        props._id, props.soil, props.theta_s, props.theta_r, props.k_sat_ver, 
        props.soil_depth, props.conductivity_decay, props.brooks_corey
    ];
    fillTable([values], soilAttributesTable());
}

async function geoJSONExporter(data, fileName) {
    try { 
        const json = JSON.stringify(data, null, 2);
        if ('showSaveFilePicker' in window) {
            // --- Chrome/Edge/Opera ---
            const fileHandle = await window.showSaveFilePicker({
                suggestedName: fileName,
                types: [{
                    description: 'GeoJSON',
                    accept: { 'application/json': ['.geojson'] }
                }]
            });
            const writable = await fileHandle.createWritable();
            await writable.write(json); await writable.close();
        } else {
            // --- Fallback cho Firefox, Safari ---
            const blob = new Blob([json], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = fileName;
            document.body.appendChild(a); a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        alert(`Exporting succeeded: ${fileName}`);
    } catch (error) { alert(`Exporting failed: ${error.message}`); }
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
                lastLayer = clearMap(lastLayer, map);
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
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function () { setActiveMode(); });
    });
    terrainInputFile().addEventListener('change', async (event) => { 
        const file = event.target.files[0]; if (!file) return;
        const formData = new FormData();
        formData.append('file', file); formData.append('projectName', getState().currentProject);
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
            const contents = { projectName: getState().currentProject, filename: layerCheck };
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
        const content = { projectName: getState().currentProject, filename: layerCheck, key: 'fill' };
        const fillCheck = await sendQuery('raster_check', content);
        if (fillCheck.status === 'error') { alert(fillCheck.message); return; }
        startLoading(`Running flow direction algorithm. Please wait ...`);
        try {
            const contents = { projectName: getState().currentProject, filename: layerCheck };
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
        const content = { projectName: getState().currentProject, filename: layerCheck, key: 'flow_direction' };
        startLoading(`Checking flow direction data. Please wait ...`);
        const flowDirectionCheck = await sendQuery('raster_check', content); stopLoading();
        if (flowDirectionCheck.status === 'error') { alert(flowDirectionCheck.message); return; }
        startLoading(`Running flow accumulation algorithm. Please wait ...`);
        pourpointContainer().style.display = 'none'; exportContainer().style.display = 'none';
        try {
            const contents = { projectName: getState().currentProject, filename: layerCheck };
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
            mapContainer.style.cursor = 'crosshair'; isPourpointActive = true;
        } else { 
            pourpointLat().value = ''; pourpointLon().value = ''; lat = null; lon = null;
        }
    });
    catchmentExportBtn().addEventListener('click', async () => { 
        const layerCheck = terrainInputText().value;
        if (layerCheck === '') { alert('Please upload terrain data first.'); return; }
        if (catchmentLayer === null) { alert('Please select pourpoint and create a catchment first.'); return; }
        await geoJSONExporter(catchmentLayer.toGeoJSON(), 'catchment.geojson');
    });
    document.querySelectorAll('input[name="catchment"]').forEach(radio => {
        radio.addEventListener('change', (e) => { 
            catchmentLayer = clearMap(catchmentLayer, map);
            const tiles = document.querySelectorAll('.main-panel[data-panel="terrain-tab"] .tile');
            if (e.target.value === 'catchment-upload') { 
                catchmentUploadContainer().style.display = 'block';
                tiles.forEach(tile => {
                    const title = tile.querySelector('h3')?.textContent.trim();
                    if (title !== "Catchment Options") { tile.style.display = 'none';}
                });
            } else {
                catchmentUploadContainer().style.display = 'none';
                tiles.forEach(tile => {
                    const title = tile.querySelector('h3')?.textContent.trim();
                    if (title !== "Catchment Options") { tile.style.display = 'block';}
                });
            }
        });
    });
    catchmentUploadBtn().addEventListener('click', () => catchmentInputFile().click());
    catchmentInputFile().addEventListener('change', async (event) => {
        const file = event.target.files[0]; if (!file) return; 
        const formData = new FormData(); formData.append('file', file);
        startLoading('Uploading catchment data. Please wait...');
        try {
            const response = await fetch('/catchment_upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.status === 'error') { alert(data.message); return; }
            catchmentLayer = clearMap(catchmentLayer, map);
            catchmentLayer = L.geoJSON(data.content, { style: { color: 'red', weight: 2, opacity: 1 }}).addTo(map);
        } catch (error) { alert(`Uploading catchment failed: ${error.message}`); }
        stopLoading(); event.target.value = '';
    });
    soilBtn().addEventListener('click', () => soilInputFile().click());
    soilInputFile().addEventListener('change', async (event) => { 
        const file = event.target.files[0]; if (!file) return;
        const formData = new FormData(); formData.append('file', file); 
        formData.append('projectName', getState().currentProject); formData.append('key', 'soil');
        startLoading('Uploading and processing soil data. Please wait...');
        try {
            const response = await fetch('/data_upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.status === 'error') { alert(data.message); return; }
            soilLayer = clearMap(soilLayer, map);
            soilLayer = await mapPlotter(data.content, map, 'soil');
            soilInputText().value = file.name; event.target.value = ''; 
            soilCheckbox().checked = true; isSoilActive = true;
            soilInvalidCheckerBtn().style.display = 'block'; 
        } catch (error) { 
            alert(`Uploading soil data failed: ${error.message}`); 
            soilInvalidCheckerBtn().style.display = 'none';
            soilCheckbox().checked = false; isSoilActive = false;
        }
        stopLoading(); colorbar_container().style.display = 'none';
    });
    soilCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) { 
            if (!soilLayer) { 
                alert('Please upload/create a soil layer first.');
                e.target.checked = false; soilInputFile().click(); return; 
            } else { soilLayer.addTo(map); }
        } else { soilLayer.remove(); }
    });
    soilInvalidCheckerBtn().addEventListener('click', () => { 
        if (soilLayer === null) { alert('Please upload/create a soil layer first.'); return; }
        deleteTable(soilAttributesTable());
        startLoading('Checking for invalid soil polygons. Please wait...');
        setTimeout(() => { 
            const invalidSoil = [], invalidIDs = [];
            soilLayer.eachLayer((layer) => { 
                // Highlight invalid polygons
                if (layer.feature.properties.soil === '') {
                    layer.setStyle({ color: 'yellow', weight: 3 });
                    const id = layer.feature.properties._id;
                    const values = [
                        id,'Unknown','Unknown','Unknown',
                        'Unknown','Unknown','Unknown','Unknown'
                    ]
                    invalidSoil.push(values); invalidIDs.push(id);
                }
            }); stopLoading();
            if (invalidSoil.length === 0) { alert('All soil polygons are valid.'); 
            } else { 
                fillTable(invalidSoil, soilAttributesTable());
                alert(`Number of invalid soil polygons: ${invalidSoil.length}.`);
                // Add ids to invalid id list
                invalidIDs.forEach((id) => { 
                    var option = document.createElement('option');
                    option.value = id; option.textContent = id;
                    soilIds().appendChild(option);
                });
            }
        }, 50);
    });
    soilClipBtn().addEventListener('click', async () => { 
        if (soilLayer !== null && catchmentLayer !== null) { 
            const content = { baseLayer: soilLayer.toGeoJSON(), clipLayer: catchmentLayer.toGeoJSON() };
            startLoading(`Clipping soil layer with catchment layer. Please wait ...`);
            const request = await sendQuery('polygon_clip', content); stopLoading();
            if (request.status === 'error') { alert(request.message); return; }
            catchmentLayer.remove(); soilLayer = clearMap(soilLayer, map);
            soilLayer = await mapPlotter(request.content, map, 'soil');
        } else {alert('Please upload/create a soil layer and a catchment layer.');}
    });
    assignSoilBtn().addEventListener('click', async () => { 
        if (soilLayer === null) { alert('Please upload/create a soil layer first.'); return; }
        const soilID = soilIds().value;
        if (soilID === '') { alert('Please select a soil polygon first.'); return; }
        const soilType = soilTypes().options[soilTypes().selectedIndex].textContent;
        startLoading('Assigning soil type to selected polygon. Please wait...');
        const response = await sendQuery('assign_soil_type', { soilType: soilType });
        if (response.status === "error") { alert(response.message); return; }
        soilLayer.eachLayer((layer) => { 
            if (layer.feature.properties._id === Number(soilID)) {
                const values = [...response.content];
                layer.feature.properties.soil = soilType;
                layer.feature.properties.theta_s = values[0];
                layer.feature.properties.theta_r = values[1];
                layer.feature.properties.k_sat_ver = values[2];
                layer.feature.properties.soil_depth = values[3];
                layer.feature.properties.conductivity_decay = values[4];
                layer.feature.properties.brooks_corey = values[5];
                values.unshift(soilID);
                fillTable([values], soilAttributesTable());
                alert(`Soil type "${soilType}" assigned to polygon "${soilID}".`);
                layer.setStyle({ color: 'green', weight: 3, fillOpacity: 0.8, fillColor: 'green' });
            }
            if (layer.getTooltip()) {
                layer.getTooltip().setContent( buildTooltip(layer.feature.properties, 'soil'));
            }
        }); stopLoading();
    });
    saveSoilBtn().addEventListener('click', async () => { 
        if (soilLayer === null) { alert('Please upload/create a soil layer first.'); return; }
        await geoJSONExporter(soilLayer.toGeoJSON(), 'soil.geojson');
    });
    landBtn().addEventListener('click',  () => { landInputFile().click(); });
    landInputFile().addEventListener('change', async (event) => {
        const file = event.target.files[0]; if (!file) return;
        const formData = new FormData(); formData.append('file', file); 
        formData.append('projectName', getState().currentProject); formData.append('key', 'land');
        startLoading('Uploading and processing Land Cover data. Please wait...');
        try { 
            const response = await fetch('/data_upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.status === "error") { alert(data.message); return; }
            landUseLayer = clearMap(landUseLayer, map);
            landUseLayer = await mapPlotter(data.content, map, 'land');
            landInputText().value = file.name; event.target.value = '';
            landCheckbox().checked = true; isLandActive = true;
            landInvalidCheckerBtn().style.display = 'block';
        } catch (err) {
            alert(`Uploading Land Use/Land Cover data failed. Error: ${err}`);
            landInvalidCheckerBtn().style.display = 'none';
            landCheckbox().checked = false; isLandActive = false;
        }
        stopLoading(); colorbar_container().style.display = 'none';
    });
    landCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) { 
            if (!landLayer) { 
                alert('Please upload/create a land layer first.');
                e.target.checked = false; landInputFile().click(); return; 
            } else { landLayer.addTo(map); }
        } else { landLayer.remove(); }
    });





    // saveLandBtn().addEventListener('click', async () => { 
    //     if (landUseLayer === null) { alert('Please upload/create a land use layer first.'); return; }
    //     await geoJSONExporter(landUseLayer.toGeoJSON(), 'landUse.geojson');
    // });



    







}

setupTabs(document); update();