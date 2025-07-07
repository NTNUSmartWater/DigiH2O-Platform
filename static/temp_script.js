let stationLayer = null; crossSectionLayer = null; defaultMapLayer = null;
let isDragging = false, offsetX = 0, offsetY = 0; isOpen = true; isinfoOpen = true;
let queryPoint = false; queryPath = false; currentMarker = null;
CENTER = [62.476969, 6.471598]; ZOOM = 13; 
const chartDiv = document.getElementById('myChart');
const infoDetails = document.getElementById("infoDetails");
const content = document.getElementById("infoContent");
const menu = document.getElementById("offCanvasMenu");
const button = document.getElementById('menuBtn');
const loading = document.getElementById('loadingOverlay');
const iframe = document.getElementById('iframe_map');
const leaflet_map = document.getElementById('leaflet_map');
const arrow = document.getElementById("arrowToggle");
const infoPanel = document.getElementById("infoPanel");
const infoPanelHeader = document.getElementById("infoPanelHeader")
let infor = document.getElementById("infoDetailsContent");
let header = document.getElementById("infoHeader");
let infoWindow = document.getElementById("infoWindow");



// Convert value to color
function getColorFromValue(value, vmin, vmax) {
    if (typeof value !== 'number' || isNaN(value)) {
        return { r: 0, g: 0, b: 0, a: 0 };
    }
    // Clamp value
    value = Math.max(vmin, Math.min(vmax, value));
    const t = (value - vmin) / (vmax - vmin);
    // Simple blue → cyan → green gradient (can expand if needed)
    const r = Math.round(115 * t); // 0 → 115
    const g = Math.round(208 * t); // 66 → 208
    const b = Math.round(157 - 157 * t); // 157 → 0
    const a = 1;
    return { r, g, b, a };
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

document.addEventListener('click', function(event) {
    // Hide the main menu and info menu if user clicks outside of it
    if (menu && button) {
        const isClickedInsideMenu = menu.contains(event.target) || button.contains(event.target);
        const isMenuOpen = window.getComputedStyle(menu).width !== '0px';
        if (!isClickedInsideMenu && isMenuOpen) {toggleMenu();}
    }
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
document.querySelectorAll('.menu-item-with-submenu > .menu-link').forEach(link => {
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
}

// Move summary window
header.addEventListener("mousedown", function(e) {
    isDragging = true;
    offsetX = e.clientX - infoWindow.offsetLeft;
    offsetY = e.clientY - infoWindow.offsetTop;
});
document.addEventListener("mousemove", function(e) {
    if (isDragging) {
        infoWindow.style.left = (e.clientX - offsetX) + "px";
        infoWindow.style.top = (e.clientY - offsetY) + "px";
    }
});
document.addEventListener("mouseup", function() {
    isDragging = false;
    Plotly.Plots.resize(document.getElementById('myChart'));
});

// Load JSON file (including JSON and GeoJSON)
async function loadData(filename, key, title_y='') {
    // Clear layers if already loaded
    if (stationLayer){
        stationLayer.clearLayers(); stationLayer = null;
        return;
    }
    if (crossSectionLayer){
        crossSectionLayer.clearLayers(); crossSectionLayer = null;
        return;
    }
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
            } else if (key === "default_map") {
                // Plot a default map
                
                plotDefaultMap(data.content);
            } else {
                // Plot data
                drawChart(data.content, title_y);
            }
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    showLeafletMap();
}

// Make query for points
function makeQuery(key, query) {
    const mapContainer = map.getContainer();
    if (key === "point") {
        if (!queryPoint){
            mapContainer.style.cursor = "help";
            queryPoint = true; infoDetails.style.display = "block";
            map.on('click', function(e) {
                if (!queryPoint) return;
                const lat = e.latlng.lat.toFixed(5);
                const lng = e.latlng.lng.toFixed(5);
                if (currentMarker) { map.removeLayer(currentMarker); }
                currentMarker = L.marker(e.latlng).addTo(map);
                const html = `
                <div style="display: flex; justify-content: space-between; font-size: 13px;">
                    <div>Location:</div>
                    <div>${lng}, ${lat}</div>
                </div>
                `;
                infor.innerHTML = html;
            });
        } else {
            mapContainer.style.cursor = "pointer";
            queryPoint = false; infor.innerHTML = "";
            infoDetails.style.display = "none";
            if (currentMarker) {
                map.removeLayer(currentMarker);
                currentMarker = null;
            }
        }
    } else if (key === "path") {
        if (!queryPath){
            mapContainer.style.cursor = "crosshair";
            queryPoint = true;



        } else {
            mapContainer.style.cursor = "pointer";
            queryPoint = false;
        }
    }
}


// Plot default map
function plotDefaultMap(data) {
    
    if (defaultMapLayer) {
        return; // Already plotted
    }
    // Show spinner
    startLoading();
    defaultMapLayer = L.vectorGrid.slicer(data, {
        rendererFactory: L.canvas.tile,
        vectorTileLayerStyles: {
            sliced: function(properties, ZOOM) {
                const value = properties.value || 0; // Default value if not present
                // Use vmin and vmax from properties or set defaults
                const vmin = properties.vmin;
                const vmax = properties.vmax;
                const { r, g, b, a } = getColorFromValue(value, vmin, vmax);
                return {
                    fill: true, fillColor: `rgb(${r}, ${g}, ${b})`,
                    weight: 0.5, color: '#000', opacity: a, stroke: true,
                };
            }
        },
        interactive: true, maxZoom: ZOOM.CENTER,
        getFeatureId: f => f.properties.id || f.properties.name || f.properties.value
    });
    defaultMapLayer.addTo(map);
    // Add click event to the layer
    defaultMapLayer.on('click', function(e) {
        const properties = e.layer.feature.properties;
        alert(`Clicked on: ${properties.name || 'Unknown'}\nValue: ${properties.value || 'N/A'}`);
    })
    // Hide the spinner and show the map
    loading.style.display = "none";
}



// Draw the chart using Plotly
function drawChart(data, title_y) {
    const cols = data.columns;
    const rows = data.data;
    const x = rows.map(r => r[0]);
    const traces = [];
    for (let i = 1; i < cols.length; i++) {
        const y = rows.map(r => r[i]);
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
            title:{text: title_y, font: { size: 13, weight: 'bold' }}, 
            showgrid: true, gridcolor: '#ccc'
        },
    };
    Plotly.purge(chartDiv); // Clear the chart
    Plotly.newPlot('myChart', traces, layout, {responsive: true});
    // Resize the chart
    Plotly.Plots.resize(chartDiv);
    // Show the chart
    toggleChart(); toggleMenu();
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

