// let stationLayer = null, crossSectionLayer = null, isOpen = true; 
// let isDragging_infor = false, offsetX_infor = 0, offsetY_infor = 0;
// let isDragging_plot = false, offsetX_plot = 0, offsetY_plot = 0;
let queryPoint = false, queryPath = false, currentMarker = null;
// let layerStatic = null, layerDynamic = null, isPlaying = null;
let layerBelow = null, layerAbove = null;
// let playHandlerAttached = false, isinfoOpen = false, currentIndex = 0;
let colorbarControl = L.control({ position: 'topright' });
// let parsedDataAllFrames = null, pointContainer = []; isPath = false;
// let selectedMarkers = [], pathLine = null, marker = null;
// let storedLayer = false, clickedInsideLayer = false;
// let isPathQuery = false, polygonCentroids = [];
// const CENTER = [62.476969, 6.471598], ZOOM = 13;
// const pathQueryCheckbox = document.getElementById("pathQuery");
// const pointQueryCheckbox = document.getElementById("pointQuery");
// const chartDiv = document.getElementById('myChart');
// const content = document.getElementById("infoContent");
// const menu = document.getElementById("offCanvasMenu");
// const button = document.getElementById('menuBtn');
// const loading = document.getElementById('loadingOverlay');
// const leaflet_map = document.getElementById('leaflet_map');
// const arrow = document.getElementById("arrowToggle");
const infoDetails = document.getElementById("infoDetails");
// const infoPanel = document.getElementById("infoPanel");
// const infoPanelHeader = document.getElementById("infoPanelHeader")
// const slider = document.getElementById("time-slider");
// const playBtn = document.getElementById("play-btn");
// const timeControl = document.getElementById("time-controls");
const exportVideoBtn = document.getElementById("export-video-btn");
// const selectObject = document.getElementById("select-object");
// const velocityObject = document.getElementById("velocity-object");
const vectorObjectMain = document.getElementById("vector-object-main");
const vectorObjectSubmain = document.getElementById("vector-object-submain");
// let colorbar_title = document.getElementById("colorbar-title");
// let colorbar_color = document.getElementById("colorbar-gradient");
let infor = document.getElementById("infoDetailsContent");
let infoHeader = document.getElementById("infoHeader");
// let infoWindow = document.getElementById("infoWindow");
// let plotHeader = document.getElementById("plotHeader");
// let plotWindow = document.getElementById("plotWindow");
// const belowLayer = document.getElementById("below-object");
// const aboveLayer = document.getElementById("above-object");
// const plotLayersBtn = document.getElementById("plotLayersBtn");
const chart = document.getElementById("chartPanel");
// let globalChartData = {
//     filename: "", data: null, titleX: "", titleY: "", validColumns: [], columnIndexMap: {}, swap: false
// };
// const hoverTooltip = L.tooltip({
//   permanent: false, direction: 'bottom',
//   sticky: true, offset: [0, 10],
//   className: 'custom-tooltip' // optional: for styling
// });





// // Load JSON file (including JSON and GeoJSON)
// async function loadData(filename, key, title, colorbarKey='depth', station='') {
//     // Show spinner
//     startLoading();
//     // Deselect checkbox
//     if (pathQueryCheckbox.checked) pathQueryCheckbox.checked = false;
//     if (pointQueryCheckbox.checked) pointQueryCheckbox.checked = false;
//     hideQuery('path'); hideQuery('point');
//     try {
//         const response = await fetch('/process_data', {
//         method: 'POST', headers: {'Content-Type': 'application/json'},
//         body: JSON.stringify({data_filename: filename, key: key, station: station})});
//         const data = await response.json();
//         if (data.status === "ok") {
//             }  else if (filename.includes("velocity")){
//                 // Plot a vector map
//                 plotVectorMap(data.content, title, colorbarKey);
//             } else {
//                 // Plot a 2D map
//                 plotMap(data.content, filename, title, colorbarKey);            
//             }
//         } else if (data.status === "error") {alert(data.message);}
//     } catch (error) {alert(error);}
//     showLeafletMap(); // Hide the spinner and show the map
// }

function changeVelocity(object) {
    if (object.selectedIndex === 0) return;
    const index = object.selectedIndex - 1;
    loadData(`${object.value}_velocity`, index, 'Velocity (m/s)', 'velocity');
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
    const scale = 400, arrowLength = 1;
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





// function hideQuery(key) {
//     const mapContainer = map.getContainer();
//     if (key === "point") {
//         queryPoint = false; toggleinfoMenu();
//         mapContainer.style.cursor = "grab"; infor.innerHTML = "";
//         infoDetails.style.display = "none";
//         if (currentMarker) {
//             map.removeLayer(currentMarker);
//             currentMarker = null;
//         }
//         map.off('click', mapPoint);
//         if (plotWindow.style.display === "flex") { plotWindow.style.display = "none"; }
//     } else if (key === "path") {
//         queryPath = false; isPath = false;
//         map.closeTooltip(hoverTooltip);
//         mapContainer.style.cursor = "grab";
//         map.off('click', mapPath);
//         // Reset
//         pathQueryReset();
//     }
// } 

// // Make query for points
// function makeQuery(key) {
//     const mapContainer = map.getContainer();
//     if (key === "point") {
//         queryPoint = true;
//         mapContainer.style.cursor = "help";
//         infoDetails.style.display = "block";
//         map.on('click', mapPoint);
//         isinfoOpen = false; toggleinfoMenu();
//     } else if (key === "path") {
//         queryPath = true; isPath = true;
//         if (!isPathQuery) {
//             alert("This type of map does not support path queries.\nOnly static and dynamic (with single layer) maps are supported.");
//             // Deselect checkbox
//             if (pathQueryCheckbox.checked) pathQueryCheckbox.checked = false;
//             return;
//         }
//         if (!layerStatic && !layerDynamic) {
//             alert("To use this feature, you need to load a layer first.");
//             return;
//         } else {
//             mapContainer.style.cursor = "crosshair";
//             pathQueryReset();
//         }
//     }
// }







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



// async function initiateVelocities(object) {
//     startLoading();
//     try {
//         const response = await fetch('/process_velocity', {
//         method: 'POST', headers: {'Content-Type': 'application/json'},
//         body: JSON.stringify({})});
//         const data = await response.json();
//         if (data.status === "ok") {
//             // Add options to the velocity object
//             object.innerHTML = '';
//             // Add hint to the velocity object
//             const hint_velocity = document.createElement('option');
//             hint_velocity.value = ''; hint_velocity.selected = true;
//             hint_velocity.textContent = '-- Select a type --'; 
//             object.add(hint_velocity);
//             // Add options
//             data.content.forEach(item => {
//                 const option = document.createElement('option');
//                 option.value = item; option.text = item;
//                 object.add(option);
//             });
//         } else if (data.status === "error") {alert(data.message);}
//     } catch (error) {alert(error);}
//     // Hide the spinner and show the map
//     showLeafletMap();
// }




// async function initiateVector() {
//     startLoading();
//     try {
//         const response = await fetch('/process_vector', {
//         method: 'POST', headers: {'Content-Type': 'application/json'},
//         body: JSON.stringify({})});
//         const data = await response.json();
//         if (data.status === "ok") {
//             // Add options to the velocity object
//             vectorObjectMain.innerHTML = '';
//             // Add hint to the velocity object
//             const hint_velocity = document.createElement('option');
//             hint_velocity.value = ''; hint_velocity.selected = true;
//             hint_velocity.textContent = '-- Select a type --'; 
//             vectorObjectMain.add(hint_velocity);
//             // Add options
//             data.content.forEach(item => {
//                 const option = document.createElement('option');
//                 option.value = item; option.text = item;
//                 vectorObjectMain.add(option);
//             });
//         } else if (data.status === "error") {alert(data.message);}
//     } catch (error) {alert(error);}
//     // Hide the spinner and show the map
//     showLeafletMap();
// }


