import { sendQuery, renderProjects, fillTable } from "./tableManager.js";
import { getState } from "./constants.js";
import { L, CENTER, ZOOM } from "./mapManager.js";
import { getColorFromValue, updateColorbar, nameChecker } from "./utils.js";

const regionList = () => document.getElementById("project-list");
const regionName = () => document.getElementById('project-name');
const loadingGrid = () => document.getElementById('loadingOverlay-grid');
const lakeLabel = () => document.getElementById('lake-name-label');
const lakeSelector = () => document.getElementById('lake-name');
const lakeTable = () => document.getElementById('lake-table');
const lakeSearcher = () => document.getElementById('lake-search');
const sugesstionLake = () => document.getElementById('lake-suggestions');
const tableContent = () => document.getElementById('table-of-contents');
const menuContent = () => document.getElementById('menu-container');
const polygonCheckbox = () => document.getElementById('polygon-checkbox');
const depthCheckbox = () => document.getElementById('depth-checkbox');
const colorbar_container_grid = () => document.getElementById("custom-colorbar-grid");
const colorbar_title_grid = () => document.getElementById("colorbar-title-grid");
const colorbar_color_grid = () => document.getElementById("colorbar-gradient-grid");
const colorbar_label_grid = () => document.getElementById("colorbar-labels-grid");
const vertexesBtn = () => document.getElementById("vertexes-btn");
const refinementCheckbox = () => document.getElementById("refinement-checkbox");
const refinementContainer = () => document.getElementById("refinement-container");
const refinementValue = () => document.getElementById("refinement-value");
const deleteCheckbox = () => document.getElementById("delete-checkbox");
const scaleSelector = () => document.getElementById("scale-factor");
const scaleFactor = () => document.getElementById("custom-scale-factor");
const orthoCheckbox = () => document.getElementById("orthogonalisation-checkbox");
const createGrid = () => document.getElementById('generate-grid');
const gridName = () => document.getElementById('grid-name');
const saveGrid = () => document.getElementById('save-grid');
const hoverTooltip = L.tooltip({
    permanent: false, direction: 'bottom',
    sticky: true, offset: [0, 10], className: 'custom-tooltip'
});

let lakesData = {}, lakeMap = null, lakeLayer = null, pointLayer = null, entireNorway = false, 
    refineChecked = false, deleteChecked = false, dataLake = null, dataDepth = null,
    timeOut = null, levelValue = null, pointContainer = [], html = '',
    baseMap = null, currentTileLayer = null, gridLayer = null, orthoLayer = null;

function startLoading(str = '') {
    loadingGrid().querySelector('.loading-text-grid').textContent = str;
    loadingGrid().style.display = 'flex'; loadingGrid().style.pointerEvents = 'auto';
}
function stopLoading() { 
    loadingGrid().style.display = "none"; loadingGrid().style.pointerEvents = "none";
}
function clearMap(layer) {
    if (layer) { lakeMap.removeLayer(layer); layer = null; }
    return null;
}

async function plotFigure(obj) {
    const tempLayer = L.geoJSON(obj, {
        style: feature => {
            switch (feature.geometry.type) {
                case 'LineString': 
                case 'MultiLineString' || 'MultiPolygon' || 'Polygon':
                    return { color: 'black' };
                default: return {};
            }
        }
    }).addTo(lakeMap);
    return tempLayer;
}

async function loadLakes(){
    startLoading("Initializing Database for entire Norway's Lakes. Please wait...");
    const response = await sendQuery('init_lakes', {projectName: getState().currentProject});
    if (response.status === "error") { alert(response.message); return; }
    stopLoading(); lakesData = response.content; 
    dataLake = lakesData.lake; dataDepth = lakesData.depth;
}

function createLakeMap() {
    if (lakeMap) return;
    const mapDiv = document.getElementById("leaflet-map-lakes");
    if (!mapDiv) { alert("Map container not found"); return; }
    if (lakeMap) { lakeMap.remove(); lakeMap = null; }
    lakeMap = L.map(mapDiv, { center: CENTER, zoom: ZOOM, zoomControl: false, attributionControl: true });
    currentTileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(lakeMap);
    setTimeout(() => { lakeMap.invalidateSize(); }, 0);
    lakeMap.on('mousemove', function (e) { 
        if (refineChecked) {
            if (pointContainer.length === 0) { html = "Select start point to refine"; }
            hoverTooltip.setLatLng(e.latlng).setContent(html);
            lakeMap.openTooltip(hoverTooltip);
        }
        if (deleteChecked) {
            if (pointContainer.length === 0) { html = "Select start point to delete"; }
            hoverTooltip.setLatLng(e.latlng).setContent(html);
            lakeMap.openTooltip(hoverTooltip);
        }
    });
    lakeMap.on('mouseout', function () { lakeMap.closeTooltip(hoverTooltip); });
    lakeMap.on('click', async function () {
        if (refineChecked) {
            if (pointContainer.length === 1) { html = "Select end point to refine"; }
            if (pointContainer.length === 2) { 
                await polygonRefinement(pointContainer); pointContainer = []; 
                html = "Select start point to refine";
                if (hoverTooltip) lakeMap.closeTooltip(hoverTooltip); return; 
            }
        }
        if (deleteChecked) {
            if (pointContainer.length === 1) { html = "Select end point to delete"; }
            if (pointContainer.length === 2) { 
                await pointRemoval(pointContainer); pointContainer = []; 
                html = "Select start point to delete";
                if (hoverTooltip) lakeMap.closeTooltip(hoverTooltip); return; 
            }
        }
    });
}

function resetMap(){
    lakeMap.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) lakeMap.removeLayer(layer); });
    polygonCheckbox().checked = false; depthCheckbox().checked = false;
    refinementCheckbox().checked = false; orthoCheckbox().checked = false; deleteCheckbox().checked = false;
    refineChecked = false; deleteChecked = false;
}

function polygonPlotter(polygon) {
    // Draw lake polygon
    const tempLayer = L.geoJSON(polygon, {
        style: { color: 'blue', weight: 2, fillColor: 'cyan', fillOpacity: 0 },
        // Add tooltips or popups if needed
        onEachFeature: (feature, layer) => {
            if (feature.properties) {
                let tooltip = `
                    <div style="font-weight: bold; text-align: center;">${feature.properties.Name}</div>
                    <hr style="margin: 5px 0 5px 0;">
                    <strong>Region:</strong> ${feature.properties.Region}<br>
                    <strong>Area:</strong> ${feature.properties.area} (m²)<br>
                    <strong>Perimeter:</strong> ${feature.properties.perimeter} (m)
                `;
                if (!entireNorway) {
                    tooltip = tooltip + `<br>
                        <strong>Max. Depth:</strong> ${feature.properties.max} (m)<br>
                        <strong>Min. Depth:</strong> ${feature.properties.min} (m)<br>
                        <strong>Avg. Depth:</strong> ${feature.properties.avg} (m)
                    `;
                }
                layer.bindTooltip(tooltip, {sticky: true});
            }
        }
    }).addTo(lakeMap);
    tempLayer.on('mousemove', () => { 
        if (refineChecked || deleteChecked) { tempLayer.eachLayer(layer => layer.closeTooltip()); } 
    });
    // Fit map to lake bounds
    const bounds = tempLayer.getBounds();
    if (bounds.isValid()) { 
        setTimeout(() => { 
            lakeMap.invalidateSize(); lakeMap.fitBounds(bounds); 
        }, 0);
    }
    return tempLayer;
}

function gridPlotter(polygon, points, colorbarKey='depth') {
    // Make grid points colored by depth
    const lakePolygon = polygon.features[0];
    const cellSize = Math.max(1, Math.floor(lakePolygon.properties.area / 60000));
    colorbar_container_grid().style.display = 'block';
    const grid = turf.squareGrid(turf.bbox(lakePolygon), cellSize, {units: 'meters'});
    grid.features.forEach(cell => {
        const center = turf.center(cell);
        if (!turf.booleanPointInPolygon(center , lakePolygon)) return;
        let num = 0, den = 0;
        points.features.forEach(p => {
            const d = turf.distance(center , p, {units: 'meters'});
            const w = 1 / Math.max(d, 1);
            num += w * p.properties.depth; den += w;
        });
        if (den > 0) { cell.properties.value = num / den; }
    });
    const vmin = lakePolygon.properties.min, vmax = lakePolygon.properties.max;
    const tempGrid = L.geoJSON(grid, {
        filter: f => f.properties.value !== undefined,
        style: f => {
            const value = f.properties.value;
            const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey);
            return { fill: true, fillColor: `rgb(${r},${g},${b})`, 
                fillOpacity: a, weight: 0, opacity: 1, stroke: false };
        }
    }).addTo(lakeMap);
    updateColorbar(vmin, vmax, 'Depth (m)', colorbarKey, colorbar_color_grid(), 
        colorbar_title_grid(), colorbar_label_grid());
    return tempGrid;
}

async function addItems(value) {
    timeOut = setTimeout( async() => {
        const response = await sendQuery('search_lake', {projectName: getState().currentProject, name: value});
        if (response.status === "error") { alert(response.message); return; }
        if (response.content.length === 0) {sugesstionLake().style.display = 'none'; return; }
        sugesstionLake().innerHTML = '';
        response.content.forEach(lake => {
            var div = document.createElement('div');
            div.textContent = lake;
            div.addEventListener('click', () => {
                lakeSearcher().value = lake; regionName().value = '';
                lakeSelector().innerHTML = `<option value="${lake}">${lake}</option>`;
                sugesstionLake().style.display = 'none';
                lakeSelector().dispatchEvent(new Event('change'));
            });
            sugesstionLake().appendChild(div);
        });
        sugesstionLake().style.display = 'block';
    }, 200);
}

function addPointLayer(points) {
    const tempLayer = L.geoJSON(points, {
        pointToLayer: (_, latlng) => {
            return L.circleMarker(latlng, {
                radius: 2, color: 'black', fillColor: 'red', fillOpacity: 1
            });
        },
        onEachFeature: (feature, layer) => {
            layer.on('click', () => { 
                if ((refineChecked || deleteChecked) && 
                    !pointContainer.includes(feature.properties.id)) { 
                    pointContainer.push(feature.properties.id); 
                }
            });
            layer.bindTooltip(`Id: ${feature.properties.id}`, {
                sticky: true, permanent: false, direction: 'center', opacity: 1
            });
        }
    }).addTo(lakeMap);
    return tempLayer;
}

async function polygonRefinement(pointIds) {
    // Sort pointIds
    pointIds.sort((a, b) => a - b);
    const refineValue = Number(refinementValue().value); gridLayer = clearMap(gridLayer);
    if (!Number.isFinite(refineValue) || refineValue <= 0) { alert("Please enter a valid non-negative value."); return; }
    if (pointLayer === null) { alert("No polygon has been found. Select the button 'Get/Reset Vertexes' to draw the original polygon."); return; }
    const pointCollection = [];
    pointLayer.eachLayer(layer => {
        const latlng = layer.getLatLng();
        pointCollection.push([latlng.lat, latlng.lng]);
    });
    if (pointCollection.length < 2) { alert("No point has been found. Select the button 'Get/Reset Vertexes' to create vertexes."); return; }
    startLoading('Refining Vertexes. Please wait...');
    const contents = {
        projectName: getState().currentProject, distance: refineValue, polygon: pointCollection,
        startPoint: pointIds[0], endPoint: pointIds[pointIds.length - 1]
    }
    const response = await sendQuery('vertex_refiner', contents); stopLoading();
    if (response.status === "error") { alert(response.message);  return; }
    const polygon = response.content.polygon, point = response.content.point;
    dataLake = polygon;
    if (!polygonCheckbox().checked) { polygonCheckbox().checked = true; }
    lakeMap.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) lakeMap.removeLayer(layer); });
    pointLayer = clearMap(pointLayer); pointLayer = addPointLayer(point);
    orthoCheckbox().checked = false; orthoCheckbox().dispatchEvent(new Event('change'));
    refineChecked = false; refinementCheckbox().checked = false;
    refinementCheckbox().dispatchEvent(new Event('change'));
}

async function pointRemoval(pointIds) {
    pointIds.sort((a, b) => a - b);
    if (pointLayer === null) { alert("No polygon has been found. Select the button 'Get/Reset Vertexes' to draw the original polygon."); return; }
    const pointCollection = []; deleteChecked = true;
    pointLayer.eachLayer(layer => {
        const latlng = layer.getLatLng();
        pointCollection.push([latlng.lat, latlng.lng]);
    });
    if (pointCollection.length < 2) { alert("No point has been found. Select the button 'Get/Reset Vertexes' to draw the original polygon."); return; }
    startLoading('Deleting Vertexes. Please wait...');
    const contents = {
        projectName: getState().currentProject, polygon: pointCollection,
        startPoint: pointIds[0], endPoint: pointIds[pointIds.length - 1]
    }
    await new Promise(resolve => setTimeout(resolve, 0));
    const response = await sendQuery('vertex_remover', contents); stopLoading();
    if (response.status === "error") { alert(response.message); return; }
    const polygon = response.content.polygon, point = response.content.point;
    lakeMap.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) lakeMap.removeLayer(layer); });
    lakeLayer = plotFigure(polygon); pointLayer = addPointLayer(point);
    orthoCheckbox().checked = false; orthoCheckbox().dispatchEvent(new Event('change'));
    deleteChecked = false; deleteCheckbox().checked = false;
    deleteCheckbox().dispatchEvent(new Event('change'));
}

async function initializeProject(){
    // Update region name
    regionName().addEventListener('click', async () => {
        sugesstionLake().style.display = "none"; lakeSearcher().value = "";
        if (regionName().value.trim() === "") { 
            lakeLabel().style.display = "none"; lakeSelector().style.display = "none"; 
        }
        if (Object.keys(lakesData).length === 0) { await loadLakes(); }
        regionList().innerHTML = '';
        // Add "All regions" option
        const allLi = document.createElement("li");
        allLi.textContent = "All regions"; allLi.style.fontWeight = "bold";
        allLi.dataset.value = "All regions"; allLi.style.fontSize = "14px";
        allLi.addEventListener('mousedown', () => {
            regionName().value = allLi.dataset.value;
            regionList().style.display = "none"; 
            lakeLabel().style.display = "none";
            lakeSelector().style.display = "none";
            regionName().dispatchEvent(new Event('change'));
        });
        regionList().appendChild(allLi);
        const allLi1 = document.createElement("hr");
        allLi1.style.margin = "5px 10px 5px 10px"; allLi1.style.borderTop = "1px solid #0414f5";
        regionList().appendChild(allLi1);
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
            lakeLayer = clearMap(lakeLayer); lakeSelector().value = ""; regionName().value = "";
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

async function dataPreparationManager(){
    baseMap = document.getElementById("base-map-select");
    if (!lakeMap) { createLakeMap(); }; lakeLayer = clearMap(lakeLayer);
    regionName().addEventListener('change', async () => {
        const selectedLake = regionName().value.trim(); entireNorway = false;
        if (!selectedLake || selectedLake === "") { return; }
        if (selectedLake === "All regions" ) {
            startLoading('Loading Lakes for entire Norway. Please wait...'); entireNorway = true;
            const response = await sendQuery('load_lakes', { projectName: getState().currentProject, lakeName: 'all' }); stopLoading();
            if (response.status === "error") { alert(response.message);  return; }
            tableContent().style.display = "none"; menuContent().style.display = "none";
            colorbar_container_grid().style.display = 'none'; lakeSelector().style.display = "none";
            dataLake = response.content.lake; dataDepth = response.content.depth;
            lakeLayer = clearMap(lakeLayer); lakeLayer = polygonPlotter(dataLake);
            return;
        }
        lakeSelector().innerHTML = lakesData[selectedLake].map(name => `<option value="${name}">${name}</option>`).join('');
        lakeSelector().value = lakesData[selectedLake][0]; lakeSelector().dispatchEvent(new Event('change'));
    });
    lakeSelector().addEventListener('change', async () => {
        const lakeName = lakeSelector().value; if (!lakeName) return;
        gridLayer = clearMap(gridLayer); lakeLayer = clearMap(lakeLayer);
        pointLayer = clearMap(pointLayer); orthoLayer = clearMap(orthoLayer);
        startLoading(`Loading data for lake: ${lakeName}`);
        const response = await sendQuery('load_lakes', { projectName: getState().currentProject, lakeName: lakeName }); stopLoading();
        if (response.status === "error") { alert(response.message); return; }
        dataLake = response.content.lake; dataDepth = response.content.depth;
        createLakeMap(); const data = dataLake.features[0].properties;
        const contents = [[data.Name, data.Region, data.area, data.perimeter, data.min, data.max, data.avg]];
        tableContent().style.display = "block"; menuContent().style.display = "flex";
        fillTable(contents, lakeTable(), true); lakeSelector().style.display = 'flex';
        depthCheckbox().checked = true; polygonCheckbox().checked = true; orthoCheckbox().checked = false;
        // Plot lake and depth on map
        window.depthGridLayer = clearMap(window.depthGridLayer);
        window.depthGridLayer = gridPlotter(dataLake, dataDepth);
        lakeLayer = clearMap(lakeLayer); lakeLayer = polygonPlotter(dataLake);
    });
    // Search lake
    lakeSearcher().addEventListener('click', (e) => { 
        addItems(e.target.value.trim()); regionList().style.display = "none";
        lakeSelector().style.display = 'none'; regionName().value = ''; resetMap();
    });
    lakeSearcher().addEventListener('input', (e) => {
        clearTimeout(timeOut); addItems(e.target.value.trim()); regionName().value = '';
        regionList().style.display = "none"; lakeSelector().style.display = 'none'; resetMap();
    });
    document.addEventListener('click', (e) => { 
        const input = lakeSearcher(), suggestion = sugesstionLake();
        if (!input.contains(e.target) && !suggestion.contains(e.target)) {
            suggestion.style.display = "none";
        }
    });
    polygonCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) { 
            if (lakeLayer === null) { lakeLayer = polygonPlotter(dataLake); }
        } else { lakeLayer = clearMap(lakeLayer); }
    });
    depthCheckbox().addEventListener('change', async (e) => {
        if (e.target.checked) { 
            if (window.depthGridLayer === null) {
                startLoading('Plotting depth grid. Please wait...');
                await new Promise(resolve => setTimeout(resolve, 0));
                window.depthGridLayer = gridPlotter(dataLake, dataDepth);
                stopLoading();
            }
        } else {
            window.depthGridLayer = clearMap(window.depthGridLayer);
            colorbar_container_grid().style.display = 'none';
        }
    });
    baseMap.addEventListener('change', () => {
        const url = baseMap.value.trim(); currentTileLayer = clearMap(currentTileLayer);
        currentTileLayer = L.tileLayer(url, {zIndex: 0});
        currentTileLayer.addTo(lakeMap);
        setTimeout(() => { lakeMap.invalidateSize(); }, 0);
    });
    vertexesBtn().addEventListener('click', async () => {
        gridLayer = clearMap(gridLayer); lakeLayer = clearMap(lakeLayer);
        colorbar_container_grid().style.display = 'none';
        startLoading('Generating Vertexes. Please wait...');
        await new Promise(resolve => setTimeout(resolve, 0));
        const response = await sendQuery('vertex_generator', { projectName: getState().currentProject }); stopLoading();
        if (response.status === "error") { alert(response.message); return; }
        pointLayer = clearMap(pointLayer); pointLayer = addPointLayer(response.content);
        if (!polygonCheckbox().checked) { polygonCheckbox().checked = true; }
        polygonCheckbox().dispatchEvent(new Event('change'));
        orthoCheckbox().checked = false; orthoCheckbox().dispatchEvent(new Event('change'));
        refineChecked = false; refinementCheckbox().checked = false;
        refinementCheckbox().dispatchEvent(new Event('change'));
        depthCheckbox().checked = false; depthCheckbox().dispatchEvent(new Event('change'));
    });
    refinementCheckbox().addEventListener('change', (e) => {
        if (e.target.checked) { 
            if (pointLayer === null) { 
                alert("Select the button 'Get/Reset Vertexes' to create vertexes.");
                e.target.checked = false; return;
            }
            refineChecked = true; depthCheckbox().checked = false;
            depthCheckbox().dispatchEvent(new Event('change'));
            orthoLayer = clearMap(orthoLayer); deleteChecked = false;
            orthoCheckbox().checked = false; orthoCheckbox().dispatchEvent(new Event('change'));
            pointContainer = []; gridLayer = clearMap(gridLayer);
            refinementContainer().style.display = 'flex';
            deleteChecked = false; deleteCheckbox().checked = false;
            deleteCheckbox().dispatchEvent(new Event('change'));
        } else { refinementContainer().style.display = 'none'; refineChecked = false; }
    });
    deleteCheckbox().addEventListener('change', async (e) => {
        if (!e.target.checked) { deleteChecked = false; return; }
        if (pointLayer === null) { 
            alert("Select the button 'Get/Reset Vertexes' to create vertexes.");
            e.target.checked = false; return;
        }
        pointContainer = []; gridLayer = clearMap(gridLayer); deleteChecked = true; 
        orthoCheckbox().checked = false; orthoCheckbox().dispatchEvent(new Event('change'));
        refineChecked = false; refinementCheckbox().checked = false;
        refinementCheckbox().dispatchEvent(new Event('change'));
    });
    scaleSelector().addEventListener('change', (e) => {
        const value = e.target.value;
        if (value === "auto") { scaleFactor().style.display = "none"; }
        else { scaleFactor().style.display = "flex"; }
    });
    scaleFactor().addEventListener('input', (e) => { 
        const value = e.target.value;
        if (value === "" || !Number.isFinite(Number(value)) || Number(value) <= 0) { e.target.value = '1.0'; return; }
    });
    createGrid().addEventListener('click', async () => {
        if (pointLayer === null) { alert("Please generate vertexes first."); return; }
        const levelSelector = scaleSelector().value, pointCollection = [];
        if (levelSelector === "auto") { levelValue = ''; } else { levelValue = Number(scaleFactor().value); }
        pointLayer.eachLayer(layer => {
            const latlng = layer.getLatLng();
            pointCollection.push([latlng.lat, latlng.lng]);
        });
        if (pointCollection.length === 0) { alert("No vertexes found."); return; }
        pointCollection.push(pointCollection[0]);
        startLoading('Generating an Unstructured Grid. Please wait...');
        await new Promise(resolve => setTimeout(resolve, 0));
        const contents = { projectName: getState().currentProject, pointCollection: pointCollection, levelValue: levelValue }
        const response = await sendQuery('grid_creator', contents); stopLoading();
        if (response.status === "error") { alert(response.message); return; }
        gridLayer = clearMap(gridLayer); orthoLayer = clearMap(orthoLayer);
        depthCheckbox().checked = false; depthCheckbox().dispatchEvent(new Event('change'));
        orthoCheckbox().checked = false; orthoCheckbox().dispatchEvent(new Event('change'));
        gridLayer = L.geoJSON(response.content, {
            style: feature => {
                switch (feature.geometry.type) {
                    case 'LineString': 
                    case 'MultiLineString': return { color: 'black', weight: 0.5 };
                    case 'Polygon':
                    case 'MultiPolygon':
                        return { color: 'black', fillColor: 'darkcyan', fillOpacity: 0.5, weight: 0.5 };
                    default: return {};
                }
            }
        }).addTo(lakeMap);
        refineChecked = false; refinementCheckbox().checked = false;
        refinementCheckbox().dispatchEvent(new Event('change'));
    });
    orthoCheckbox().addEventListener('change', async (e) => {
        if (e.target.checked) { 
            if (gridLayer === null) { 
                alert("Please generate grid first."); 
                orthoCheckbox().checked = false; return; 
            }
            startLoading('Generating Orthogonalization. Please wait...');
            await new Promise(resolve => setTimeout(resolve, 0));
            const contents = { projectName: getState().currentProject };
            const response = await sendQuery('grid_ortho', contents); stopLoading();
            if (response.status === "error") { alert(response.message); return; }
            window.depthGridLayer = clearMap(window.depthGridLayer);
            orthoLayer = clearMap(orthoLayer); depthCheckbox().checked = false;
            const vmin = response.content.min, vmax = response.content.max, colorKey = 'ortho';
            orthoLayer = L.geoJSON(response.content.data, {
                pointToLayer: (feature, latlng) => {
                    const value = Number(feature.properties.orth);
                    const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorKey);
                    const col = `rgb(${r},${g},${b})`;
                    return L.circleMarker(latlng, {
                        color: col, fillColor: col, radius: 2, fillOpacity: a
                    });
                },
                onEachFeature: (feature, layer) => {
                    layer.bindTooltip(`Orthogonalization: ${feature.properties.orth}`, {
                        sticky: true, permanent: false, direction: 'center', opacity: 1
                    });
                }
            }).addTo(lakeMap);
            updateColorbar(vmin, vmax, 'Orthogonalization', colorKey, colorbar_color_grid(), 
                colorbar_title_grid(), colorbar_label_grid());
            colorbar_container_grid().style.display = 'block';
        } else { 
            orthoLayer = clearMap(orthoLayer);
            if (!depthCheckbox().checked) { colorbar_container_grid().style.display = 'none'; } 
        }
    });
    saveGrid().addEventListener('click', async() => {
        if (gridLayer === null) { alert("Please generate unstructured grid first."); return; }
        let name = gridName().value.trim();
        if (name === "") { alert("Please enter a name."); return; }
        if (nameChecker(name)) { alert('Grid name contains invalid characters.'); return; }
        if (!name.toLowerCase().endsWith('.nc')) { name = name + '.nc'; }
        startLoading('Checking grid existence. Please wait...');
        await new Promise(resolve => setTimeout(resolve, 0));
        const contents = { projectName: getState().currentProject, gridName: name };
        const check = await sendQuery('grid_checker', contents); stopLoading();
        if (check.status === "error") { 
            if (!confirm(`File "${name}" already exists. Do you want to overwrite it?`)) { return; }
        }
        startLoading('Saving grid. Please wait...');
        const response = await sendQuery('grid_saver', contents);
        stopLoading(); alert(response.message);
    });
    baseMap.dispatchEvent(new Event('change'));
}

await loadLakes(); await initializeProject(); dataPreparationManager();