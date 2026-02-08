import { sendQuery, renderProjects, fillTable } from "./tableManager.js";
import { getState } from "./constants.js";
import { L, CENTER, ZOOM } from "./mapManager.js";
import { getColorFromValue, updateColorbar } from "./utils.js";

const regionList = () => document.getElementById("project-list");
const regionName = () => document.getElementById('project-name');
const lakeLabel = () => document.getElementById('lake-name-label');
const lakeSelector = () => document.getElementById('lake-name');
const lakeTable = () => document.getElementById('lake-table');
const tableContent = () => document.getElementById('table-of-contents');
const boundaryCheckbox = () => document.getElementById('boundary-checkbox');
const depthCheckbox = () => document.getElementById('depth-checkbox');
const colorbar_container_grid = () => document.getElementById("custom-colorbar-grid");
const colorbar_title_grid = () => document.getElementById("colorbar-title-grid");
const colorbar_color_grid = () => document.getElementById("colorbar-gradient-grid");
const colorbar_label_grid = () => document.getElementById("colorbar-labels-grid");



const createGrid = () => document.getElementById('generate-grid');
const saveGrid = () => document.getElementById('save-grid');


let lakesData = {}, lakeMap = null, lakeLayer = null, dataLake = null,
    allLakesChecked = false, gridLayer = null, baseMap = null, currentTileLayer = null;
async function loadLakes(){
    window.parent.postMessage({type: 'showOverlay', 
        message: 'Initializing Lakes Database for entire Norway. Please wait...'}, '*');
    const response = await sendQuery('init_lakes', {projectName: getState().currentProject});
    lakesData = response.status !== "error" ? response.content : {};
    window.parent.postMessage({type: 'hideOverlay'}, '*');
}

function createLakeMap() {
    if (lakeMap) return;
    const mapDiv = document.getElementById("leaflet_map_lakes");
    if (!mapDiv) { console.error("Map container not found"); return; }
    if (lakeMap) { lakeMap.remove(); lakeMap = null; }
    lakeMap = L.map(mapDiv, { center: CENTER, zoom: ZOOM, zoomControl: false, attributionControl: true });
    currentTileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(lakeMap);
    setTimeout(() => { lakeMap.invalidateSize(); }, 0);
}

async function initializeProject(){
    // Update region name
    regionName().addEventListener('click', async () => {
        if (regionName().value.trim() === "") { lakeLabel().style.display = "none"; lakeSelector().style.display = "none"; }
        if (Object.keys(lakesData).length === 0) { await loadLakes(); }
        regionList().innerHTML = '';
        // Add "All regions" option
        const allLi = document.createElement("li");
        allLi.textContent = "All regions";
        allLi.dataset.value = "All regions";
        allLi.addEventListener('mousedown', () => {
            regionName().value = allLi.dataset.value;
            regionList().style.display = "none"; 
            lakeLabel().style.display = "none";
            lakeSelector().style.display = "none";
            regionName().dispatchEvent(new Event('change'));
        });
        regionList().appendChild(allLi);
        Object.keys(lakesData).forEach(p => {
            const li = document.createElement("li");
            li.textContent = p;
            li.addEventListener('mousedown', () => {
                regionName().value = p; regionList().style.display = "none";
                lakeLabel().style.display = "block"; lakeSelector().style.display = "block";
                regionName().dispatchEvent(new Event('change'));
            });
            regionList().appendChild(li);
        })
        regionList().style.display = "block"; 
    });
    regionName().addEventListener('input', (e) => { 
        const value = e.target.value.trim();
        if (value !== "") { renderProjects(regionList(), regionName(), Object.keys(lakesData), value); }
        else { 
            lakeMap.removeLayer(lakeLayer); lakeLayer = null;
            lakeSelector().value = ""; regionName().value = "";
            lakeLabel().style.display = "none"; lakeSelector().style.display = "none";
            regionName().dispatchEvent(new Event('change'));
        }
    });
    regionName().addEventListener('blur', () => { 
        setTimeout(() => { regionList().style.display = "none"; }, 100);
        if (regionName().value.trim() === "") { 
            lakeLabel().style.display = "none"; lakeSelector().style.display = "none";
        }
    });
}

function gridPlotter(polygon, points, cellSize, colorbarKey='depth') {
    colorbar_container_grid().style.display = 'block';
    if (window.depthGridLayer) { lakeMap.removeLayer(window.depthGridLayer); window.depthGridLayer = null; }
    const grid = turf.squareGrid(turf.bbox(polygon), cellSize, {units: 'meters'}), values = [];
    grid.features.forEach(cell => {
        const center = turf.center(cell);
        if (!turf.booleanPointInPolygon(center , polygon)) return;
        let num = 0, den = 0;
        points.features.forEach(p => {
            const d = turf.distance(center , p, {units: 'meters'});
            const w = 1 / Math.max(d, 1);
            num += w * p.properties.depth; den += w;
        });
        if (den > 0) { cell.properties.value = num / den; values.push(num / den); }
    });
    const vmin = Math.min(...values), vmax = Math.max(...values);
    window.depthGridLayer = L.geoJSON(grid, {
        filter: f => f.properties.value !== undefined,
        style: f => {
            const value = f.properties.value;
            const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey);
            return { fill: true, fillColor: `rgb(${r},${g},${b})`, 
                fillOpacity: a, weight: 0, opacity: 1, stroke: false };
        }
    }).addTo(lakeMap);
    updateColorbar(vmin, vmax, 'Depth (m)', colorbarKey, colorbar_color_grid(), colorbar_title_grid(), colorbar_label_grid());
}

function geoJSONPlotter(data, checker) {
    if (lakeLayer) { lakeMap.removeLayer(lakeLayer); lakeLayer = null; }
    // Make grid points colored by depth
    if (checker) {
        const depth = data.depth, lakePolygon = data.lake.features[0]
        const cellSize = Math.max(1, Math.floor(lakePolygon.properties.area / 60000));
        gridPlotter(lakePolygon, depth, cellSize);
    }
    // Draw lake boundary
    lakeLayer = L.geoJSON(data.lake, {
        style: { color: 'blue', weight: 2, fillColor: 'cyan', fillOpacity: 0 },
        // Add tooltips or popups if needed
        onEachFeature: (feature, layer) => {
            if (feature.properties) {
                const tooltip = `
                    <div style="font-weight: bold; text-align: center;">${feature.properties.Name}</div>
                    <hr style="margin: 5px 0 5px 0;">
                    <strong>Region:</strong> ${feature.properties.Region}<br>
                    <strong>Area (m²):</strong> ${feature.properties.area}<br>
                    <strong>Max Depth (m):</strong> ${feature.properties.max}<br>
                    <strong>Min Depth (m):</strong> ${feature.properties.min}<br>
                    <strong>Avg Depth (m):</strong> ${feature.properties.avg}
                `;
                layer.bindTooltip(tooltip, {sticky: true});
            }
        }
    }).addTo(lakeMap);
    // Fit map to lake bounds
    const bounds = lakeLayer.getBounds();
    if (bounds.isValid()) { lakeMap.fitBounds(bounds); }
    return lakeLayer;
}

async function dataPreparationManager(){
    baseMap = document.getElementById("base-map-select");
    if (!lakeMap) { createLakeMap(); }
    regionName().addEventListener('change', async () => {
        const selectedLake = regionName().value.trim(); if (!selectedLake) return;
        if (selectedLake === "All regions" ) {
            window.parent.postMessage({type: 'showOverlay', message: 'Getting Lakes for entire Norway. Please wait...'}, '*');
            const response = await sendQuery('load_lakes', { projectName: getState().currentProject, lakeName: 'all' });
            window.parent.postMessage({type: 'hideOverlay'}, '*');
            if (response.status === "error") { alert(response.message);  return; }
            tableContent().style.display = "none"; dataLake = response.content;
            depthCheckbox().checked = false; boundaryCheckbox().checked = true; allLakesChecked = false;
            lakeLayer = geoJSONPlotter(response.content, allLakesChecked); return;
        }
        lakeSelector().innerHTML = lakesData[selectedLake].map(name => `<option value="${name}">${name}</option>`).join('');
        lakeSelector().value = lakesData[selectedLake][0]; lakeSelector().dispatchEvent(new Event('change'));
    });
    lakeSelector().addEventListener('change', async () => {
        const lakeName = lakeSelector().value; if (!lakeName) return;
        window.parent.postMessage({type: 'showOverlay', message: `Loading data for lake: ${lakeName}`}, '*');
        const response = await sendQuery('load_lakes', { projectName: getState().currentProject, lakeName: lakeName });
        window.parent.postMessage({type: 'hideOverlay'}, '*');
        if (response.status === "error") { alert(response.message);  return; }
        createLakeMap(); const data = response.content.lake.features[0].properties;
        const contents = [[data.Name, data.Region, data.area, data.min, data.max, data.avg]];
        fillTable(contents, lakeTable(), true); tableContent().style.display = "block";
        depthCheckbox().checked = true; boundaryCheckbox().checked = true; 
        allLakesChecked = true; dataLake = response.content;
        // Plot lake on map
        lakeLayer = geoJSONPlotter(response.content, allLakesChecked);
    });
    boundaryCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) { if (lakeLayer) { lakeMap.addLayer(lakeLayer); }
        } else { if (lakeLayer) { lakeMap.removeLayer(lakeLayer); } }
    });
    depthCheckbox().addEventListener('change', (e) => {
        if (!allLakesChecked) { 
            alert("This option is only available for an individual lake."); 
            colorbar_container_grid().style.display = 'none'; e.target.checked = false; return;
        }
        if (e.target.checked) { 
            const depth = dataLake.depth, lakePolygon = dataLake.lake.features[0];
            const cellSize = Math.max(1, Math.floor(lakePolygon.properties.area / 60000));
            gridPlotter(lakePolygon, depth, cellSize);
        } else {
            if (window.depthGridLayer) { 
                lakeMap.removeLayer(window.depthGridLayer); window.depthGridLayer = null; 
            };
            colorbar_container_grid().style.display = 'none';
        }
    });
    baseMap.addEventListener('change', () => {
        const url = baseMap.value.trim();
        if (currentTileLayer) lakeMap.removeLayer(currentTileLayer);
        currentTileLayer = L.tileLayer(url, {zIndex: 0});
        currentTileLayer.addTo(lakeMap);
        setTimeout(() => { lakeMap.invalidateSize(); }, 0);
    });
    createGrid().addEventListener('click', async () => {
        if (gridLayer) { lakeMap.removeLayer(gridLayer); gridLayer = null; }
        const response = await sendQuery('grid_creator', {});
        if (response.status === "error") { alert(response.message); return; }
        gridLayer = geoJSONPlotter(response.content, false);
        // const projectName = getState().currentProject;
        // const regionName = regionName().value.trim();
        // const lakeName = lakeSelector().value.trim();
        // window.parent.postMessage({type: 'createGrid', projectName, regionName, lakeName}, '*');
    });

    saveGrid().addEventListener('click', () => {
        // const projectName = getState().currentProject;
        // const regionName = regionName().value.trim();
        // const lakeName = lakeSelector().value.trim();
        // window.parent.postMessage({type: 'plotMap', projectName, regionName, lakeName}, '*');
    });
    baseMap.dispatchEvent(new Event('change'));
}

await loadLakes(); await initializeProject(); dataPreparationManager(); 
