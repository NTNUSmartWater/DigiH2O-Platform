import { getState, CENTER, ZOOM, L } from "./constants.js";
import { sendQuery, fillTable, getDataFromTable, deleteTable, csvUploader } from "./tableManager.js";
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
const soilClipBtn = () => document.getElementById('soil-clip-btn');
const soilIds = () => document.getElementById('soil-id');
const soilTypes = () => document.getElementById('soil-type');
const assignSoilBtn = () => document.getElementById('assign-soil-btn');
const saveSoilBtn = () => document.getElementById('save-soil-btn');
const soilAttributesTable = () => document.getElementById('soil-attributes-table');
const landInputFile = () => document.getElementById('land-input-file');
const landInputText = () => document.getElementById('land-input-text');
const landBtn = () => document.getElementById('land-btn');
const landCheckbox = () => document.getElementById('land-checker-checkbox');
const landInvalidCheckerBtn = () => document.getElementById('land-invalid-checker-btn');
const landClipBtn = () => document.getElementById('land-clip-btn');
const landIds = () => document.getElementById('land-id');
const landTypes = () => document.getElementById('land-type');
const assignLandBtn = () => document.getElementById('assign-land-btn');
const saveLandBtn = () => document.getElementById('save-land-btn');
const landAttributesTable = () => document.getElementById('land-attributes-table');
const riverInputFile = () => document.getElementById('river-input-file');
const riverUploadBtn = () => document.getElementById('river-upload-btn');
const riverInputText = () => document.getElementById('river-network-input-text');
const thresholdLabel = () => document.getElementById('river-threshold-label');
const riverThreshold = () => document.getElementById('river-network-threshold');
const riverAttributesTable = () => document.getElementById('river-attributes-table');
const assignRiverBtn = () => document.getElementById('river-assign-btn');
const saveRiverBtn = () => document.getElementById('river-save-btn');
const lakeInputFile = () => document.getElementById('lake-input-file');
const lakeUploadBtn = () => document.getElementById('lake-upload-btn');
const riverLakeClipBtn = () => document.getElementById('river-clip-lake-btn');
const riverCatchmentClipBtn = () => document.getElementById('river-clip-catchment-btn');
const riverDeleteBtn = () => document.getElementById('river-delete-btn');
const riverCheckbox = () => document.getElementById('river-checker-checkbox');
const initialTopMoisture = () => document.getElementById('initial-top-moisture');
const initialSubMoisture = () => document.getElementById('initial-sub-moisture');
const initialGroundwater = () => document.getElementById('initial-groundwater');
const initialOverlandFlow = () => document.getElementById('initial-overland-flow');
const initialRiverStorage = () => document.getElementById('initial-river-storage');
const initialLakeStorage = () => document.getElementById('initial-lake-storage');
const initialSnowDepth = () => document.getElementById('initial-snow-depth');
const initialWaterDepth = () => document.getElementById('initial-water-depth');
const initialSaturationDeficit = () => document.getElementById('initial-saturation-deficit');

const weatherCSVContainer = () => document.getElementById('weather-csv-container');
const weatherInputFile = () => document.getElementById('weather-input-file');
const weatherInputText = () => document.getElementById('weather-input-text');
const weatherBtn = () => document.getElementById('weather-btn');
const weatherStationSelector = () => document.getElementById('weather-station');
const weatherStationContainer = () => document.getElementById('weather-station-container');
const weatherStationStartContainer = () => document.getElementById('weather-station-start');
const weatherStationEndContainer = () => document.getElementById('weather-station-end');
const weatherStart = () => document.getElementById('weather-start-date');
const weatherEnd = () => document.getElementById('weather-end-date');
const weatherAttributesTable = () => document.getElementById('weather-attributes-table');






let map = null, terrainLayer = null, minTerrain = null, maxTerrain = null,
    fillLayer = null, minFill = null, maxFill = null, markerLayer = null,
    flowDirectionLayer = null, minFlowDirection = null, maxFlowDirection = null,
    flowAccumulationLayer = null, minFlowAccumulation = null, maxFlowAccumulation = null,
    catchmentLayer = null, lastLayer = null, lat=null, lon=null, soilLayer = null, 
    isPourpointActive = false, landLayer = null, riverLayer = null, lakeLayer = null;

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
    isPourpointActive = false;
    markerLayer = clearMap(markerLayer, map);
    const mapContainer = map.getContainer(); mapContainer.style.cursor = "grab";
    if (pourpointCheckbox().checked) { pourpointCheckbox().checked = false; }
    pourpointCheckbox().dispatchEvent(new Event("change"));
    if (map) { map.closeTooltip(hoverTooltip); }
}

function buildTooltip(props, key) {
    if (key === 'soil') {
        return `
            <div style="font-weight: bold; text-align: center;">ID: ${props._id || 'Unknown'}</div>
            <hr style="margin: 5px 0 5px 0;">
            <strong>• Type:</strong> ${props.soil ?? 'Unknown'}<br>
            <strong>• θS (m³/m³):</strong> ${props.theta_s ?? 'Unknown'}<br>
            <strong>• θR (m³/m³):</strong> ${props.theta_r ?? 'Unknown'}<br>
            <strong>• KsatVer (mm/day):</strong> ${props.k_sat_ver ?? 'Unknown'}<br>
            <strong>• SoilDepth (mm):</strong> ${props.soil_depth ?? 'Unknown'}<br>
            <strong>• Conductivity decay:</strong> ${props.conductivity_decay ?? 'Unknown'}<br>
            <strong>• Brooks-Corey:</strong> ${props.brooks_corey ?? 'Unknown'}<br>
            <hr style="margin: 5px 0 5px 0;">
            <strong>Click to change attributes</strong>
        `;
    } else if (key === 'land') {
        return `
            <div style="font-weight: bold; text-align: center;">ID: ${props._id || 'Unknown'}</div>
            <hr style="margin: 5px 0 5px 0;">
            <strong>• Type:</strong> ${props.land ?? 'Unknown'}<br>
            <strong>• Leaf Area Index (ha):</strong> ${props.LAI ?? 'Unknown'}<br>
            <strong>• Root Depth (m):</strong> ${props.root_depth ?? 'Unknown'}<br>
            <strong>• Interception (mm):</strong> ${props.interception ?? 'Unknown'}<br>
            <strong>• Manning roughness:</strong> ${props.manning_n ?? 'Unknown'}<br>
            <strong>• Albedo:</strong> ${props.albedo ?? 'Unknown'}<br>
            <strong>• Crop coefficient:</strong> ${props.kc ?? 'Unknown'}<br>
            <hr style="margin: 5px 0 5px 0;">
            <strong>Click to change attributes</strong>
        `;
    } else if (key === 'river') {
        return `
            <div style="font-weight: bold; text-align: center;">ID: ${props._id || 'Unknown'}</div>
            <hr style="margin: 5px 0 5px 0;">
            <strong>• Width (m):</strong> ${props.width ?? 'Unknown'}<br>
            <strong>• Depth (m):</strong> ${props.depth ?? 'Unknown'}<br>
            <strong>• Manning roughness:</strong> ${props.manning_n ?? 'Unknown'}<br>
            <hr style="margin: 5px 0 5px 0;">
            <strong>Click to change attributes</strong>
        `;
    }
}

async function mapPlotter(data, map, key) {
    const isRiver = key === 'river';
    const resetStyle = (layer) => {
        const id = layer.feature.properties._id;
        layer.setStyle({  // Reset to default style
            color: 'black', weight: isRiver ? 3 : 1, opacity: 1,
            ...(isRiver ? {} : { fillOpacity: 0.8, fillColor: getColor(id) })
        });
    };
    const layer = L.geoJSON(data, { 
        pointToLayer: () => null,
        style: feature => ({ 
            color: 'black', weight: isRiver ? 3 : 1, opacity: 1,
            ...(isRiver ? {} : { fillOpacity: 0.8, fillColor: getColor(feature.properties._id) }) 
        }),
        onEachFeature: (feature, featureLayer) => { 
            featureLayer.on('click', (e) => { 
                L.DomEvent.stopPropagation(e);
                // Reset the color of all features
                layer.eachLayer(resetStyle);
                // Highlight the clicked feature
                featureLayer.setStyle({ color: 'yellow', weight: isRiver ? 7 : 5 });
                tableAdjust(feature.properties, key);
            });
            featureLayer.bindTooltip(`${buildTooltip(feature.properties, key)}`, {sticky: true});
        }
    }).addTo(map);
    map.on('click', () => { layer.eachLayer(resetStyle); });
    return layer;
}

function tableAdjust(props, key) { 
    if (key === 'soil') {
        soilIds().textContent = '';
        var option = document.createElement('option');
        option.value = props._id; option.textContent = props._id;
        soilIds().appendChild(option);
        const values = [
            props._id, props.soil, props.theta_s, props.theta_r, props.k_sat_ver, 
            props.soil_depth, props.conductivity_decay, props.brooks_corey
        ];
        fillTable([values], soilAttributesTable());
    } else if (key === 'land') {
        landIds().textContent = '';
        var option = document.createElement('option');
        option.value = props._id; option.textContent = props._id;
        landIds().appendChild(option);
        const values = [
            props._id, props.land, props.LAI, props.root_depth, props.interception, 
            props.manning_n, props.albedo, props.kc
        ];
        fillTable([values], landAttributesTable());
    } else if (key === 'river') {
        const values = [props._id, props.width, props.depth, props.manning_n];
        fillTable([values], riverAttributesTable());
    }
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
                    if (title !== "Catchment Import") { tile.style.display = 'none';}
                });
            } else {
                catchmentUploadContainer().style.display = 'none';
                tiles.forEach(tile => {
                    const title = tile.querySelector('h3')?.textContent.trim();
                    if (title !== "Catchment Import") { tile.style.display = 'block';}
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
            const response = await fetch('/geojson_upload', { method: 'POST', body: formData });
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
            soilCheckbox().checked = true;
            soilInvalidCheckerBtn().style.display = 'block'; 
        } catch (error) { 
            alert(`Uploading soil data failed: ${error.message}`); 
            soilInvalidCheckerBtn().style.display = 'none';
            soilCheckbox().checked = false;
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
        if (soilLayer === null) { alert('Please upload/create a soil layer.'); return; }
        if (catchmentLayer === null) { alert('Please upload/create a catchment layer.'); return; }
        const content = { baseLayer: soilLayer.toGeoJSON(), clipLayer: catchmentLayer.toGeoJSON(), getArea: 'inside' };
        startLoading(`Clipping soil layer with catchment layer. Please wait ...`);
        const request = await sendQuery('polygon_clip', content); stopLoading();
        if (request.status === 'error') { alert(request.message); return; }
        if (catchmentLayer) { catchmentLayer.remove(); }; if (landLayer) { landLayer.remove(); }
        if (riverLayer) { riverLayer.remove(); }; soilLayer = clearMap(soilLayer, map);
        soilLayer = await mapPlotter(request.content, map, 'soil');
    });
    assignSoilBtn().addEventListener('click', async () => { 
        if (soilLayer === null) { alert('Please upload/create a soil layer first.'); return; }
        const soilID = soilIds().value;
        if (soilID === '') { alert('Please select a soil polygon first.'); return; }
        const soilType = soilTypes().options[soilTypes().selectedIndex].textContent;
        startLoading('Assigning soil type to selected polygon. Please wait...');
        const response = await sendQuery('assign_type', { data: soilType, key: 'soil' });
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
            landLayer = clearMap(landLayer, map);
            landLayer = await mapPlotter(data.content, map, 'land');
            landInputText().value = file.name; event.target.value = '';
            landCheckbox().checked = true;
            landInvalidCheckerBtn().style.display = 'block';
        } catch (err) {
            alert(`Uploading Land Use/Land Cover data failed. Error: ${err}`);
            landInvalidCheckerBtn().style.display = 'none';
            landCheckbox().checked = false;
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
    landInvalidCheckerBtn().addEventListener('click', () => { 
        if (landLayer === null) { alert('Please upload/create a land cover layer first.'); return; }
        deleteTable(landAttributesTable());
        startLoading('Checking for invalid land cover polygons. Please wait...');
        setTimeout(() => {
            const invalidLand = [], invalidIDs = [];
            landLayer.eachLayer((layer) => {
                // Highlight invalid polygons
                if (layer.feature.properties.soil === '') {
                    layer.setStyle({ color: 'yellow', weight: 3 });
                    const id = layer.feature.properties._id;
                    const values = [
                        id,'Unknown','Unknown','Unknown',
                        'Unknown','Unknown','Unknown','Unknown'
                    ]
                    invalidLand.push(values); invalidIDs.push(id);
                }
            }); stopLoading();
            if (invalidLand.length === 0) { alert('All land cover polygons are valid.'); 
            } else { 
                fillTable(invalidLand, landAttributesTable());
                alert(`Number of invalid land cover polygons: ${invalidLand.length}.`);
                // Add ids to invalid id list
                invalidIDs.forEach((id) => { 
                    var option = document.createElement('option');
                    option.value = id; option.textContent = id;
                    landIds().appendChild(option);
                });
            }
        }, 50);
    });
    landClipBtn().addEventListener('click', async () => { 
        if (landLayer === null) { alert('Please upload/create a land cover layer first.'); return; }
        if (catchmentLayer === null) { alert('Please upload/create a catchment layer first.'); return; }
        const content = { baseLayer: landLayer.toGeoJSON(), clipLayer: catchmentLayer.toGeoJSON(), getArea: 'inside' };
        startLoading(`Clipping land cover layer with catchment layer. Please wait ...`);
        const request = await sendQuery('polygon_clip', content); stopLoading();
        if (request.status === 'error') { alert(request.message); return; }
        if (catchmentLayer) { catchmentLayer.remove(); }; if (soilLayer) { soilLayer.remove(); }
        if (riverLayer) { riverLayer.remove(); }; landLayer = clearMap(landLayer, map);
        landLayer = await mapPlotter(request.content, map, 'land');
    });
    assignLandBtn().addEventListener('click', async () => { 
        if (landLayer === null) { alert('Please upload/create a land cover layer first.'); return; }
        const landID = landIds().value;
        if (landID === '') { alert('Please select a land cover polygon first.'); return; }
        const landType = landTypes().options[landTypes().selectedIndex].textContent;
        startLoading('Assigning land cover type to selected polygon. Please wait...');
        const response = await sendQuery('assign_type', { data: landType, key: 'land' });
        if (response.status === "error") { alert(response.message); return; }
        landLayer.eachLayer((layer) => {
            if (layer.feature.properties._id === Number(landID)) {
                const values = [...response.content];
                layer.feature.properties.land = landType;
                layer.feature.properties.LAI = values[0];
                layer.feature.properties.root_depth = values[1];
                layer.feature.properties.interception = values[2];
                layer.feature.properties.manning_n = values[3];
                layer.feature.properties.albedo = values[4];
                layer.feature.properties.kc = values[5];
                values.unshift(landID);
                fillTable([values], landAttributesTable());
                alert(`Land type "${landType}" assigned to polygon "${landID}".`);
                layer.setStyle({ color: 'green', weight: 3, fillOpacity: 0.8, fillColor: 'green' });
            }
            if (layer.getTooltip()) {
                layer.getTooltip().setContent( buildTooltip(layer.feature.properties, 'land'));
            }
        }); stopLoading();
    });
    saveLandBtn().addEventListener('click', async () => { 
        if (landLayer === null) { alert('Please upload/create a land cover layer first.'); return; }
        await geoJSONExporter(landLayer.toGeoJSON(), 'landcover.geojson');
    });
    document.querySelectorAll('input[name="river"]').forEach((radio) => {
        radio.addEventListener('change', (e) => {
            const value = e.target.value; riverInputText().value = '';
            if (value === 'river-vector') { 
                thresholdLabel().style.display = 'none'; riverThreshold().style.display = 'none';
            } else { thresholdLabel().style.display = 'flex'; riverThreshold().style.display = 'flex'; }
        });
    });
    riverUploadBtn().addEventListener('click', () => { riverInputFile().click(); });
    riverInputFile().addEventListener('change', async (e) => {
        const riverOption = document.querySelector('input[name="river"]:checked').value;
        const threshold = Number(riverThreshold().value);
        if (riverOption === 'river-flow-accumulation' && threshold <= 0) {
            alert('Please select a threshold value greater than 0.'); return; 
        }
        const file = e.target.files[0]; if (!file) return;
        const formData = new FormData(); formData.append('threshold', threshold);
        formData.append('file', file); formData.append('key', riverOption);
        formData.append('projectName', getState().currentProject);
        startLoading('Uploading and processing river data. Please wait...');
        try {
            const response = await fetch('/river_upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.status === 'error') { alert(data.message); return; }
            riverLayer = clearMap(riverLayer, map);
            riverLayer = await mapPlotter(data.content, map, 'river');
            riverInputText().value = file.name; riverCheckbox().checked = true;
        } catch (error) { 
            alert(`Uploading river data failed: ${error.message}`);
            riverInputText().value = ''; riverCheckbox().checked = false;
        }
        e.target.value = ''; stopLoading();
    });
    lakeUploadBtn().addEventListener('click', () => { lakeInputFile().click(); });
    lakeInputFile().addEventListener('change', async (event) => {
        const file = event.target.files[0]; if (!file) return; 
        const formData = new FormData(); formData.append('file', file);
        startLoading('Uploading lake boundary. Please wait...');
        try {
            const response = await fetch('/geojson_upload', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.status === 'error') { alert(data.message); return; }
            lakeLayer = clearMap(lakeLayer, map);
            lakeLayer = L.geoJSON(data.content, { style: { color: 'red', weight: 2, opacity: 1 }}).addTo(map);
        } catch (error) { alert(`Uploading lake boundary failed: ${error.message}`); }
        stopLoading(); event.target.value = '';
    });
    riverLakeClipBtn().addEventListener('click', async () => {
        if (riverLayer === null) { alert('Please upload/create a river layer first.'); return; }
        if (lakeLayer === null) { alert('Please upload a lake boundary.'); return; }
        const content = { baseLayer: riverLayer.toGeoJSON(), clipLayer: lakeLayer.toGeoJSON(), getArea: 'outside' };
        startLoading('Clipping river layer to lake boundary. Please wait...');
        const request = await sendQuery('polygon_clip', content); stopLoading();
        if (request.status === 'error') { alert(request.message); return; }
        if (lakeLayer) { lakeLayer.remove(); }; riverLayer = clearMap(riverLayer, map);
        riverLayer = await mapPlotter(request.content, map, 'river'); riverCheckbox().checked = true;
    });
    riverCatchmentClipBtn().addEventListener('click', async () => {
        if (riverLayer === null) { alert('Please upload/create a river layer first.'); return; }
        if (catchmentLayer === null) { alert('Please upload a catchment boundary.'); return; }
        const content = { baseLayer: riverLayer.toGeoJSON(), clipLayer: catchmentLayer.toGeoJSON(), getArea: 'inside' };
        startLoading('Clipping river layer to catchment boundary. Please wait...');
        const request = await sendQuery('polygon_clip', content); stopLoading();
        if (request.status === 'error') { alert(request.message); return; }
        if (catchmentLayer) { catchmentLayer.remove(); }; riverLayer = clearMap(riverLayer, map);
        riverLayer = await mapPlotter(request.content, map, 'river'); riverCheckbox().checked = true;
    });
    riverDeleteBtn().addEventListener('click', () => {
        if (riverLayer === null) { alert('Please upload/create a river layer first.'); return; }
        const data = getDataFromTable(riverAttributesTable(), true).rows;
        if (data.length === 0) { alert('Please select a segment of the river on map to delete first.'); return; }
        const id = Number(data[0][0]); let selectedID = false;
        riverLayer.eachLayer((layer) => {
            if (Number(layer.feature.properties._id) === id) { layer.remove(); selectedID = true; }
        });
        if (selectedID) { alert(`Segment "${id}" was deleted from the river layer.`); }
        deleteTable(riverAttributesTable());
    });
    riverCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) { 
            if (!riverLayer) { 
                alert('Please upload/create a river layer first.');
                e.target.checked = false; return; 
            } else { riverLayer.addTo(map); }
        } else { riverLayer.remove(); }
    });
    assignRiverBtn().addEventListener('click', async () => { 
        if (riverLayer === null) { alert('Please upload/create a river layer first.'); return; }
        const data = getDataFromTable(riverAttributesTable(), true).rows;
        if (data.length === 0) { alert('Please select a segment of the river on map to edit first.'); return; }
        if (data[0].some(v => !v.trim() || Number.isNaN(Number(v)))) {
            alert('Values in the table must be numeric.'); return;
        }
        riverLayer.eachLayer((layer) => {
            if (layer.feature.properties._id === Number(data[0][0])) {
                layer.feature.properties.width = data[0][1];
                layer.feature.properties.depth = data[0][2];
                layer.feature.properties.manning_n = data[0][3];
                alert(`Attributes were assigned to segment "${data[0][0]}".`);
                layer.setStyle({ color: 'green', weight: 3, fillOpacity: 0.8 });
            }
            if (layer.getTooltip()) {
                layer.getTooltip().setContent( buildTooltip(layer.feature.properties, 'river'));
            }
        });
    });
    saveRiverBtn().addEventListener('click', async () => { 
        if (riverLayer === null) { alert('Please upload/create a river layer first.'); return; }
        await geoJSONExporter(riverLayer.toGeoJSON(), 'river.geojson');
    });
    document.querySelectorAll('input[name="weather"]').forEach(radio => {
        radio.addEventListener('change', (e) => { 
            if (e.target.value === 'weather-csv') { 
                weatherCSVContainer().style.display = 'flex';
                weatherStationContainer().style.display = 'none';
                weatherStationStartContainer().style.display = 'none';
                weatherStationEndContainer().style.display = 'none';
            } else {
                weatherCSVContainer().style.display = 'none';
                weatherStationContainer().style.display = 'flex';
                weatherStationStartContainer().style.display = 'flex';
                weatherStationEndContainer().style.display = 'flex';
            }
        });
    });
    weatherBtn().addEventListener('click', () => { weatherInputFile().click(); });
    weatherInputFile().addEventListener('change', async (e) => {
        startLoading('Uploading weather data from CSV file. Please wait...');
        try { await csvUploader(e, weatherInputText(), weatherAttributesTable(), 8);
        } finally { stopLoading(); }
    });
    weatherStationSelector().addEventListener('change', async(e) => {
        const value = e.target.value; if (!value || value === '') return;
        const start = weatherStart().value, end = weatherEnd().value;
        if (start === '' || end === '') { 
            alert('Please select start and end dates first.');
            e.target.value = ''; return; 
        }
        if (value == 'eklima') {

        } else if (value == 'nmi') {

        } else if (value == 'nve') {

        } else if (value == 'ecmwf') {

        } else if (value == 'power') {

        }
        const content = { start: start, end: end, station: value };
        startLoading('Downloading weather data for selected station. Please wait...');
        const response = await sendQuery('weather_provider', content); stopLoading();
        if (response.status === 'error') { alert(response.message); e.target.value = ''; return; }
        fillTable(response.content, weatherAttributesTable());
    });





    







}

setupTabs(document); update();