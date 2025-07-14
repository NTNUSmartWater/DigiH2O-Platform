let stationLayer = null, crossSectionLayer = null, isOpen = true; 
let isDragging_infor = false, offsetX_infor = 0, offsetY_infor = 0;
let isDragging_plot = false, offsetX_plot = 0, offsetY_plot = 0;
let queryPoint = true, queryPath = true, currentMarker = null;
let layerStatic = null, layerDynamic = null, isPlaying = null; 
let playHandlerAttached = false, isinfoOpen = true, currentIndex = 0;
let colorbarControl = L.control({ position: 'topright' });
CENTER = [62.476969, 6.471598]; ZOOM = 13; 
const chartDiv = document.getElementById('myChart');
const content = document.getElementById("infoContent");
const menu = document.getElementById("offCanvasMenu");
const button = document.getElementById('menuBtn');
const loading = document.getElementById('loadingOverlay');
const iframe = document.getElementById('iframe_map');
const leaflet_map = document.getElementById('leaflet_map');
const arrow = document.getElementById("arrowToggle");
const infoDetails = document.getElementById("infoDetails");
const infoPanel = document.getElementById("infoPanel");
const infoPanelHeader = document.getElementById("infoPanelHeader")
const slider = document.getElementById("time-slider");
const playBtn = document.getElementById("play-btn");
const timeControl = document.getElementById("time-controls");
const exportVideoBtn = document.getElementById("export-video-btn");
let colorbar_title = document.getElementById("colorbar-title");
let colorbar_min = document.getElementById("colorbar-min");
let colorbar_max = document.getElementById("colorbar-max");
let colorbar_color = document.getElementById("colorbar-gradient");
let infor = document.getElementById("infoDetailsContent");
let infoHeader = document.getElementById("infoHeader");
let infoWindow = document.getElementById("infoWindow");
let plotHeader = document.getElementById("plotHeader");
let plotWindow = document.getElementById("plotWindow");


// Convert value to color
function getColorFromValue(value, vmin, vmax) {
    if (typeof value !== 'number' || isNaN(value)) {
        return { r: 150, g: 150, b: 150, a: 0 };
    }
    if (vmin === vmax) return { r: 0, g: 0, b: 100, a: 1 };
    // Clamp value
    value = Math.max(vmin, Math.min(vmax, value));
    const t = (value - vmin) / (vmax - vmin);
    // Map value to color: blue green
    const r = 0;
    const g = Math.round(255 * t);
    const b = Math.round(255 * (1 - t));
    return { r, g, b, a: 1 };
}

// Show spinner when loading
function startLoading() {
    loading.style.display = 'flex';
    iframe.style.display = 'none';
    leaflet_map.style.display = 'none';
}

function showLeafletMap() {
    leaflet_map.style.display = "block";
    iframe.style.display = "none";
    loading.style.display = "none";
}
function showIframeMap() {
    leaflet_map.style.display = "none";
    iframe.style.display = "block";
    loading.style.display = "block";
}

// Generate the map
showLeafletMap();
var map = L.map('leaflet_map', {center:CENTER, zoom: ZOOM, zoomControl: false});
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}').addTo(map);        
// Add scale bar
L.control.scale({
    position: 'bottomright', imperial: false, metric: true, maxWidth: 200
}).addTo(map);
// Move the control to the top right corner
const scaleElem = document.querySelector('.leaflet-control-scale');
document.getElementById('right-side-controls').appendChild(scaleElem);

document.addEventListener('click', function(event) {
    // Hide the main menu and info menu if user clicks outside of it
    if (menu && button) {
        const isClickedInsideMenu = menu.contains(event.target) || button.contains(event.target);
        if (!isClickedInsideMenu && isOpen) {toggleMenu();}
    }
    if (!queryPoint){return;}
    if (infoPanel && infoPanelHeader) {
        const isClickedInsideInfo = infoPanel.contains(event.target);
        const currentHeight = parseFloat(window.getComputedStyle(infoPanel).height);
        const isInfoOpen = currentHeight > 35;
        if (!isClickedInsideInfo && isInfoOpen) {toggleinfoMenu();}
    }
})

// Function to toggle the menu
function toggleMenu() {
    menu.style.width = isOpen ? "0" : "250px";
    isOpen = !isOpen;    
}

function toggleinfoMenu() {
    if (isinfoOpen) {
        infoPanel.style.height = "35px";
        arrow.textContent = "▼";
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
        submenu.classList.toggle('open');
        this.classList.toggle('active');
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
async function loadData(filename, key, title='') {
    // Show spinner
    startLoading();
    try {
        const response = await fetch('/process_data', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({data_filename: filename, key: key})});
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
                                iconSize: [30, 30],
                                popupAnchor: [1, -34],
                            });
                            const marker = L.marker(latlng, {icon: customIcon});
                            const id = feature.properties.name || 'Unknown';
                            // Add tooltip
                            marker.bindTooltip(id, {
                                permanent: false, direction: 'top', offset: [0, 0]
                            });
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
                drawChart(data.content, title);
            } else if (filename.includes("velocity")){
                // Plot a vector map
                plotVectorMap(data.content, filename, title);
            } else {
                // Plot a 2D map
                plotMap(data.content, filename, title);            
            }
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    // Hide the spinner and show the map
    loading.style.display = "none";
    showLeafletMap();
}

function getMinMaxFromGeoJSON_Vector(data, columns) {
    let globalMin = Infinity, globalMax = -Infinity;
    data.features.forEach(feature => {
        columns.forEach(field => {
            let value = feature.properties[field];
            if (typeof value === 'string') {
                // Convert string to number or array
                value = JSON.parse(value.replace(/[()]/g, '[').replace(/,/g, ','));
            }
            const c = value[2];
            if (typeof c === 'number') {
                if (c < globalMin) globalMin = c;
                if (c > globalMax) globalMax = c;
            }
        });
    });
    if (!isFinite(globalMin)) globalMin = null;
    if (!isFinite(globalMax)) globalMax = null;
    return { min: globalMin, max: globalMax };
}

function buildFrameData(data, index) {
    
}

function getColorFromC(c, vmin, vmax) {
    const norm = Math.max(0, Math.min(1, (c - vmin) / (vmax - vmin)));
    const red = Math.round(255 * norm);
    const blue = 255 - red;
    return `rgb(${red},0,${blue})`;
}
function vectorCreator() {
    if (layerStatic && map.hasLayer(layerStatic)) {
        map.removeLayer(layerStatic); layerStatic = null;
    };
    if (layerDynamic && map.hasLayer(layerDynamic)) {
        map.removeLayer(layerDynamic); layerDynamic = null;
    };
    const layer = new L.CanvasLayer({
        data: buildFrameData(data, index),
        drawLayer: function() {
            const ctx = this._ctx;
            const map = this._map;
            const scale = 10;
            const data = this.options.data;
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            data.forEach(pt => {
                const latlng = L.latLng(pt.y, pt.x);
                const p = map.latLngToContainerPoint(latlng);
                const dx = pt.a * scale;
                const dy = -pt.b * scale;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(p.x + dx, p.y + dy);
                ctx.strokeStyle = getColorFromC(pt.c, vmin, vmax);
                ctx.lineWidth = 1;
                ctx.stroke();
            });
        }
    });
    return layer;
}



function plotVectorMap(data, filename, title) {
    timeControl.style.display = "flex"; // Show time slider
    // Get column name
    const timestamp = Object.keys(data.features[0].properties);
    // Get min and max values
    const { min: vmin, max: vmax } = getMinMaxFromGeoJSON_Vector(data, timestamp);
    alert(vmin + " " + vmax);
    currentIndex = timestamp.length - 1;
    // Destroy slider if it exists
    if (slider.noUiSlider) { 
        slider.noUiSlider.destroy();
        clearInterval(isPlaying); isPlaying = null;
        playBtn.textContent = "▶ Play";
    }
    layerDynamic = vectorCreator();
    // Recreate Slider
    noUiSlider.create(slider, {
        start: currentIndex, step: 1,
        range: { min: 0, max: timestamp.length - 1 },
        tooltips: {
            to: value => timestamp[Math.floor(value)],
            from: value => timestamp.indexOf(value)
        }
    });
    // Update map by time
    slider.noUiSlider.on('update', (values, handle, unencoded) => {
        if (isPlaying) return;
        currentIndex = Math.floor(unencoded[handle]);
        layerDynamic.options.data = buildFrameData(data, timestamp[currentIndex]);
        layerDynamic.drawLayer();
    });
    // Play/Pause button
    if (!playHandlerAttached) {
        playBtn.addEventListener("click", () => {
            if (isPlaying) {
                clearInterval(isPlaying); isPlaying = null;
                playBtn.textContent = "▶ Play";
            } else {
                currentIndex = Math.floor(slider.noUiSlider.get());
                isPlaying = setInterval(() => {
                    currentIndex = (currentIndex + 1) % timestamp.length;
                    slider.noUiSlider.set(currentIndex);
                    updateMapByTime(data, layerDynamic, timestamp, currentIndex, vmin, vmax);
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
    const lat = e.latlng.lat.toFixed(6);
    const lng = e.latlng.lng.toFixed(6);
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

function hideQuery(key) {
    const mapContainer = map.getContainer();
    if (key === "point") {
        toggleinfoMenu();
        mapContainer.style.cursor = "grab"; infor.innerHTML = "";
        infoDetails.style.display = "none";
        if (currentMarker) {
            map.removeLayer(currentMarker);
            currentMarker = null;
        }
        map.off('click', mapPoint);
        queryPoint = !queryPoint;
    } else if (key === "path") {




        crossSectionLayer.clearLayers(); crossSectionLayer = null;
    }
} 
// Make query for points
function makeQuery(key) {
    const mapContainer = map.getContainer();
    if (key === "point") {
        if (queryPoint){
            mapContainer.style.cursor = "help";
            infoDetails.style.display = "block";
            map.on('click', mapPoint);
            isinfoOpen = false; toggleinfoMenu();
            queryPoint = !queryPoint;
        }
    } else if (key === "path") {
        if (queryPath){
            mapContainer.style.cursor = "crosshair";
            
            
            
            
            
            queryPath = !queryPath;
        } 
    }
}

// Update color for colorbar
function updateColorbar(min, max, title) {
    colorbar_title.textContent = title;
    colorbar_min.textContent = min.toFixed(2);
    colorbar_max.textContent = max.toFixed(2);
    const midValue = (min + max) / 2;
    const minColor = getColorFromValue(min, min, max);
    const midColor = getColorFromValue(midValue, min, max);
    const maxColor = getColorFromValue(max, min, max);
    const gradient = `linear-gradient(to top,
        rgb(${minColor.r}, ${minColor.g}, ${minColor.b}) 0%,
        rgb(${midColor.r}, ${midColor.g}, ${midColor.b}) 50%,
        rgb(${maxColor.r}, ${maxColor.g}, ${maxColor.b}) 100%
    )`;
    colorbar_color.style.background = gradient;
}

// Get min and max values from geojson
function getMinMaxFromGeoJSON(data, columns) {
    let globalMin = Infinity; globalMax = -Infinity;
    data.features.forEach(feature => {
        columns.forEach(field => {
            const value = feature.properties[field];
            if (typeof value === "number" && !isNaN(value)) {
                if (value < globalMin) globalMin = value;
                if (value > globalMax) globalMax = value;
            }
        });
    });
    if (!isFinite(globalMin)) globalMin = null;
    if (!isFinite(globalMax)) globalMax = null;
    return { min: globalMin, max: globalMax };
}

// Create dynamic layer
function layerCreator(data, columnName, vmin, vmax, title, filename) {
    if (layerStatic && map.hasLayer(layerStatic)) {
        map.removeLayer(layerStatic); layerStatic = null;
    };
    if (layerDynamic && map.hasLayer(layerDynamic)) {
        map.removeLayer(layerDynamic); layerDynamic = null;
    };
    const layer = L.vectorGrid.slicer(data, {
        rendererFactory: L.canvas.tile, vectorTileLayerStyles: {
            sliced: function(properties) {
                const value = properties[columnName];
                const { r, g, b, a } = getColorFromValue(value, vmin, vmax);
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
    }
    // Assign column name to use later
    layer.columnName = columnName;
    map.addLayer(layer);
    const hoverTooltip = L.tooltip({ direction: 'top', sticky: true });
    layer.on('mouseover', function(e) {
        if (isPlaying) return;
        const props = e.layer.properties;
        const value = props[layer.columnName];
        // Show tooltip
        const html = `
        <div style="text-align: center;">
            <b>Value:</b> ${value ?? 'N/A'}${txt}
        </div>
        `;
        hoverTooltip.setContent(html).setLatLng(e.latlng)
        map.openTooltip(hoverTooltip);
    }).on('mouseout', function(e) {
        map.closeTooltip(hoverTooltip);
        layer.resetFeatureStyle(e.layer._id);
    });
    // Adjust Colorbar Control
    updateColorbar(vmin, vmax, title);
    if (filename.includes('multilayers')) {
        // Add click event to the layer
        layer.on('click', function(e) {
            const feature = e.layer;
            // Get index of the feature
            const selectedFeatureId = feature.properties.index;
            // Highlight feature 
            layer.resetFeatureStyle(feature.leaflet_id);
            feature.setStyle({ fillColor: 'red', color: 'yellow', fillOpacity: 1 });
            // Load data to plot
            plotMultilayer(selectedFeatureId, title, filename);
        });
    }
    return layer;
}

async function plotMultilayer(id, title, filename) {
    startLoading();
    try {
        const response = await fetch('/select_polygon', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({filename: filename, id: id})});
        const data = await response.json();
        if (data.status === "ok") {
            drawChart(data.content, title);
            toggleMenu();
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    loading.style.display = "none";
    showLeafletMap();
}

// Update dynamic layer
function updateMapByTime(data, layer, time, index, vmin, vmax) {
    const columnName = time[index];
    if (!layer || !map.hasLayer(layer)) return;
    data.features.forEach(f => {
        const value = f.properties[columnName];
        const { r, g, b, a } = getColorFromValue(value, vmin, vmax);
        const style = {
            fill: true, fillColor: `rgb(${r},${g},${b})`,
            fillOpacity: a, weight: 0, opacity: 1
        };
        const id = f.properties.index;
        layer.setFeatureStyle(id, style);
    });
    layer.columnName = columnName;
}

// Init dynamic map
function initDynamicMap(data, title, filename) {
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
    layerDynamic = layerCreator(data, timestamp[currentIndex], vmin, vmax, title, filename);
    // Recreate Slider
    noUiSlider.create(slider, {
        start: currentIndex, step: 1,
        range: { min: 0, max: timestamp.length - 1 },
        tooltips: {
            to: value => timestamp[Math.floor(value)],
            from: value => timestamp.indexOf(value)
        }
    });
    // Update map by time
    slider.noUiSlider.on('update', (values, handle, unencoded) => {
        if (isPlaying) return;
        currentIndex = Math.floor(unencoded[handle]);
        updateMapByTime(data, layerDynamic, timestamp, currentIndex, vmin, vmax);
    });
    // Play/Pause button
    if (!playHandlerAttached) {
        playBtn.addEventListener("click", () => {
            if (isPlaying) {
                clearInterval(isPlaying); isPlaying = null;
                playBtn.textContent = "▶ Play";
            } else {
                currentIndex = Math.floor(slider.noUiSlider.get());
                isPlaying = setInterval(() => {
                    currentIndex = (currentIndex + 1) % timestamp.length;
                    slider.noUiSlider.set(currentIndex);
                    updateMapByTime(data, layerDynamic, timestamp, currentIndex, vmin, vmax);
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
function plotMap(data, filename, title) {
    if (filename.includes("static")) {
        isPlaying = null;
        // Plot static map
        timeControl.style.display = "none"; // Hide time slider
        // Get the min and max values of the data
        const values = data.features.map(f => f.properties.value)
                        .filter(v => typeof v === 'number' && !isNaN(v));
        const vmin = Math.min(...values);
        const vmax = Math.max(...values);
        layerStatic = layerCreator(data, "value", vmin, vmax, title, 'static');
    }else{
        // Plot dynamic map
        initDynamicMap(data, title, filename);
    }
}

function openPlotChart(key='NaN') {
    const currentDisplay = window.getComputedStyle(plotWindow).display;
    if (currentDisplay === "none") { plotWindow.style.display = "flex";}
    if (key === 'NaN') { plotWindow.style.display = "none"; }
    toggleMenu();
}

// Draw the chart using Plotly
function drawChart(data, title) {
    const cols = data.columns, rows = data.data;
    const x = rows.map(r => r[0]);
    const traces = [];
    for (let i = 1; i < cols.length; i++) {
        const y = rows.map(r => r[i]);
        const hasValid = y.some(val => val !== null && !isNaN(val));
        if (!hasValid) continue;
        traces.push({
        x: x, y: y, name: cols[i],
        type: 'scatter', mode: 'lines'
      });
    }
    const layout = {
        margin: {l: 60, r: 0, t: 5, b: 40},
        xaxis: {
            title:{text: 'Time', font: { size: 16, weight: 'bold' }},
            showgrid: true, gridcolor: '#ccc' 
        },
        yaxis: {
            title:{text: title, font: { size: 13, weight: 'bold' }}, 
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
    let csvHeader = 'Time';
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
    const headers = ['Time'];
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

// Load default map
loadData('temperature_toplayer.geojson', 'mesh2d_tem1', 'Temperature (°C)');
// loadData('depth_static.geojson', 'depth', 'Depth (m)');


// // Plot dynamically
// function loadHtml(filename) {
//     fetch(`/get_temp_html?filename=${filename}`)
//     .then(response => response.json()).then(data => {
//         if (data.status === "ok") {
//             if (stationLayer) { stationLayer.clearLayers(); stationLayer = null; }
//             if (crossSectionLayer) {crossSectionLayer.clearLayers(); crossSectionLayer = null;}
//             const iframe = document.getElementById('iframe_map');
//             const loading = document.getElementById('loadingOverlay');
//             // Start loading the iframe
//             loading.style.display = 'block';
//             // Load the iframe when file is large
//             iframe.src = `${data.content}?ts=${Date.now()}`;
//             iframe.onload = () => {loading.style.display = 'none';};
//         // Hide the Leaflet map and clear the layers
//         showIframeMap();
//         if (stationLayer) { stationLayer.clearLayers(); stationLayer = null; }
//         if (gridLayer) { gridLayer.clearLayers(); gridLayer = null; }
//         } else if (data.status === "error") {
//             alert(data.message);
//             return;
//         }                
//     });
// }


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