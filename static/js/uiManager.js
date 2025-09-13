// Import necessary functions
import { initializeMap, baseMapButtonFunctionality } from './mapManager.js';
import { startLoading, showLeafletMap, map } from './mapManager.js';
import { plotChart, plotEvents, drawChart } from './chartManager.js';
import { plot2DMapStatic } from "./map2DManager.js";
import { deactivePointQuery, deactivePathQuery } from "./queryManager.js";
import { generalObtionsManager } from './generalOptionManager.js';
import { dynamicMapManager } from './dynamicMapManager.js';
import { getProject, setProject } from './constants.js';
import { sendQuery } from './tableManager.js';


let isNewProject = false, oldProject = '', newProject = null, gridLayer = null;
let pickerState = { location: false, point: false, crosssection: false, boundary: false, source: false };
let markersPoints = [], hoverTooltip, markersBoundary = [], boundaryContainer = [], pathLineBoundary = null;
let markersCrosssection = [], crosssectionContainer = [], pathLineCrosssection = null;

const popupMenu = () => document.getElementById('popup-menu');
const popupContent = () => document.getElementById('popup-content');
const contactInfo = () => document.getElementById('informationContact');
const contactInfoHeader = () => document.getElementById('informationContactHeader');
const contactInfoContent = () => document.getElementById('informationContactContent');
const contactInfoCloseBtn = () => document.getElementById('closeInformationContact');
const projectTitle = () => document.getElementById('projectTitle');
const projectSetting = () => document.getElementById('projectWindow');
const projectSettingHeader = () => document.getElementById('projectWindowHeader');
const projectSettingContent = () => document.getElementById('projectWindowContent');
const projectSettingCloseBtn = () => document.getElementById('closeProjectWindow');
const simulationWindow = () => document.getElementById('simulationWindow');
const simulationHeader = () => document.getElementById('simulationWindowHeader');
const simulationContent = () => document.getElementById('simulationWindowContent');
const simulationCloseBtn = () => document.getElementById('closeSimulationWindow');
const mapContainer = () => map.getContainer();

initializeMap();
baseMapButtonFunctionality();
projectChecker();
initializeMenu();
updateEvents();
plotEvents();


// ============================ Functions ============================

async function showPopupMenu(id, htmlFile) {
    try {
        const response = await fetch(`/load_popupMenu?htmlFile=${htmlFile}`);
        const html = await response.text();
        popupContent().innerHTML = html;
        if (id === '1') generalObtionsManager('summary.json', 'stations.geojson', 'sources.geojson', 'crosssections.geojson'); // Events on general options submenu
        if (id === '2') measuredPointManager(); // Events on measured points submenu
        if (id === '3') dynamicMapManager(); // Events on dynamic map submenu
        if (id === '4') staticMapManager(); // Events on static map submenu
    } catch (error) {alert(error + ' ' + htmlFile);}
}

async function projectChecker() {
    const projectMenu = document.querySelectorAll('.menu');
    projectMenu.forEach(menu => {
        menu.style.display = (getProject()===null)?'none':'block';
    });
    const project = document.querySelector('.menu[data-info="0|project_menu.html"]');
    project.style.display = 'block';
    if (getProject() !== null) newProject = getProject();
    if (isNewProject === false) {setProject(null);};
    if (isNewProject === false && newProject === null) return;
    projectTitle().textContent = `Project: ${newProject.project}`;
    startLoading('Reading Simulation Outputs and Setting up Database.\nThis takes for a while. Please wait...');
    const data = await sendQuery('setup_database', {projectName: newProject.project, files: newProject.values});
    if (data.status === "error") alert(data.message);
    showLeafletMap();
}

async function initializeMenu(){
    // Work with pupup menu
    document.querySelectorAll('.nav ul li a').forEach(link => {
        link.addEventListener('click', async(event) => {
            event.stopPropagation(); event.preventDefault();
            const rect = link.getBoundingClientRect();
            const pm = popupMenu();
            if (pm.classList.contains('show')) {
                pm.classList.remove('show');
            }
            const info = link.dataset.info;
            if (info === 'home') { history.back(); return; }
            if (info === 'help') { contacInformation(); return;}
            const [id, htmlFile] = info.split('|');
            startLoading('Getting Information. Please wait...');
            await showPopupMenu(id, htmlFile);
            showLeafletMap();
            pm.style.top = `${rect.bottom + 15 + window.scrollY}px`;
            pm.style.left = `${rect.left + window.scrollX}px`;
            pm.classList.add('show');
        });
    })
}

function moveWindow(window, header){
    let dragging = false;
    let offsetX = 0, offsetY = 0;
    header().addEventListener("mousedown", function(e) {
        dragging = true;
        offsetX = e.clientX - window().offsetLeft;
        offsetY = e.clientY - window().offsetTop;
        e.preventDefault();
    });
    header().addEventListener("mouseup", function() { dragging = false; });
    document.addEventListener("mousemove", function(e) {
        if (dragging) {
            window().style.left = (e.clientX - offsetX) + "px";
            window().style.top = (e.clientY - offsetY) + "px";
        }
    });
}

function iframeInit(scr, objWindow, objHeader, objContent, title){
    // Detect iframe if exist
    const iframe = objContent.querySelector("iframe");
    if (iframe) iframe.remove();
    // Add iframe
    const newIframe = document.createElement("iframe");
    newIframe.src = `/${scr}`;
    objContent.appendChild(newIframe);
    objHeader.childNodes[0].nodeValue = title;
    objWindow.style.display = 'flex';
}

function updateEvents() {
    // Check if events are already bound
    if (window.__menuEventsBound) return;
    window.__menuEventsBound = true;
    const pm = popupMenu();
    if (pm){
        pm.addEventListener('mouseenter', () => pm.classList.add('show'));
        pm.addEventListener('mouseleave', () => pm.classList.remove('show'));
    }
    document.addEventListener('click', (e) => {
        // Close the popup menu if clicked outside
        if (pm && !pm.contains(e.target)) pm.classList.remove('show');
        // Toogle the menu if click on menu-link
        const link = e.target.closest('.menu-link');
        if (link){
            e.preventDefault(); e.stopPropagation();
            const submenu = link.nextElementSibling;
            if (submenu && submenu.classList.contains('submenu')){
                // Close other submenus and remove active on menu-links
                document.querySelectorAll('.submenu.open').forEach(s => {
                    if (s !== submenu) s.classList.remove('open');
                });
                document.querySelectorAll('.menu-link.active').forEach(l => {
                    if (l !== link) l.classList.remove('active');
                });
                // Toggle class open
                submenu.classList.toggle('open');
                link.classList.toggle('active');
            }
            return;
        }
        const link1 = e.target.closest('.menu-link-1');
        if (link1){
            e.preventDefault(); e.stopPropagation();
            const submenu1 = link1.nextElementSibling;
            if (submenu1 && submenu1.classList.contains('submenu-1')){
                // Close other submenus and remove active on menu-links
                document.querySelectorAll('.submenu-1.open').forEach(s => {
                    if (s !== submenu1) s.classList.remove('open');
                });
                document.querySelectorAll('.menu-link-1.active').forEach(l => {
                    if (l !== link1) l.classList.remove('active');
                });
                // Toggle class open
                submenu1.classList.toggle('open');
                link1.classList.toggle('active');
            }
            return;
        }
    });
    // Select project
    popupContent().addEventListener('click', (e) => {
        const project = e.target.closest('.project');
        if (project) {
            const name = project.dataset.info;
            // isNewProject = false;
            if (name === 'reset-project') {
                setProject(null); location.reload();
            } else if (name === 'default-project') { 
                const params = ["FlowFM_his.nc", "FlowFM_map.nc",
                    "deltashell_his.nc", "deltashell_map.nc"];
                setProject({ project: 'Demo_Project', values: params });
                projectChecker();
            } else if (name === 'open-project') {
                iframeInit("open_project", projectSetting(), projectSettingHeader(), 
                    projectSettingContent(), "Open Project"); isNewProject = false;
            } else if (name === 'new-project') { 
                iframeInit("new_project", projectSetting(), projectSettingHeader(), 
                    projectSettingContent(), "New Project"); isNewProject = true;
            } else if (name === 'grid-generation') {
                // Grid Generation
                iframeInit("grid_generation", projectSetting(), projectSettingHeader(), 
                    projectSettingContent(), "Grid Generation");
                location.reload();
            } else if (name === 'run-simulation') {
                // Run Simulation
                iframeInit("run_simulation", simulationWindow(), simulationHeader(), 
                    simulationContent(), "Run Simulation");
            }
        }
    });
    // Listent events from open project iframe
    window.addEventListener('message', async (event) => {
        if (event.data?.type === 'projectConfirmed') {
            if (oldProject !== event.data.project) isNewProject = true;
            setProject({
                project: event.data.project,
                values: event.data.values
            });
            projectSetting().style.display = 'none';
            if (isNewProject) location.reload();
            else projectChecker();
        }
        if (event.data?.type === 'projectPreparation') { 
            const data = await sendQuery('setup_new_project', {projectName: event.data.name});
            alert(data.message);
        }
        if (event.data?.type === 'pickLocation') { 
            showPicker('location');
            markersPoints.forEach(marker => map.removeLayer(marker)); markersPoints = [];
        }
        if (event.data?.type === 'pickPoint') { 
            showPicker('point');
            // Remove existing markers
            markersPoints.forEach(marker => map.removeLayer(marker)); markersPoints = [];
            const rows = event.data.data.rows;
            // Add new markers
            rows.forEach(row => {
                const [name, lat, lon] = row;
                if (!name || isNaN(lat) || isNaN(lon)) return;
                const marker = L.marker([parseFloat(lat), parseFloat(lon)]).addTo(map);
                marker.bindPopup(name); markersPoints.push(marker);
            })
        }
        if (event.data?.type === 'updateObsPoint') {
            const rows = event.data.data.rows;
            // Remove existing markers
            markersPoints.forEach(marker => map.removeLayer(marker));
            markersPoints = [];
            if (rows.length === 0) return;
            // Add new markers
            rows.forEach(row => {
                const [name, lat, lon] = row;
                if (!name || isNaN(lat) || isNaN(lon)) return;
                const marker = L.marker([parseFloat(lat), parseFloat(lon)]).addTo(map);
                marker.bindPopup(name); markersPoints.push(marker);
            })
        }
        if (event.data?.type === 'pickCrossSection' || event.data?.type === 'clearCrossSection') { 
            if (event.data?.type === 'pickCrossSection') {
                showPicker('crosssection');
                const rows = event.data.data.rows;
                if (rows.length === 0) return;
            }
            markersCrosssection.forEach(marker => map.removeLayer(marker));
            markersCrosssection = []; crosssectionContainer = [];
            if (pathLineCrosssection) { map.removeLayer(pathLineCrosssection); pathLineCrosssection = null; }
        }
        if (event.data?.type === 'pickBoundary' || event.data?.type === 'clearBoundary') { 
            if (event.data?.type === 'pickBoundary') {
                showPicker('boundary');
                const rows = event.data.data.rows;
                if (rows.length === 0) return;
            }
            markersBoundary.forEach(marker => map.removeLayer(marker));
            markersBoundary = []; boundaryContainer = [];
            if (pathLineBoundary) { map.removeLayer(pathLineBoundary); pathLineBoundary = null; }
        }
        // Show/hide overlay
        if (event.data?.type === 'showOverlay') { startLoading(event.data.message); }
        if (event.data?.type === 'hideOverlay') { showLeafletMap(); }
        if (event.data?.type === 'pickSource') { showPicker('source'); }
        if (event.data?.type === 'plotSource') {
            const rows = event.data.rows;
            const columns = event.data.columns;
            const chartData = { columns, data: rows };
            drawChart(chartData, 'Source Data Chart', 'Time', 'Value', false);
        }
        if (event.data?.type === 'showGrid') {
            startLoading(event.data.message);
            const name = event.data.projectName;
            const gridName = event.data.gridName;
            const data = await sendQuery('open_grid', {projectName: name, gridName: gridName});
            if (data.status === "error") {alert(data.message); return;}
            // Show the grid on the map
            if (gridLayer) map.removeLayer(gridLayer);
            gridLayer = L.geoJSON(data.content, {style: {color: 'black', weight: 1}}).addTo(map);
            gridLayer.bindPopup("Grid: " + gridName);
            showLeafletMap();
        }
        if (event.data?.type === 'showGridTool') {
            const data = await sendQuery('open_gridTool', {});
            if (data.status === "error") {alert(data.message); return;}
        }
    });
    // Move window
    moveWindow(contactInfo, contactInfoHeader);
    moveWindow(projectSetting, projectSettingHeader);
    moveWindow(simulationWindow, simulationHeader);
    // Close windows
    contactInfoCloseBtn().addEventListener('click', () => { contactInfo().style.display = 'none'; });
    projectSettingCloseBtn().addEventListener('click', () => { 
        projectSetting().style.display = 'none'; 
        if (gridLayer) map.removeLayer(gridLayer);
    });
    simulationCloseBtn().addEventListener('click', () => { simulationWindow().style.display = 'none'; });
    map.on('mousemove', function (e) {
        if (!pickerState.location && !pickerState.point && !pickerState.source && !pickerState.crosssection && 
            !pickerState.boundary) {
            if (hoverTooltip) map.closeTooltip(hoverTooltip);
            mapContainer().style.cursor = 'grab';
            return;
        }
        if (pickerState.crosssection || pickerState.boundary) {
            if (!hoverTooltip) hoverTooltip = L.tooltip({
                permanent: false, direction: 'bottom',
                sticky: true, offset: [0, 10],
                className: 'custom-tooltip'
            });
            const html = `- Click the left mouse button to select a point.<br>- Right-click to finish the selection.`;
            hoverTooltip.setLatLng(e.latlng).setContent(html);
            map.openTooltip(hoverTooltip);
        }
        mapContainer().style.cursor = 'crosshair';
    })
    map.on('click', function(e) {
        if (pickerState.location) { hidePicker('location', e.latlng, 'locationPicked'); }
        if (pickerState.point) { 
            // Add marker
            const marker = L.marker([parseFloat(e.latlng.lat), parseFloat(e.latlng.lng)]).addTo(map);
                markersPoints.push(marker);
            hidePicker('point', e.latlng, 'pointPicked'); 
        }
        if (pickerState.crosssection && e.type === "click" && e.originalEvent.button === 0) { 
            // Add marker
            const marker = L.circleMarker(e.latlng, {
                radius: 5, color: 'blue', fillColor: 'cyan', fillOpacity: 0.9
            }).addTo(map);
            markersCrosssection.push(marker);
            // Add point
            crosssectionContainer.push({ lat: e.latlng.lat, lng: e.latlng.lng });
            // Plot line
            const latlngs = crosssectionContainer.map(p => [p.lat, p.lng]);
            if (pathLineCrosssection) {
                pathLineCrosssection.setLatLngs(latlngs);
            } else {
                pathLineCrosssection = L.polyline(latlngs, {
                    color: 'orange', weight: 2, dashArray: '5,5'
                }).addTo(map);
            }
        }
        if (pickerState.boundary && e.type === "click" && e.originalEvent.button === 0) { 
            // Add marker
            const marker = L.circleMarker(e.latlng, {
                radius: 5, color: 'red', fillColor: 'pink', fillOpacity: 0.9
            }).addTo(map);
            markersBoundary.push(marker);
            // Add point
            boundaryContainer.push({ lat: e.latlng.lat, lng: e.latlng.lng });
            // Plot line
            const latlngs = boundaryContainer.map(p => [p.lat, p.lng]);
            if (pathLineBoundary) {
                pathLineBoundary.setLatLngs(latlngs);
            } else {
                pathLineBoundary = L.polyline(latlngs, {
                    color: 'orange', weight: 2, dashArray: '5,5'
                }).addTo(map);
            }
        }
        if (pickerState.source) { 
            const marker = L.marker([parseFloat(e.latlng.lat), parseFloat(e.latlng.lng)]).addTo(map);
                markersPoints.push(marker);
            hidePicker('source', e.latlng, 'sourcePicked'); 
        }
    });
    map.on('contextmenu', function(e) {
        // Right-click
        if (pickerState.crosssection) {
            e.originalEvent.preventDefault(); // Suppress context menu
            if (crosssectionContainer.length < 2) {
                alert("Not enough points selected. Please select at least two points."); return;
            }
            hidePicker('crosssection', crosssectionContainer, 'crossSectionPicked');
        }
        if (pickerState.boundary) {
            e.originalEvent.preventDefault(); // Suppress context menu
            if (boundaryContainer.length < 2) {
                alert("Not enough points selected. Please select at least two points."); return;
            }
            hidePicker('boundary', boundaryContainer, 'boundaryPicked');
        }
        // Remove tooltip
        if (hoverTooltip) map.closeTooltip(hoverTooltip);        
    });
}

function showPicker(key){
    // Show point picker on the map
    pickerState[key] = true;
    mapContainer().style.cursor = 'crosshair';
    projectSetting().style.display = 'none';
}
function hidePicker(key, data, type){
    const iframe = projectSettingContent().querySelector("iframe");
    if (iframe) { iframe.contentWindow.postMessage({ type: type, content: data }, '*'); }
    pickerState[key] = false;
    mapContainer().style.cursor = 'grab';
    projectSetting().style.display = 'flex';
}

function measuredPointManager() {
    // Set function for plot using Plotly
    document.querySelectorAll('.function').forEach(plot => {
        plot.addEventListener('click', () => {
            const [filename, key, titleY, chartTitle] = plot.dataset.info.split('|');
            plotChart(filename, key, chartTitle, 'Time', titleY, false);
        });
    });
}

function staticMapManager() {
    deactivePathQuery(); deactivePointQuery(); 
    document.querySelectorAll('.map2D_static').forEach(plot => {
        plot.addEventListener('click', () => {
            const [filename, key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapStatic(filename, key, colorbarTitle, colorbarKey);
        });
    });
}

function contacInformation() {
    // Add iframe if not exist
    if (!contactInfoContent().querySelector("iframe")) {
        const iframe = document.createElement("iframe");
        iframe.src = "/load_contact";
        contactInfoContent().appendChild(iframe);
    }
    contactInfo().style.display = 'flex';
}

