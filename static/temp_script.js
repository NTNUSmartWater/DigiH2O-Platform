let stationLayer = null, crossSectionLayer = null, isOpen = true; 
let isDragging_infor = false, offsetX_infor = 0, offsetY_infor = 0;
let isDragging_plot = false, offsetX_plot = 0, offsetY_plot = 0;
let queryPoint = false, queryPath = false, currentMarker = null;
let layerStatic = null, layerDynamic = null, isPlaying = null;
let layerBelow = null, layerAbove = null;
let playHandlerAttached = false, isinfoOpen = false, currentIndex = 0;
let colorbarControl = L.control({ position: 'topright' });
let parsedDataAllFrames = null, pointContainer = []; isPath = false;
let selectedMarkers = [], pathLine = null, marker = null;
let storedLayer = false, clickedInsideLayer = false;
let isPathQuery = false, polygonCentroids = [];
const CENTER = [62.476969, 6.471598], ZOOM = 13;
const pathQueryCheckbox = document.getElementById("pathQuery");
const pointQueryCheckbox = document.getElementById("pointQuery");
const chartDiv = document.getElementById('myChart');
const content = document.getElementById("infoContent");
const menu = document.getElementById("offCanvasMenu");
const button = document.getElementById('menuBtn');
const loading = document.getElementById('loadingOverlay');
const leaflet_map = document.getElementById('leaflet_map');
const arrow = document.getElementById("arrowToggle");
const infoDetails = document.getElementById("infoDetails");
const infoPanel = document.getElementById("infoPanel");
const infoPanelHeader = document.getElementById("infoPanelHeader")
const slider = document.getElementById("time-slider");
const playBtn = document.getElementById("play-btn");
const timeControl = document.getElementById("time-controls");
const exportVideoBtn = document.getElementById("export-video-btn");
const selectObject = document.getElementById("select-object");
const velocityObject = document.getElementById("velocity-object");
let colorbar_title = document.getElementById("colorbar-title");
let colorbar_color = document.getElementById("colorbar-gradient");
let infor = document.getElementById("infoDetailsContent");
let infoHeader = document.getElementById("infoHeader");
let infoWindow = document.getElementById("infoWindow");
let plotHeader = document.getElementById("plotHeader");
let plotWindow = document.getElementById("plotWindow");
const belowLayer = document.getElementById("below-object");
const aboveLayer = document.getElementById("above-object");
const plotLayersBtn = document.getElementById("plotLayersBtn");
let globalChartData = {
    filename: "", data: null, title: "", validColumns: [], columnIndexMap: {}
};
const hoverTooltip = L.tooltip({
  permanent: false, direction: 'bottom',
  sticky: true, offset: [0, 10],
  className: 'custom-tooltip' // optional: for styling
});

const arrowShape = new Path2D();
arrowShape.moveTo(0, 0);          // Origin
arrowShape.lineTo(1, 0);          // Main length
arrowShape.moveTo(1, 0);
arrowShape.lineTo(0.8, 0.1);      // Left branch
arrowShape.moveTo(1, 0);
arrowShape.lineTo(0.8, -0.1);     // Right branch


// Define CanvasLayer
L.CanvasLayer = L.Layer.extend({
    initialize: function (options) { L.setOptions(this, options);},
    onAdd: function (map) {
        this._map = map;
        this._canvas = L.DomUtil.create('canvas', 'leaflet-layer');
        const size = map.getSize();
        this._canvas.width = size.x;
        this._canvas.height = size.y;
        const pane = map.getPane(this.options.pane || 'overlayPane');
        pane.appendChild(this._canvas);
        this._ctx = this._canvas.getContext('2d');
        map.on('moveend zoomend resize', this._reset, this);
        this._reset();
    },
    onRemove: function (map) {
        const pane = map.getPane(this.options.pane || 'overlayPane');
        if (this._canvas) pane.removeChild(this._canvas);
        map.off('moveend zoomend resize', this._reset, this);
    },
    _reset: function () {
        const size = this._map.getSize();
        this._canvas.width = size.x;
        this._canvas.height = size.y;
        const topLeft = this._map.containerPointToLayerPoint([0, 0]);
        L.DomUtil.setPosition(this._canvas, topLeft);
        this._redraw();
    },
    _redraw: function () {
        if (typeof this.options.drawLayer === 'function') {
            this.options.drawLayer.call(this);
        }
    }
});

// Show spinner when loading
function startLoading() {
    loading.style.display = 'flex';
    leaflet_map.style.display = 'none';
}
function showLeafletMap() {
    leaflet_map.style.display = "block";
    loading.style.display = "none";
}

// Generate the map
var map = L.map('leaflet_map', {center:CENTER, zoom: ZOOM, zoomControl: false});
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}').addTo(map);        
// Add scale bar
L.control.scale({
    position: 'bottomright', imperial: false, metric: true, maxWidth: 200
}).addTo(map);

// Add tooltip
map.on('mousemove', function (e) {
    if (!isPath) {
        map.closeTooltip(hoverTooltip);
        return;
    }
    const html = `- Click the left mouse button to select a point.<br>- Right-click to finish the selection.`;
    hoverTooltip.setLatLng(e.latlng).setContent(html);
    map.openTooltip(hoverTooltip);
});

// Move the control to the top right corner
const scaleElem = document.querySelector('.leaflet-control-scale');
document.getElementById('right-side-controls').appendChild(scaleElem);

document.addEventListener('click', function(event) {
    // Hide the main menu and info menu if user clicks outside of it
    if (menu && button) {
        const isClickedInsideMenu = menu.contains(event.target) || button.contains(event.target);
        if (!isClickedInsideMenu && isOpen) {toggleMenu();}
    }
    if (queryPoint){return;}
    if (infoPanelHeader) {
        const isClickedInsideInfo = infoPanel.contains(event.target);
        if (!isClickedInsideInfo && isinfoOpen) {toggleinfoMenu();}
    }
})

// Function to toggle the menu
function toggleMenu() {
    menu.style.width = isOpen ? "0" : "320px"; isOpen = !isOpen;    
}

function toggleinfoMenu() {
    if (isinfoOpen) {
        infoPanel.style.height = "35px"; arrow.textContent = "▼";
    } else {
        // Open the info menu with measured height
        infoPanel.style.height = infoPanel.scrollHeight + "px";
        // Asign auto scroll
        const removeFixedHeight = () => {
            infoPanel.style.height = "auto";
            infoPanel.removeEventListener("transitionend", removeFixedHeight);
        };
        infoPanel.addEventListener("transitionend", removeFixedHeight);
        arrow.textContent = "▲";
    }
    isinfoOpen = !isinfoOpen;
}
infoPanelHeader.addEventListener("click", toggleinfoMenu);

// Function to toggle the chart
function toggleChart(key=NaN) {
    const chart = document.getElementById("chartPanel");
    const bottomPx = parseFloat(window.getComputedStyle(chart).bottom);
    if (bottomPx !== 0) { chart.style.bottom = "0";}
    if (key === '') { chart.style.bottom = "-100%"; }
}

// Get all menu-link having submenu
document.querySelectorAll('.menu-item-with-submenu .menu-link').forEach(link => {
    link.addEventListener('click', function(event) {
        event.preventDefault();
        const submenu = this.nextElementSibling;
        if (!submenu) return; // No submenu found
        // Close other submenus and remove active on menu-links
        document.querySelectorAll('.submenu.open').forEach(openSubmenu => {
            if (openSubmenu !== submenu) {
                openSubmenu.classList.remove('open');
            }
        });
        document.querySelectorAll('.menu-link.active').forEach(activeLink => {
            if (activeLink !== this) {
                activeLink.classList.remove('active');
            }
        });
        // Toggle class open
        submenu.classList.toggle('open'); this.classList.toggle('active');
    });
});

document.querySelectorAll('.menu-item-with-submenu_1 .menu-link_1').forEach(link => {
    link.addEventListener('click', function(event) {
        event.preventDefault();
        const submenu = this.nextElementSibling;
        if (!submenu) return; // No submenu found
        // Close other submenus and remove active on menu-links
        document.querySelectorAll('.submenu_1.open').forEach(openSubmenu => {
            if (openSubmenu !== submenu) {
                openSubmenu.classList.remove('open');
            }
        });
        document.querySelectorAll('.menu-link_1.active').forEach(activeLink => {
            if (activeLink !== this) {
                activeLink.classList.remove('active');
            }
        });
        // Toggle class open
        submenu.classList.toggle('open');
        this.classList.toggle('active');
    });
});

// Function to open project summary
function openProjectSummary(filename) {
    const currentDisplay = window.getComputedStyle(infoWindow).display;
    if (currentDisplay === "none") {
        // Read the project summary
        fetch(`/get_json?data_filename=${filename}`)
            .then(response => response.json()).then(data => {
                if (data.status === "ok") {
                    // Create a table to display the summary
                    let html = `
                        <table>
                        <thead>
                            <tr>
                            <th style="text-align: center;">Parameter</th>
                            <th style="text-align: center;">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                    `;
                    data.content.forEach(item => {
                        html += `
                            <tr>
                                <td>${item.parameter}</td>
                                <td>${item.value}</td>
                            </tr>
                        `;
                    });
                    html += `
                        </tbody>
                        </table>
                    `;
                    content.innerHTML = html;
                    // Open the summary window
                    infoWindow.style.display = "block";
                } else if (data.status === "error") {alert(data.message);}  
            });
    } else { infoWindow.style.display = "none";}
    toggleMenu();
}

// Move summary window
infoHeader.addEventListener("mousedown", function(e) {
    isDragging_infor = true;
    offsetX_infor = e.clientX - infoWindow.offsetLeft;
    offsetY_infor = e.clientY - infoWindow.offsetTop;
});
plotHeader.addEventListener("mousedown", function(e) {
    isDragging_plot = true;
    offsetX_plot = e.clientX - plotWindow.offsetLeft;
    offsetY_plot = e.clientY - plotWindow.offsetTop;
});
document.addEventListener("mousemove", function(e) {
    if (isDragging_infor) {
        infoWindow.style.left = (e.clientX - offsetX_infor) + "px";
        infoWindow.style.top = (e.clientY - offsetY_infor) + "px";
    }
    if (isDragging_plot) {
        plotWindow.style.left = (e.clientX - offsetX_plot) + "px";
        plotWindow.style.top = (e.clientY - offsetY_plot) + "px";
    }
});
document.addEventListener("mouseup", function() {
    isDragging_infor = false; isDragging_plot = false;
    Plotly.Plots.resize(chartDiv);
});

// Load JSON file (including JSON and GeoJSON)
async function loadData(filename, key, title, colorbarKey='depth', station='') {
    // Show spinner
    startLoading();
    // Deselect checkbox
    if (pathQueryCheckbox.checked) pathQueryCheckbox.checked = false;
    if (pointQueryCheckbox.checked) pointQueryCheckbox.checked = false;
    hideQuery('path'); hideQuery('point');
    try {
        const response = await fetch('/process_data', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({data_filename: filename, key: key, station: station})});
        const data = await response.json();
        if (data.status === "ok") {
            if (key === "stations") {
                // Add station layer to the map
                if (!stationLayer) {
                    stationLayer = L.geoJSON(data.content, {
                        // Custom marker icon
                        pointToLayer: function (feature, latlng) {
                            const customIcon = L.icon({
                                iconUrl: 'images/station.png?v=${Date.now()}',
                                iconSize: [30, 30], popupAnchor: [1, -34],
                            });
                            const marker = L.marker(latlng, {icon: customIcon});
                            const id = feature.properties.name || 'Unknown';
                            // Add tooltip
                            const value = `
                                <div style="text-align: center;">
                                    <b>${id}</b><br>Select object to see more parameters
                                </div>
                            `;
                            marker.bindTooltip(value, {
                                permanent: false, direction: 'top', offset: [0, 0]
                            });
                            // Add popup
                            const popupContent = `
                                <div style="font-family: Arial;">
                                    <h3 style="text-align: center;">${id}</h3>
                                    <hr style="margin: 0;">
                                    <ul style="left: 0; cursor: pointer; padding-left: 0; list-style: none;">
                                        <li><a  onclick="loadData('temperature_in-situ.json', 'temperature', 'Temperature (°C)', 'temperature', '${id}')">• Temperature</a></li>
                                        <li><a  onclick="loadData('salinity_in-situ.json', 'salinity', 'Salinity (PSU)', undefined, '${id}')">• Salinity</a></li>
                                        <li><a  onclick="loadData('contaminant_in-situ.json', 'Contaminant', 'Contaminant (μg/L)', undefined, '${id}')">• Contaminant</a></li>
                                    </ul>
                                </div>
                            `;
                            marker.bindPopup(popupContent, {offset: [0, 40]});
                            return marker;
                        }   
                    }).addTo(map);
                    // Zoom to the extent of the station layer
                    if (stationLayer && stationLayer.getBounds().isValid()) {
                        const center = stationLayer.getBounds().getCenter();
                        map.setView(center, ZOOM);
                    }
                }   
            } else if (key === "cross_sections") {
                // Add cross section layer to the map
                if (!crossSectionLayer) {
                    


                }
            } else if (filename.includes(".json")) {
                // Plot data
                drawChart(filename, data.content, title);
                toggleMenu();
            } else if (filename.includes("velocity")){
                // Plot a vector map
                plotVectorMap(data.content, title, colorbarKey);
            } else {
                // Plot a 2D map
                plotMap(data.content, filename, title, colorbarKey);            
            }
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    showLeafletMap(); // Hide the spinner and show the map
}

function changeVelocity(object) {
    if (object.selectedIndex === 0) return;
    const index = object.selectedIndex - 1;
    loadData(`${object.value}_velocity`, index, 'Velocity (m/s)', 'velocity');
}

async function initiateVelocities() {
    startLoading();
    try {
        const response = await fetch('/process_velocity', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})});
        const data = await response.json();
        if (data.status === "ok") {
            // Add options to the velocity object
            velocityObject.innerHTML = '';
            // Add hint to the velocity object
            const hint_velocity = document.createElement('option');
            hint_velocity.value = ''; hint_velocity.selected = true;
            hint_velocity.textContent = '-- Select a type --'; 
            velocityObject.add(hint_velocity);
            // Add options
            data.content.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                velocityObject.add(option);
            });
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    // Hide the spinner and show the map
    showLeafletMap();
}

function buildFrameData(data, i) {
    const coordsArray = data.coordinates, values = data.values[i];
    const result = [];    
    for (let i = 0; i < coordsArray.length; i++) {
        const coords = coordsArray[i];
        const val = values[i];
        if (typeof val === 'string') {
            const temp = val.replace(/[()]/g, '');
            parts = temp.split(',').map(s => parseFloat(s.trim()));
        } else if (Array.isArray(val)) { parts = val.map(Number); }
        if (!isNaN(parts[0]) && !isNaN(parts[1]) && !isNaN(parts[2])) {
            result.push({
                x: coords[0], y: coords[1], a: parts[0], b: parts[1], c: parts[2]
            });
        }
    }
    return result;
}

function vectorCreator(parsedData, vmin, vmax, title, colorbarKey, key='velocity') {
    if (layerStatic && map.hasLayer(layerStatic)) {
        map.removeLayer(layerStatic); layerStatic = null;
    };
    if (layerDynamic && map.hasLayer(layerDynamic)) {
        map.removeLayer(layerDynamic); layerDynamic = null;
    };
    const scale = 900, arrowLength = 1;
    const layer = new L.CanvasLayer({ data: parsedData,
        drawLayer: function () {
            const ctx = this._ctx, map = this._map;
            const canvas = ctx.canvas, data = this.options.data;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (let i = 0; i < data.length; i++) {
                const pt = data[i];
                const p = map.latLngToContainerPoint([pt.y, pt.x]);
                if (p.x < 0 || p.x > canvas.width || p.y < 0 || p.y > canvas.height) continue;
                const dx = pt.a * scale, dy = -pt.b * scale;
                const length = Math.sqrt(dx * dx + dy * dy);
                if (length < 0.1) continue;
                const angle = Math.atan2(dy, dx);
                ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(angle);
                ctx.scale(length / arrowLength, length / arrowLength);
                if (key === "velocity") {
                    const color = getColorFromValue(pt.c, vmin, vmax, colorbarKey);
                    ctx.strokeStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
                } else {
                    ctx.strokeStyle = "rgba(255, 255, 255, 1)";
                }
                ctx.lineWidth = 1 / (length / arrowLength);
                ctx.stroke(arrowShape); ctx.restore();
            }
        }
    });
    // Adjust Colorbar Control
    updateColorbar(vmin, vmax, title, colorbarKey);
    return layer;
}

function plotVectorMap(data, title, colorbarKey) {
    timeControl.style.display = "flex"; // Show time slider
    // Get column name
    const timestamp = data.time;
    // Get min and max values
    const vmin = data.min_max[0], vmax = data.min_max[1];
    currentIndex = timestamp.length - 1;
    parsedDataAllFrames = timestamp.map((_, i) => buildFrameData(data, i));
    layerDynamic = vectorCreator(parsedDataAllFrames[currentIndex], vmin, vmax, title, colorbarKey);
    map.addLayer(layerDynamic);
    // Destroy slider if it exists
    if (slider.noUiSlider) { 
        slider.noUiSlider.destroy(); 
        clearInterval(isPlaying); isPlaying = null;
        playBtn.textContent = "▶ Play";
    }
    // Recreate Slider
    noUiSlider.create(slider, {
        start: currentIndex, step: 1,
        range: { min: 0, max: timestamp.length - 1 },
        tooltips: {
            to: value => timestamp[Math.round(value)],
            from: value => timestamp.indexOf(value)
        }
    });
    // Update map by time
    slider.noUiSlider.on('update', (values, handle, unencoded) => {
        currentIndex = Math.round(unencoded[handle]);
        // Update vector canvas
        layerDynamic.options.data = parsedDataAllFrames[currentIndex];
        layerDynamic._redraw();
    });
    // Play/Pause button
    if (!playHandlerAttached) {
        playBtn.addEventListener("click", () => {
            if (isPlaying) {
                clearInterval(isPlaying); isPlaying = null;
                playBtn.textContent = "▶ Play";
            } else {
                currentIndex = parseInt(Math.round(slider.noUiSlider.get()));
                isPlaying = setInterval(() => {
                    currentIndex = (currentIndex + 1) % timestamp.length;
                    slider.noUiSlider.set(currentIndex);
                }, 800);
                playBtn.textContent = "⏸ Pause";
            }
        });
        playHandlerAttached = true;
    }
}

function hideComponent(key) {
    if (key === "stations") {
        stationLayer.clearLayers(); stationLayer = null; 
    } else if (key === "cross_sections") {
        crossSectionLayer.clearLayers(); crossSectionLayer = null;
    }
}

// Click event for the map
function mapPoint(e) {
    const lat = e.latlng.lat.toFixed(6), lng = e.latlng.lng.toFixed(6);
    if (currentMarker) { map.removeLayer(currentMarker); }
    currentMarker = L.marker(e.latlng).addTo(map);
    let html = `
        <div style="display: flex; justify-content: space-between;">
            <div style="padding-left: 10px;">Location:</div>
            <div style="padding-right: 10px;">${lng}, ${lat}</div>
        </div>`;
    if (layerStatic || layerDynamic) {
        const combinedLayer = layerStatic || layerDynamic;
        const fieldName = combinedLayer.columnName;
        const getValue = new Promise(resolve => {
            combinedLayer.once('click', function(e) {
                resolve(e.layer.properties[fieldName] || 'N/A');
            });
        });
        getValue.then(value => {
            html += `
            <div style="display: flex; justify-content: space-between;">
                <div style="padding-left: 10px;">${colorbar_title.textContent}:</div>
                <div style="padding-right: 10px;">${value}</div>
            </div>`;
            infor.innerHTML = html;
        });
    }
    infor.innerHTML = html;
    // Update the height of the info window
    infoPanel.style.height = 'auto';
}

function interpolateValue(location, centroids, power = 5, maxDistance = Infinity) {
    const weights = [], values = [];
    for (const c of centroids){
        const d = turf.distance(
            turf.point([location.lng, location.lat]),
            turf.point([c.lng, c.lat]), {unit: 'meters'}
        );
        if (d > maxDistance || d === 0) continue;
        const w = 1 / Math.pow(d, power);
        weights.push(w); values.push(c.value * w);
    }
    if (weights.length === 0) return null;
    const sumWeughts = weights.reduce((a, b) => a + b, 0);
    const sumValues = values.reduce((a, b) => a + b, 0);
    return Number((sumValues / sumWeughts).toFixed(2));
}

function plotProfile(pointContainer, titleY, titleX='Distance (m)') {
    const subset_dis = 100, interpolatedPoints = [];
    // Convert Lat, Long to x, y
    const originLocation = L.Projection.SphericalMercator.project(
        L.latLng(pointContainer[0].lat, pointContainer[0].lng));
    for (let i = 0; i < pointContainer.length - 1; i++) {
        const p1 = pointContainer[i], p2 = pointContainer[i + 1];
        const pt1 = L.Projection.SphericalMercator.project(L.latLng(p1.lat, p1.lng));
        const pt2 = L.Projection.SphericalMercator.project(L.latLng(p2.lat, p2.lng));
        const dx = pt2.x - pt1.x, dy = pt2.y - pt1.y;
        const segmentDist = Math.sqrt(dx * dx + dy * dy);
        const segments = Math.floor(segmentDist / subset_dis);
        // Add the first point
        const originDx = pt1.x - originLocation.x;
        const originDy = pt1.y - originLocation.y;
        const originDist = Number(Math.sqrt(originDx * originDx + originDy * originDy).toFixed(2));
        interpolatedPoints.push([originDist, p1.value]);
        // Add the intermediate points        
        for (let j = 1; j < segments; j++) {
            const ratio = j / segments;
            const interpX = pt1.x + ratio * dx, interpY = pt1.y + ratio * dy;
            const latlngInterp = L.Projection.SphericalMercator.unproject(L.point(interpX, interpY));
            // Interpolate
            const location = L.latLng(latlngInterp.lat, latlngInterp.lng);
            const interpValue = interpolateValue(location, polygonCentroids);
            // Compute distance
            const originDx1 = interpX - originLocation.x;
            const originDy1 = interpY - originLocation.y;
            const distInterp = Number(Math.sqrt(originDx1 * originDx1 + originDy1 * originDy1).toFixed(2));
            if (interpValue !== null) {
                interpolatedPoints.push([distInterp, interpValue]);
            }
        }
        // Add the last point
        const lastPt = pointContainer[pointContainer.length - 1];
        const lastPtProj = L.Projection.SphericalMercator.project(L.latLng(lastPt.lat, lastPt.lng));
        const lastDx = lastPtProj.x - originLocation.x;
        const lastDy = lastPtProj.y - originLocation.y;
        const lastDist = Number(Math.sqrt(lastDx * lastDx + lastDy * lastDy).toFixed(2));
        interpolatedPoints.push([lastDist, lastPt.value]);
    }
    // Sort by distance
    interpolatedPoints.sort((a, b) => a[0] - b[0]);
    const input = {
        columns: [titleX, titleY], data: interpolatedPoints
    };
    drawChart('', input, titleY, titleX);
    toggleMenu();
}

function mapPath(e) {
    if (!isPath) return;
    // Right-click
    if (e.type === "contextmenu") {
        e.originalEvent.preventDefault(); // Suppress context menu
        if (pointContainer.length < 2) {
            alert("Not enough points selected. Please select at least two points.");
            return;
        }
        // TODO:
        const title = colorbar_title.textContent;
        plotProfile(pointContainer, title);
    }
    // Left-click
    if (e.type === "click" && e.originalEvent.button === 0) {
        // Check which layer selected
        if (clickedInsideLayer) {
            // Add marker
            marker = L.circleMarker(e.latlng, {
                radius: 5, color: 'blue', fillColor: 'cyan', fillOpacity: 0.9
            }).addTo(map);
            selectedMarkers.push(marker);
            // Get selected value
            const value = e.layerProps?.[storedLayer?.columnName] ?? null;
            // Add point
            pointContainer.push({
                lat: e.latlng.lat, lng: e.latlng.lng, value: value
            });
            // Plot line
            const latlngs = pointContainer.map(p => [p.lat, p.lng]);
            if (pathLine) {
                pathLine.setLatLngs(latlngs);
            } else {
                pathLine = L.polyline(latlngs, {
                    color: 'orange', weight: 2, dashArray: '5,5'
                }).addTo(map);
            }
        }
        clickedInsideLayer = false;
    }
}

map.on("click", mapPath);
map.on("contextmenu", mapPath);

function pathQueryReset() {
    // Reset
    selectedMarkers.forEach(m => map.removeLayer(m));
    selectedMarkers = []; pointContainer = [];
    if (pathLine) { map.removeLayer(pathLine); pathLine = null; }
    if (plotWindow.style.display === "flex") { plotWindow.style.display = "none"; }
}

function hideQuery(key) {
    const mapContainer = map.getContainer();
    if (key === "point") {
        queryPoint = false; toggleinfoMenu();
        mapContainer.style.cursor = "grab"; infor.innerHTML = "";
        infoDetails.style.display = "none";
        if (currentMarker) {
            map.removeLayer(currentMarker);
            currentMarker = null;
        }
        map.off('click', mapPoint);
        if (plotWindow.style.display === "flex") { plotWindow.style.display = "none"; }
    } else if (key === "path") {
        queryPath = false; isPath = false;
        map.closeTooltip(hoverTooltip);
        mapContainer.style.cursor = "grab";
        map.off('click', mapPath);
        // Reset
        pathQueryReset();
    }
} 
// Make query for points
function makeQuery(key) {
    const mapContainer = map.getContainer();
    if (key === "point") {
        queryPoint = true;
        mapContainer.style.cursor = "help";
        infoDetails.style.display = "block";
        map.on('click', mapPoint);
        isinfoOpen = false; toggleinfoMenu();
    } else if (key === "path") {
        queryPath = true; isPath = true;
        if (!isPathQuery) {
            alert("This type of map does not support path queries.\nOnly static and dynamic (with single layer) maps are supported.");
            // Deselect checkbox
            if (pathQueryCheckbox.checked) pathQueryCheckbox.checked = false;
            return;
        }
        if (!layerStatic && !layerDynamic) {
            alert("To use this feature, you need to load a layer first.");
            return;
        } else {
            mapContainer.style.cursor = "crosshair";
            pathQueryReset();
        }
    }
}

// Convert value to color
function getColorFromValue(value, vmin, vmax, colorbarKey) {
    if (typeof value !== 'number' || isNaN(value)) {
        return { r: 150, g: 150, b: 150, a: 0 };
    }
    if (vmin === vmax) return { r: 0, g: 0, b: 100, a: 1 };
    // Clamp value
    value = Math.max(vmin, Math.min(vmax, value));
    const t = (value - vmin) / (vmax - vmin);
    let colors;
    if (colorbarKey === "depth") {
        colors = [
            { r: 0,   g: 51,  b: 102 }, // dark blue
            { r: 0,   g: 119, b: 190 }, // light blue
            { r: 160, g: 216, b: 239 }  // very light blue
        ];
    }else if (colorbarKey === "velocity") {
        colors = [
            { r: 255, g: 255, b: 255 },  // White
            { r: 255, g: 255, b: 85  },  // Yellow
            { r: 255, g: 4,   b: 0   }   // Red
        ];
    }else {
        colors = [
            { r: 0,   g: 0,   b: 255 }, // blue
            { r: 255, g: 165, b: 0   }, // orange
            { r: 255, g: 0,   b: 0   }  // red
        ];
    }
    const binCount = colors.length - 1;
    const scaledT = t * binCount;
    const lower = Math.floor(scaledT);
    const upper = Math.min(colors.length - 1, lower + 1);
    const frac = scaledT - lower;
    const c1 = colors[lower];
    const c2 = colors[upper];
    const r = Math.round(c1.r + (c2.r - c1.r) * frac);
    const g = Math.round(c1.g + (c2.g - c1.g) * frac);
    const b = Math.round(c1.b + (c2.b - c1.b) * frac);
    return { r, g, b, a: 1 };
}

// Update color for colorbar
function updateColorbar(min, max, title, colorbarKey) {
    colorbar_title.textContent = title;
    const midValue = (min + max) / 2;
    const minColor = getColorFromValue(min, min, max, colorbarKey);
    const midColor = getColorFromValue(midValue, min, max, colorbarKey);
    const maxColor = getColorFromValue(max, min, max, colorbarKey);
    // Update gradient
    const gradient = `linear-gradient(to top,
        rgb(${minColor.r}, ${minColor.g}, ${minColor.b}) 0%,
        rgb(${midColor.r}, ${midColor.g}, ${midColor.b}) 50%,
        rgb(${maxColor.r}, ${maxColor.g}, ${maxColor.b}) 100%
    )`;
    colorbar_color.style.background = gradient;
    // Update 5 labels
    const labels = document.getElementById("colorbar-labels").children;
    for (let i = 0; i < 5; i++) {
        const percent = i / 4; // 0.0, 0.25, ..., 1.0
        const value = min + (max - min) * (1 - percent); // Top to bottom
        labels[i].textContent = value.toFixed(2);
    }
}

// Create dynamic layer
function layerCreator(data, columnName, vmin, vmax, filename, title, colorbarKey) {
    if (layerStatic && map.hasLayer(layerStatic)) {
        map.removeLayer(layerStatic); layerStatic = null;
    }
    if (layerDynamic && map.hasLayer(layerDynamic)) {
        map.removeLayer(layerDynamic); layerDynamic = null;
    }
    const layer = L.vectorGrid.slicer(data, {
        rendererFactory: L.canvas.tile, vectorTileLayerStyles: {
            sliced: function(properties) {
                const value = properties[columnName];
                const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey);
                return {
                    fill: true, fillColor: `rgb(${r},${g},${b})`, fillOpacity: a,
                    weight: 0, opacity: 1
                };
            },
        }, interactive: true, maxZoom: 18, getFeatureId: f => f.properties.index
    });
    let txt = '';
    if (filename.includes('multilayers')) {
        txt = `<br>Select object to see values in each layer`;
        isPathQuery = false;
    } else {
        // Assign value to use later
        isPathQuery = true; polygonCentroids = [];
        polygonCentroids = data.features.map(f => {
            const center = turf.centroid(f).geometry.coordinates;
            return {
                lat: center[1], lng: center[0],
                value: f.properties[columnName],
            };
        });
    }
    // Assign column name to use later
    layer.columnName = columnName; storedLayer = layer;
    const hoverTooltip = L.tooltip({ direction: 'top', sticky: true });
    layer.on('mouseover', function(e) {
        if (isPlaying) return;
        const props = e.layer.properties;
        const value = props[columnName];
        // Show tooltip
        const html = `
            <div style="text-align: center;">
                <b>${title}:</b> ${value ?? 'N/A'}${txt}
            </div>
        `;
        hoverTooltip.setContent(html).setLatLng(e.latlng)
        map.openTooltip(hoverTooltip);
    }).on('mouseout', function(e) {
        map.closeTooltip(hoverTooltip);
        layer.resetFeatureStyle(e.layer._id);
    });
    // Add click event to the layer
    layer.on('click', function(e) {
        clickedInsideLayer = true;
        const feature = e.layer;
        const props = feature.properties;
        if (isPath){
            mapPath({
                ...e, layerProps: props
            });
        }
        if (filename.includes('multilayers')) {
            // Get index of the feature
            const selectedFeatureId = props.index;
            // Highlight feature 
            layer.resetFeatureStyle(feature.leaflet_id);
            feature.setStyle({ fillColor: 'red', color: 'yellow', fillOpacity: 1 });
            // Load data to plot
            plotMultilayer(selectedFeatureId, filename, title);
        }
    });
    // Adjust Colorbar Control
    updateColorbar(vmin, vmax, title, colorbarKey);
    return layer;
}

async function plotMultilayer(id, filename, title) {
    startLoading();
    try {
        const response = await fetch('/select_polygon', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({filename: filename, id: id})});
        const data = await response.json();
        if (data.status === "ok") {
            drawChart(filename, data.content, title);
            toggleMenu();
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    showLeafletMap();
}

// Update dynamic layer
function updateMapByTime(data, layer, time, index, vmin, vmax, colorbarKey) {
    const columnName = time[index];
    if (!layer || !map.hasLayer(layer)) return;
    data.features.forEach(f => {
        const value = f.properties[columnName];
        const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey);
        const style = {
            fill: true, fillColor: `rgb(${r},${g},${b})`,
            fillOpacity: a, weight: 0, opacity: 1
        };
        const id = f.properties.index;
        layer.setFeatureStyle(id, style);
    });
    layer.columnName = columnName;
}

// Get min and max values from GeoJSON
function getMinMaxFromGeoJSON(data, columns) {
    let globalMin = Infinity; globalMax = -Infinity;
    data.features.forEach(feature => {
        columns.forEach(field => {
            const value = feature.properties[field];
            if (typeof value === "number" && !isNaN(value)) {
                if (value < globalMin) globalMin = value;
                if (value > globalMax) globalMax = value;
            } else if (typeof value === 'string') {
                const temp = value.replace(/[()]/g, '');
                const parts = temp.split(',').map(s => parseFloat(s.trim()));
                const c = parts[2];
                if (typeof c === 'number') {
                    if (c < globalMin) globalMin = c;
                    if (c > globalMax) globalMax = c;
                }
            }
        });
    });
    if (!isFinite(globalMin)) globalMin = null;
    if (!isFinite(globalMax)) globalMax = null;
    return { min: globalMin, max: globalMax };
}

// Init dynamic map
function initDynamicMap(data, filename, title, colorbarKey) {
    timeControl.style.display = "flex"; // Show time slider
    // Get column name
    const allColumns = Object.keys(data.features[0].properties);
    const timestamp = allColumns.filter(k => !k.includes("index"));
    // Get min and max values
    const { min: vmin, max: vmax } = getMinMaxFromGeoJSON(data, timestamp);
    currentIndex = timestamp.length - 1;
    // Destroy slider if it exists
    if (slider.noUiSlider) { 
        slider.noUiSlider.destroy();
        clearInterval(isPlaying); isPlaying = null;
        playBtn.textContent = "▶ Play";
    }
    layerDynamic = layerCreator(data, timestamp[currentIndex], vmin, vmax, filename, title, colorbarKey);
    map.addLayer(layerDynamic);
    // Recreate Slider
    noUiSlider.create(slider, {
        start: currentIndex, step: 1,
        range: { min: 0, max: timestamp.length - 1 },
        tooltips: {
            to: value => timestamp[Math.round(value)],
            from: value => timestamp.indexOf(value)
        }
    });
    // Update map by time
    slider.noUiSlider.on('update', (values, handle, unencoded) => {
        currentIndex = Math.round(unencoded[handle]);
        updateMapByTime(data, layerDynamic, timestamp, currentIndex, vmin, vmax, colorbarKey);
    });
    // Play/Pause button
    if (!playHandlerAttached) {
        playBtn.addEventListener("click", () => {
            if (isPlaying) {
                clearInterval(isPlaying); isPlaying = null;
                playBtn.textContent = "▶ Play";
            } else {
                currentIndex = parseInt(Math.floor(slider.noUiSlider.get()));
                isPlaying = setInterval(() => {
                    currentIndex = (currentIndex + 1) % timestamp.length;
                    slider.noUiSlider.set(currentIndex);
                }, 800);
                playBtn.textContent = "⏸ Pause";
            }
        });
        playHandlerAttached = true;
    }
    // // Export video
    // exportVideoBtn.addEventListener("click", async () => {
    //     playBtn.disabled = true;
    //     exportVideoBtn.disabled = true;
    //     await exportAnimationToVideo({
    //         data, layer: layerDynamic, timestamps: timestamp, vmin, vmax,
    //         fps: 5, quality: 0.95
    //     });
    //     playBtn.disabled = false;
    //     exportVideoBtn.disabled = false;
    // });
}

// Plot dynamic map
function plotMap(data, filename, title, colorbarKey) {
    if (filename.includes("static")) {
        isPlaying = null;
        // Plot static map
        timeControl.style.display = "none"; // Hide time slider
        // Get the min and max values of the data
        const values = data.features.map(f => f.properties.value)
                        .filter(v => typeof v === 'number' && !isNaN(v));
        const vmin = Math.min(...values);
        const vmax = Math.max(...values);
        layerStatic = layerCreator(data, "value", vmin, vmax, filename, title, colorbarKey);
        map.addLayer(layerStatic);
    }else{
        // Plot dynamic map
        initDynamicMap(data, filename, title, colorbarKey);
    }
}

function openPlotChart(key='NaN') {
    const currentDisplay = window.getComputedStyle(plotWindow).display;
    if (currentDisplay === "none") { plotWindow.style.display = "flex";}
    if (key === 'NaN') { plotWindow.style.display = "none"; }
    toggleMenu();
}

// Change object to plot
function changeData(value) {
    const { filename, data, title } = globalChartData;
    if (data) { drawChart(filename, data, title, undefined, value);
    } else { alert("No data available to update chart.");}
}

// Draw the chart using Plotly
function drawChart(filename, data, titleY, titleX='Time', selectedColumnName = "All") {
    const cols = data.columns, rows = data.data;
    // alert(cols);
    const x = rows.map(r => r[0]);
    const traces = [];
    const validColumns = [];
    const columnIndexMap = {};
    for (let i = 1; i < cols.length; i++) {
        const y = rows.map(r => r[i]);
        const hasValid = y.some(val => val !== null && !isNaN(val));
        if (hasValid) {
            validColumns.push(i);
            columnIndexMap[cols[i]] = i;
        };
    }
    selectObject.innerHTML = '';
    if (validColumns.length > 1) {
        // Add "All" option
        const allOption = document.createElement('option');
        allOption.value = "All";
        allOption.textContent = "All";
        if (selectedColumnName === "All") { allOption.selected = true; }
        selectObject.appendChild(allOption);
    }
    // Add other options
    validColumns.forEach(i => {
        const colName = cols[i];
        const opt = document.createElement('option');
        opt.value = colName;
        opt.textContent = colName;
        if (colName === selectedColumnName) { opt.selected = true; }
        selectObject.appendChild(opt);
    })
    // Update global variable
    globalChartData = { filename, data, titleY, validColumns, columnIndexMap };
    let drawColumns;
    if (selectedColumnName === "All" || !selectedColumnName) {
        drawColumns = validColumns;
    } else {
        const selectedIndex = columnIndexMap[selectedColumnName];
        drawColumns = [selectedIndex];
    }
    let traceIndex = 0;
    const n = drawColumns.length;
    function interpolateJet(t) {
        const jetColors = [
            [0.0, [0, 0, 128]], [0.35, [0, 255, 255]],
            [0.5, [0, 255, 0]], [0.75, [255, 255, 0]], [1.0, [255, 0, 0]]
        ];
        for (let i = 0; i < jetColors.length - 1; i++) {
            const [t1, c1] = jetColors[i];
            const [t2, c2] = jetColors[i + 1];
            if (t >= t1 && t <= t2) {
                const f = (t - t1) / (t2 - t1);
                const r = Math.round(c1[0] + (c2[0] - c1[0]) * f);
                const g = Math.round(c1[1] + (c2[1] - c1[1]) * f);
                const b = Math.round(c1[2] + (c2[2] - c1[2]) * f);
                return `rgb(${r},${g},${b})`;
            }
        }
        return `rgb(255,0,0)`;
    }
    for (const i of drawColumns) {
        const y = rows.map(r => r[i]);
        const t = n <= 1 ? 0 : traceIndex / (n - 1);
        const color = interpolateJet(1-t);
        traces.push({
        x: x, y: y, name: cols[i],
        type: 'scatter', mode: 'lines', line: { color: color }
      });
      traceIndex++;
    }
    const layout = {
        margin: {l: 60, r: 0, t: 5, b: 40},
        xaxis: {
            title:{text: titleX, font: { size: 16, weight: 'bold' }},
            showgrid: true, gridcolor: '#ccc' 
        },
        yaxis: {
            title:{text: titleY, font: { size: 13, weight: 'bold' }}, 
            showgrid: true, gridcolor: '#ccc'
        },
    };
    Plotly.purge(chartDiv); // Clear the chart
    Plotly.newPlot('myChart', traces, layout, {responsive: true});
    Plotly.Plots.resize(chartDiv); // Resize the chart
    openPlotChart(''); // Show the chart
}

// Export chart data to new tab as CSV format
function viewData() {
    const data = chartDiv.data?.[0];
    if (!data) {
        alert("No data to view.");
        return;
    }
    // Get the y values
    const numTraces = chartDiv.data.length;
    const title = chartDiv.layout?.title?.text || "Chart";
    const titleText = typeof title === "string"
        ? (title.includes(':') ? title.split(':')[1].trim() : title)
        : "Chart";
    const titleY = chartDiv.layout?.yaxis?.title?.text || "Value";
    let csvHeader = chartDiv.layout?.xaxis?.title?.text || 'Unknown';
    for (let i = 0; i < numTraces; i++) {
        const traceName = chartDiv.data[i].name || `${titleText}_${titleY}_${i}`;
        csvHeader += `,${traceName}`;
    }
    let csvContent = `${csvHeader}\n`;
    for (let i = 0; i < chartDiv.data[0].x.length; i++) {
        let row = `${chartDiv.data[0].x[i]}`;
        for (let j = 0; j < numTraces; j++) {
            row += `,${chartDiv.data[j].y[i]}`;
        }
        csvContent += `${row}\n`;
    }
    const newWindow = window.open("", "_blank");
    if (newWindow) {
        const doc = newWindow.document;
        doc.title = titleY.split(' (')[0];
        const pre = doc.createElement("pre");
        pre.style.fontFamily = "monospace";
        pre.style.whiteSpace = "pre-wrap";
        pre.textContent = csvContent;
        const body = doc.body || doc.createElement("body");
        body.appendChild(pre);
        doc.body = body;
    }else {
        alert("Pop-up blocked. Please allow popups for this site.");
    }
}

// Save to Excel
function saveToExcel() {
    const data = chartDiv.data?.[0];
    if (!data) {
        alert("No data to save.");
        return;
    }
    // Get the y values
    const numTraces = chartDiv.data.length;
    const title = chartDiv.layout?.title?.text || "Chart";
    const titleText = typeof title === "string"
        ? (title.includes(':') ? title.split(':')[1].trim() : title): "Chart";
    const titleY = chartDiv.layout?.yaxis?.title?.text || "Value";
    // Prepare the data
    const title_ = chartDiv.layout?.xaxis?.title?.text || 'Unknown';
    const headers = [title_];
    for (let i = 0; i < numTraces; i++) {
        const traceName = chartDiv.data[i].name || `${titleText}_${titleY}_${i}`;
        headers.push(traceName);
    }
    const table = [headers];
    const numPoints = chartDiv.data[0].x.length;
    for (let i = 0; i < numPoints; i++) {
        const row = [chartDiv.data[0].x[i]];
        for (let j = 0; j < numTraces; j++) {
            row.push(chartDiv.data[j].y[i]);
        }
        table.push(row);
    }
    // Create workbook and worksheet
    const worksheet = XLSX.utils.aoa_to_sheet(table);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "ChartData");
    // Download the Excel file
    XLSX.writeFile(workbook, `${titleY.split(' (')[0]}.xlsx`);
}

async function initiateLayers() {
    startLoading();
    try {
        const response = await fetch('/process_layer', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({'key':'init_layers'})});
        const data = await response.json();
        if (data.status === "ok") {
            // Add options to the below layer object
            belowLayer.innerHTML = '';
            // Add hint to the velocity object
            const hint_below = document.createElement('option');
            hint_below.value = ''; hint_below.selected = true;
            hint_below.textContent = '-- Select a type --'; 
            belowLayer.add(hint_below);
            // Add options
            data.content.below.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                belowLayer.add(option);
            });
            // Add options to the above layer object
            aboveLayer.innerHTML = '';
            // Add hint to the velocity object
            const hint_above = document.createElement('option');
            hint_above.value = ''; hint_above.selected = true;
            hint_above.textContent = '-- Select a type --'; 
            aboveLayer.add(hint_above);
            // Add options
            data.content.above.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                aboveLayer.add(option);
            });
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    // Hide the spinner and show the map
    showLeafletMap();
}

async function plotLayers() {
    const below_value = belowLayer.value, above_value = aboveLayer.value;
    if (belowLayer.selectedIndex === 0 || aboveLayer.selectedIndex === 0){
        alert('Please select below and above layers.');
        return;
    }
    // Process data
    startLoading();
    try {
        const response = await fetch('/process_layer', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({'key':'process_layers',
            'below_layer': below_value, 'above_layer': above_value})});
        const data = await response.json();
        if (data.status === "ok") {
            // const temp = ['Temperature', 'Salinity', 'Contaminant'];
            const depth = ['Depth Water Level', 'Water Surface Level'];
            const title = belowLayer.value, filename = '';
            let colorbarKey = '';
            if (depth.includes(belowLayer.value)) {
                colorbarKey = 'depth';
            }
            // Remove existing layers
            if (layerBelow && map.hasLayer(layerBelow)) {
                map.removeLayer(layerBelow); layerBelow = null;
            }
            if (layerAbove && map.hasLayer(layerAbove)) {
                map.removeLayer(layerAbove); layerAbove = null;
            }
            const data_below = data.content.below;
            const data_above = data.content.above;
            timeControl.style.display = "flex"; // Show time slider
            // Destroy slider if it exists
            if (slider.noUiSlider) { 
                slider.noUiSlider.destroy();
                clearInterval(isPlaying); isPlaying = null;
                playBtn.textContent = "▶ Play";
            }
            const timestamp = data_above.time;
            currentIndex = timestamp.length - 1;
            // Process below layer
            const { min: vmin_below, max: vmax_below } = getMinMaxFromGeoJSON(data_below, timestamp);
            layerBelow = layerCreator(data_below, timestamp[currentIndex], vmin_below, vmax_below, filename, title, colorbarKey);
            map.addLayer(layerBelow);
            // Process above layer
            const vmin_above = data_above.min_max[0], vmax_above = data_above.min_max[1];
            parsedDataAllFrames = timestamp.map((_, i) => buildFrameData(data_above, i));
            layerAbove = vectorCreator(parsedDataAllFrames[currentIndex], vmin_above, vmax_above, title, colorbarKey, '');
            map.addLayer(layerAbove);
            // Recreate Slider
            noUiSlider.create(slider, {
                start: currentIndex, step: 1,
                range: { min: 0, max: timestamp.length - 1 },
                tooltips: {
                    to: value => timestamp[Math.round(value)],
                    from: value => timestamp.indexOf(value)
                }
            });
            // Update map by time
            slider.noUiSlider.on('update', (values, handle, unencoded) => {
                currentIndex = Math.round(unencoded[handle]);
                // Update vector canvas
                updateMapByTime(data_below, layerBelow, timestamp, currentIndex, vmin_below, vmax_below, colorbarKey);
                layerAbove.options.data = parsedDataAllFrames[currentIndex];
                layerAbove._redraw();
            });
            // Play/Pause button
            if (!playHandlerAttached) {
                playBtn.addEventListener("click", () => {
                    if (isPlaying) {
                        clearInterval(isPlaying); isPlaying = null;
                        playBtn.textContent = "▶ Play";
                    } else {
                        currentIndex = Math.round(slider.noUiSlider.get());
                        isPlaying = setInterval(() => {
                            currentIndex = (currentIndex + 1) % timestamp.length;
                            slider.noUiSlider.set(currentIndex);
                        }, 800);
                        playBtn.textContent = "⏸ Pause";
                    }
                });
                playHandlerAttached = true;
            }
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    // Hide the spinner and show the map
    showLeafletMap(); toggleinfoMenu();
}


// Load default map
// loadData('temperature_multilayers.geojson', 'temperature_multilayers', 'Temperature (°C)', 'temperature');
loadData('depth_static.geojson', 'depth', 'Depth (m)');
// Add layers for velocity and layers
initiateVelocities();
initiateLayers();

// // Export video
// async function exportAnimationToVideo({ data, layer, timestamps, vmin, vmax,
//     fps = 5, quality = 0.95 }) {
//     const canvas = document.querySelector("canvas");
//     const video = new Whammy.Video(fps);
//     const progressContainer = document.getElementById("export-progress-container");
//     const progressBar = document.getElementById("export-progress-bar");
//     progressContainer.style.display = "block";
//     progressBar.style.width = "0%";
//     for (let i = 0; i < timestamps.length; i++) {
//         updateMapByTime(data, layer, timestamps, i, vmin, vmax);
//         await new Promise(resolve => setTimeout(resolve, 300)); // chờ render
//         const canvas = await html2canvas(leaflet_map, {
//             useCORS: true
//         });
//         const frame = canvas.toDataURL("image/webp", quality);
//         video.add(frame);
//         const percent = ((i + 1) / timestamps.length) * 100;
//         progressBar.style.width = `${percent}%`;
//     }
//     const output = await new Promise(resolve => {
//         video.compile(false, blob => resolve(blob));
//     });
//     const url = URL.createObjectURL(output);
//     const a = document.createElement("a");
//     a.href = url;
//     a.download = "animation.webm";
//     a.click();
//     progressContainer.style.display = "none";
//     progressBar.style.width = "0%";
//     console.log("🎬 Export complete!");
// }