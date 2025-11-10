// Import necessary functions
import { initializeMap, baseMapButtonFunctionality } from './mapManager.js';
import { startLoading, showLeafletMap, map } from './mapManager.js';
import { plotChart, plotEvents, drawChart, plotWindow, thermoclinePlotter } from './chartManager.js';
import { timeControl, colorbar_container } from "./map2DManager.js";
import { generalOptionsManager, summaryWindow, profileWindow } from './generalOptionManager.js';
import { spatialMapManager } from './spatialMapManager.js';
import { sendQuery } from './tableManager.js';
import { resetState, setState } from './constants.js';

let pickerState = { location: false, point: false, crosssection: false, boundary: false, source: false },
    cachedMenus = {}, markersPoints = [], hoverTooltip, markersBoundary = [], boundaryContainer = [],
    pathLineBoundary = null, ws = null, currentProject = null, gridLayer = null, timeOut = null,
    markersCrosssection = [], crosssectionContainer = [], pathLineCrosssection = null, hideTimeout = null;

const popupMenu = () => document.getElementById('popup-menu');
const popupContent = () => document.getElementById('popup-content');
const contactInfo = () => document.getElementById('informationContact');
const contactInfoHeader = () => document.getElementById('informationContactHeader');
const contactInfoContent = () => document.getElementById('informationContactContent');
const contactInfoCloseBtn = () => document.getElementById('closeInformationContact');
const locationSearcher = () => document.getElementById('search');
const sugesstionSearcher = () => document.getElementById('suggestions');
const projectTitle = () => document.getElementById('projectTitle');
const projectOpenWindow = () => document.getElementById('project-open-window');
const projectOpenWindowHeader = () => document.getElementById('project-open-window-header');
const projectOpenWindowContent = () => document.getElementById('project-open-window-content');
const projectOpenCloseBtn = () => document.getElementById('project-open-window-close');
const substanceWindow = () => document.getElementById('substance-window');
const substanceWindowHeader = () => document.getElementById('substance-window-header');
const substanceWindowContent = () => document.getElementById('substance-window-content');
const substanceWindowCloseBtn = () => document.getElementById('substance-window-close');
const projectSetting = () => document.getElementById('projectWindow');
const projectSettingHeader = () => document.getElementById('projectWindowHeader');
const projectSettingContent = () => document.getElementById('projectWindowContent');
const projectSettingCloseBtn = () => document.getElementById('closeProjectWindow');
const simulationWindow = () => document.getElementById('simulationWindow');
const simulationHeader = () => document.getElementById('simulationWindowHeader');
const simulationContent = () => document.getElementById('simulationWindowContent');
const simulationCloseBtn = () => document.getElementById('closeSimulationWindow');
const waqWindow = () => document.getElementById('waqWindow');
const waqWindowHeader = () => document.getElementById('waqWindowHeader');
const waqCloseBtn = () => document.getElementById('closeWAQWindow');
const waqProgressbar = () => document.getElementById('progressbar');
const waqProgressText = () => document.getElementById('progress-text');
// const profileWindow = () => document.getElementById('profileWindow-thermocline');
// const profileWindowHeader = () => document.getElementById('profileWindowHeader');
// const profileCloseBtn = () => document.getElementById('closeProfileWindow');
const mapContainer = () => map.getContainer();

initializeMap(); baseMapButtonFunctionality();
projectChecker(); initializeMenu();
updateEvents(); plotEvents();

// ============================ Functions ============================

async function showPopupMenu(id, htmlFile) {
    try {
        let html;
        if (cachedMenus[htmlFile]) html = cachedMenus[htmlFile];
        else {
            const response = await fetch(`/load_popupMenu?htmlFile=${htmlFile}`);
            if (response.status === 'error') {alert(response.message); return;}
            html = await response.text();
            cachedMenus[htmlFile] = html;
        }
        popupContent().innerHTML = html;
        if (id === '1') generalOptionsManager(); // Events on general options submenu
        if (id === '2') timeSeriesManager(); // Events on time series measurement submenu
        if (id === '3') spatialMapManager(); // Events on spatial map submenu
    } catch (error) {alert(error + ': ' + htmlFile);}
}

async function projectChecker(name=null, params=null) {
    cachedMenus = {}; // Clear cache of menus for new project
    const projectMenu = document.querySelectorAll('.menu');
    projectMenu.forEach(menu => { menu.style.display = (name===null)?'none':'block'; });
    const project = document.querySelector('.menu[data-info="0|projectMenu.html"]');
    project.style.display = 'block'; projectTitle().textContent = '';
    // Clear map
    map.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) map.removeLayer(layer); });
    resetState();  // Reset variables
    if (name === null) return;
    if (summaryWindow().style.display !== 'flex') summaryWindow().style.display = 'none';  // Close summary window if open
    projectTitle().textContent = `Project: ${name}`;
    startLoading('Reading Simulation Outputs and Setting up Database.\nThis takes a while. Please wait...');
    const data = await sendQuery('setup_database', {projectName: name, params: params});
    if (data.status === "error") {alert(data.message); location.reload(); }
    showLeafletMap();
}

async function initializeMenu(){
    // Work with pupup menu
    document.querySelectorAll('.nav ul li a').forEach(link => {
        link.addEventListener('click', async(event) => {
            event.stopPropagation(); event.preventDefault();
            const rect = link.getBoundingClientRect();
            const pm = popupMenu();
            if (pm.classList.contains('show')) pm.classList.remove('show');
            const info = link.dataset.info;
            if (info === 'home') { history.back(); return; }
            if (info === 'help') { contactInformation(); return;}
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
    let dragging = false, offsetX = 0, offsetY = 0;
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

// iframeInit("open_project", projectOpenWindow(), projectOpenWindowHeader(), 
//                     projectOpenWindowContent(), "Select Project with Simulation Result(s)");
iframeInit("run_hyd_simulation", simulationWindow(), simulationHeader(), 
                    simulationContent(), "Run Hydrodynamic Simulation");

function updateEvents() {
    // Search locations
    locationSearcher().addEventListener('input', (e) => {
        clearTimeout(timeOut);
        const value = e.target.value.trim();
        if (value === '' || value.length < 2) { sugesstionSearcher().style.display = 'none'; return; }
        timeOut = setTimeout(() => {
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(value)}&addressdetails=1&limit=5`)
            .then(response => response.json()).then(data => {
                if (data.length === 0) {sugesstionSearcher().style.display = 'none';}
                sugesstionSearcher().innerHTML = '';
                data.forEach(location => {
                    var div = document.createElement('div');
                    div.textContent = location.display_name;
                    div.addEventListener('click', () => {
                        var lat = location.lat, lng = location.lon;
                        map.setView([lat, lng], 12);
                        locationSearcher().value = location.display_name;
                        sugesstionSearcher().style.display = 'none';
                    });
                    sugesstionSearcher().appendChild(div);
                });
                sugesstionSearcher().style.display = 'block';
            })
        }, 200);
    });
    // Check if events are already bound
    if (window.__menuEventsBound) return;
    window.__menuEventsBound = true;
    const pm = popupMenu();
    // Show popup menu on click or leave
    if (pm) {
        pm.addEventListener('mouseenter', () => {
            pm.classList.add('show');
            if (hideTimeout) { clearTimeout(hideTimeout); hideTimeout = null; }
        });
        pm.addEventListener('mouseleave', () => {
            hideTimeout = setTimeout(() => {
                pm.classList.remove('show');
            }, 500);
        });
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
        // Hide suggestions for location search
        if (!document.querySelector('.search-box').contains(e.target)) {
            sugesstionSearcher().style.display = 'none';
        }
    });
    popupContent().addEventListener('click', (e) => {
        const project = e.target.closest('.project');
        if (project) {
            const name = project.dataset.info;
            if (name === 'visualization') {
                // Open project for visualization
                iframeInit("open_project", projectOpenWindow(), projectOpenWindowHeader(), 
                    projectOpenWindowContent(), "Select Project with Simulation Result(s)");
            } else if (name === 'new-hyd-project') { 
                // Create new hyd project
                projectChecker();
                iframeInit("new_HYD_project", projectSetting(), projectSettingHeader(), 
                    projectSettingContent(), "Set up a new Hydrodynamic project");
            } else if (name === 'run-hyd-simulation') {
                // Run hyd simulation
                projectChecker();
                iframeInit("run_hyd_simulation", simulationWindow(), simulationHeader(), 
                    simulationContent(), "Run Hydrodynamic Simulation");
            } else if (name === 'new-wq-project') { 
                // Create and run a new wq project
                projectChecker();
                iframeInit("new_WQ_project", projectSetting(), projectSettingHeader(), 
                    projectSettingContent(), "Set up and Run Water Quality Simulation");
            } else if (name === 'grid-generation') {
                projectChecker();
                // Grid Generation
                iframeInit("grid_generation", projectSetting(), projectSettingHeader(), 
                    projectSettingContent(), "Grid Generation");
            } 
        }
    });
    // Listent events from open project iframe
    window.addEventListener('message', async (event) => {
        if (event.data?.type === 'resize-simulation') {
            const frameHeight = event.data.height;
            if (simulationWindow()) { simulationWindow().style.height = frameHeight + 'px'; }
        }
        if (event.data?.type === 'projectConfirmed') {
            projectChecker(event.data.project, event.data.values);
            projectOpenWindow().style.display = 'none';
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
            // Set custom icon
            const pointType = event.data.pointType;
            let inconUrl = null, rows = null;
            // Remove existing markers
            markersPoints.forEach(marker => map.removeLayer(marker)); markersPoints = [];
            if (pointType === 'obsPoint') {
                rows = event.data.data.rows;
                inconUrl = `/static_backend/images/station.png?v=${Date.now()}`;
            }
            else if (pointType === 'waqPoint') {
                const temp = event.data.data[0].rows;
                // Plot loads on map if available
                if (temp.length > 0) {
                    inconUrl = `/static_backend/images/waq_loads.png?v=${Date.now()}`;
                    const customIcon = L.icon({
                        iconUrl: inconUrl, iconSize: [20, 20], popupAnchor: [1, -34],
                    });
                    temp.forEach(row => {
                        const [name, lat, lon] = row;
                        if (!name || isNaN(lat) || isNaN(lon)) return;
                        const marker = L.marker([parseFloat(lat), parseFloat(lon)], { icon: customIcon }).addTo(map);
                        marker.bindPopup(name); markersPoints.push(marker);
                    })
                }
                rows = event.data.data[1].rows;
                inconUrl = `/static_backend/images/waq_obs.png?v=${Date.now()}`;
            }
            else if (pointType === 'loadsPoint') {
                const temp = event.data.data[0].rows;
                if (temp.length > 0) {
                    inconUrl = `/static_backend/images/waq_obs.png?v=${Date.now()}`;
                    const customIcon = L.icon({
                        iconUrl: inconUrl, iconSize: [20, 20], popupAnchor: [1, -34],
                    });
                    temp.forEach(row => {
                        const [name, lat, lon] = row;
                        if (!name || isNaN(lat) || isNaN(lon)) return;
                        const marker = L.marker([parseFloat(lat), parseFloat(lon)], { icon: customIcon }).addTo(map);
                        marker.bindPopup(name); markersPoints.push(marker);
                    })
                }
                rows = event.data.data[1].rows;
                inconUrl = `/static_backend/images/waq_loads.png?v=${Date.now()}`;
            }
            const customIcon = L.icon({
                iconUrl: inconUrl, iconSize: [20, 20], popupAnchor: [1, -34],
            });
            // Add new markers
            rows.forEach(row => {
                const [name, lat, lon] = row;
                if (!name || isNaN(lat) || isNaN(lon)) return;
                const marker = L.marker([parseFloat(lat), parseFloat(lon)], { icon: customIcon }).addTo(map);
                marker.bindPopup(name); markersPoints.push(marker);
            })
        }
        if (event.data?.type === 'updateObsPoint') {
            const rows = event.data.data.rows;
            // Remove existing markers
            markersPoints.forEach(marker => map.removeLayer(marker)); markersPoints = [];
            const customIcon = L.icon({
                iconUrl: `/static_backend/images/station.png?v=${Date.now()}`,
                iconSize: [20, 20], popupAnchor: [1, -34],
            });
            // Add new markers
            rows.forEach(row => {
                const [name, lat, lon] = row;
                if (!name || isNaN(lat) || isNaN(lon)) return;
                const marker = L.marker([parseFloat(lat), parseFloat(lon)], { icon: customIcon }).addTo(map);
                marker.bindPopup(name); markersPoints.push(marker);
            })
            alert('Observation points updated. See the map for details.');
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
        if (event.data?.type === 'addWQSource') {
            const sources = event.data.sources;
            sources.forEach(row => {
                const [name, lat, lon] = row;
                if (!name || isNaN(lat) || isNaN(lon)) return;
                const marker = L.marker([parseFloat(lat), parseFloat(lon)]).addTo(map);
                marker.bindPopup(name);
            })
        }
        if (event.data?.type === 'showGrid') {
            startLoading(event.data.message);
            const name = event.data.projectName, gridName = event.data.gridName;
            const data = await sendQuery('open_grid', {projectName: name, gridName: gridName});
            if (data.status === "error") {alert(data.message); return;}
            // Show the grid on the map
            if (gridLayer) map.removeLayer(gridLayer); gridLayer = null;
            gridLayer = L.geoJSON(data.content, {style: {color: 'black', weight: 1}}).addTo(map);
            showLeafletMap();
        }
        if (event.data?.type === 'showGridTool') {
            const data = await sendQuery('open_gridTool', {});
            if (data.status === "error") {alert(data.message); return;}
        }
        if (event.data?.type === 'thermoclineGrid') {
            startLoading(event.data.message);
            const key = event.data.key, query = event.data.query;
            const titleX = event.data.titleX, chartTitle = event.data.chartTitle;
            const data = await sendQuery('select_thermocline', {key: key, query: query,
                type: 'thermocline_grid'});
            if (data.status === "error") {alert(data.message); return;}
            if (gridLayer) map.removeLayer(gridLayer); gridLayer = null;
            gridLayer = L.geoJSON(data.content, {
                style: {color: 'black', weight: 1},
                onEachFeature: function (feature, layer) {
                    layer.on('click', function (e) {
                        const index = feature.properties.index;
                        // Make popup HTML
                        const popupContent = `
                            <div style="width:200px">
                                <h4 style="margin:0 0 6px 0;">Change Index: #${index}</h4>
                                <label>New Name:</label>
                                <input id="nameInput" type="text" value="${index}" 
                                    style="width:100%;margin-bottom:6px;padding:3px;" />
                                <button id="saveBtn" 
                                    style="width:100%;padding:4px;background:#007bff;
                                    color:white;border:none;border-radius:4px;cursor:pointer;">
                                    OK
                                </button>
                            </div>
                        `;
                        layer.bindPopup(popupContent).openPopup(e.latlng);
                        // Add event listener to save button
                        setTimeout(() => {
                            const input = document.getElementById('nameInput');
                            const saveBtn = document.getElementById('saveBtn');
                            if (input && saveBtn) {
                                saveBtn.addEventListener('click', async() => {
                                    const newName = input.value;
                                    if (newName !== '') {
                                        const initData = await sendQuery('select_thermocline', {key: key,
                                            query: query, idx: index, type: 'thermocline_init'});
                                        layer.closePopup(); setState({isThemocline: false});
                                        if (initData.status === "error") { alert(initData.message); return; }
                                        thermoclinePlotter(profileWindow, initData.content, newName, titleX, 'Depth (m)', chartTitle);
                                    } else { alert('Please enter a name.'); return; }
                                });
                            }
                        }, 200);
                    });
                }
            }).addTo(map);
            showLeafletMap();
        }
        if (event.data?.type === 'run-wq') {
            const params = event.data.data;
            // Check if simulation is running
            const statusRes = await sendQuery('check_sim_status_waq', {projectName: params.projectName});
            if (statusRes.status === "running") {
                alert("Simulation is already running for this project."); return;
            }
            waqWindow().style.display = 'flex';
            currentProject = params.projectName;
            ws = new WebSocket(`ws://${window.location.host}/sim_progress_waq/${currentProject}`);
            waqProgressText().innerText = 'Start running water quality simulation...';
            ws.onopen = () => {
                ws.send(JSON.stringify(params));
                waqProgressText().innerText = ''; waqProgressbar().value = 0;
            }
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.error) { waqProgressText().innerText = data.error; return; }
                if (data.status !== undefined) waqProgressText().innerText = data.status;
                if (data.logs !== undefined) waqProgressText().innerText = data.logs;
                if (data.progress !== undefined) {
                    waqProgressText().innerText = 'Completed: ' + data.progress + '%';
                    waqProgressbar().value = data.progress;
                }
            };
        }
    });
    // Move window
    moveWindow(contactInfo, contactInfoHeader); moveWindow(projectOpenWindow, projectOpenWindowHeader);
    moveWindow(projectSetting, projectSettingHeader); moveWindow(simulationWindow, simulationHeader);
    moveWindow(substanceWindow, substanceWindowHeader); moveWindow(waqWindow, waqWindowHeader);
    // Close windows
    substanceWindowCloseBtn().addEventListener('click', () => { 
        substanceWindow().style.display = 'none'; plotWindow().style.display = 'none';
        map.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) map.removeLayer(layer); });
        timeControl().style.display = 'none'; colorbar_container().style.display = 'none';
    });
    contactInfoCloseBtn().addEventListener('click', () => { contactInfo().style.display = 'none'; });
    projectOpenCloseBtn().addEventListener('click', () => { projectOpenWindow().style.display = 'none'; });
    projectSettingCloseBtn().addEventListener('click', () => { 
        // Clear map
        map.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) map.removeLayer(layer); });
        projectSetting().style.display = 'none'; 
    });
    simulationCloseBtn().addEventListener('click', () => { simulationWindow().style.display = 'none'; });
    waqCloseBtn().addEventListener('click', () => { waqWindow().style.display = 'none'; });
    map.on('mousemove', function (e) {
        if (!pickerState.location && !pickerState.point && !pickerState.source && !pickerState.crosssection && 
            !pickerState.boundary) {
            if (hoverTooltip) map.closeTooltip(hoverTooltip);
            mapContainer().style.cursor = 'grab'; return;
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
            boundaryContainer.push({ lat: e.latlng.lat, lng: e.latlng.lng });  // Add point
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
        if (hoverTooltip) map.closeTooltip(hoverTooltip); // Remove tooltip
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

function timeSeriesManager() {
    // Set function for plot using Plotly
    document.querySelectorAll('.function').forEach(plot => {
        plot.addEventListener('click', () => {
            const [key, titleY, chartTitle] = plot.dataset.info.split('|');
            plotChart('', key, chartTitle, 'Time', titleY);
        });
    });
    // Process water quality selector
    document.querySelectorAll('.waq_his').forEach(item => {
        item.addEventListener('click', async() => {
            const query = item.dataset.info;
            const data = await sendQuery('process_data', {query: query, key: 'substance_check'});
            if (data.status === "error") {alert(data.message); substanceWindow().style.display = 'none'; return;}
            substanceWindowContent().innerHTML = '';
            // Add content
            substanceWindowContent().innerHTML = data.message.map((substance, i) => 
                `<label for="${substance}"><input type="radio" name="waq-substance" id="${substance}"
                    value="${data.content[i]}" ${i === 0 ? 'checked' : ''}>${data.content[i]}</label>`).join('');
            substanceWindow().style.display = 'flex';
            plotChart(data.message[0], 'substance', `Substance: ${data.content[0]}`, 'Time', data.content[0]);
        });
    });
    // Listen to substance selection
    substanceWindowContent().addEventListener('change', (e) => {
        if (e.target && e.target.name === "waq-substance") {
            const id = e.target.id, value = e.target.value;
            plotChart(id, 'substance', `Substance: ${value}`, 'Time', value);
        }
    });
}

function contactInformation() {
    // Add iframe if not exist
    if (!contactInfoContent().querySelector("iframe")) {
        const iframe = document.createElement("iframe");
        iframe.src = "/load_contact";
        contactInfoContent().appendChild(iframe);
    }
    contactInfo().style.display = 'flex';
}