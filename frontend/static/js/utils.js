import { startLoading, showLeafletMap } from "./mapManager.js";
import { n_decimals, superscriptMap, getState, setState} from "./constants.js";

function toSuperscript(num) {
    return String(num).split('').map(ch => superscriptMap[ch] || ch).join('');
}
export function numberFormatter(num, decimals) {
    if (num === null || num === undefined || isNaN(num)) return '';
    if (num === 0) return '0';
    if (Math.abs(num) < 1e-3 || Math.abs(num) >= 1e6) { return num.toExponential(decimals); }
    return num.toFixed(decimals);
}

export function nameChecker(name) {
    return !/^[A-Za-z0-9_-]+$/.test(name);
}

export function decodeArray(base64Str, n_decimals=3) {
    // Convert base64 to ArrayBuffer
    const binaryStr = atob(base64Str);
    const buffer = new ArrayBuffer(binaryStr.length);
    const view = new Uint8Array(buffer);
    for (let i = 0; i < binaryStr.length; i++) {
        view[i] = binaryStr.charCodeAt(i);
    }
    // Convert buffer to Float32Array
    const floatArray = new Float32Array(buffer);
    // Round values
    const values = Array.from(floatArray).map(v => parseFloat(v.toFixed(n_decimals)));
    return values;
}

export function getColors(nColors){
    if (nColors === 5) return ['#0416FF', '#03FFF8', '#02FF07', '#EDFF01', '#FF1E00'];
    else if (nColors === 10) return ['#0416FF', '#0094FF', '#03DAFF', '#00A305',
        '#71E507', '#DBF400', '#FFD602', '#FF9B0F', '#FF6301', '#FF1E00'];
    else if (nColors === 15) return ['#0416FF', '#035AFF', '#039EFF', '#03E3FF', 
        '#03FFD6', '#02FF91', '#02FF4C', '#02FF07', '#41FF02', '#86FF02',
        '#CBFF01', '#FFED01', '#FFA801', '#FF6301', '#FF1E00']
    return ['#0416FF', '#0348FF', '#037AFF', '#03ADFF', '#03DFFF', '#03FFEC',
        '#03FFB9', '#02FF86', '#02FF54', '#02FF21', '#16FF02', '#49FF02', '#7BFF02',
        '#AEFF01', '#E1FF01', '#FFEA01', '#FFB701', '#FF8401', '#FF5101', '#FF1E00']
}

export function valueFormatter(value, minDiff) {
    const absVal = Math.abs(value);
    let decimalPlaces = 2;
    if (minDiff >= 0.01) decimalPlaces = 2;
    else if (0.001 <= minDiff < 0.01) decimalPlaces = 3;
    else if (0.0001 <= minDiff < 0.001) decimalPlaces = 4;
    else decimalPlaces = 6;
    if (absVal < 0.01) {
        const expStr = value.toExponential(n_decimals);
        const [mantissa, exponent] = expStr.split('e');
        const expNum = parseInt(exponent, 10);
        return `${mantissa}×10${toSuperscript(expNum)}`;
    } else { return value.toFixed(decimalPlaces); }
}

export function interpolateJet(t) {
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

// Interpolate value using inverse distance weighting
export function interpolateValue(location, centroids, power = 5, maxDistance = Infinity) {
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
    return (sumValues / sumWeughts);
}

// Convert value to color
export function getColorFromValue(value, vmin, vmax, colorbarKey) {
    if (typeof value !== 'number' || isNaN(value)) {
        return { r: 150, g: 150, b: 150, a: 0 };
    }
    if (vmin === vmax) return { r: 0, g: 0, b: 100, a: 1 };
    // Minimum difference
    const minDiff = 1e-2, epsilon = 1e-6;
    if (vmax - vmin < minDiff) vmax = vmin + minDiff;
    let t0, t1, colors;
    if (vmin + epsilon <=0 || vmax + epsilon <=0) { // avoid zero division error for vmin or vmax = 0
        t0 = (value - vmin) / (vmax - vmin);
    } else {
        t0 = (Math.log(value + epsilon) - Math.log(vmin + epsilon)) / (Math.log(vmax + epsilon) - Math.log(vmin + epsilon));
    }
    t1 = 1 - Math.max(0, Math.min(1, t0));
    if (colorbarKey === "depth") { // used for depth
        colors = [
            { r: 160, g: 216, b: 239 },  // very light blue
            { r: 80,  g: 180, b: 220 },  // light blue
            { r: 0,   g: 119, b: 190 },  // medium blue
            { r: 0,   g: 70,  b: 130 },  // dark blue
            { r: 0,   g: 25,  b: 51  },  // very dark blue
        ];
    } else if (colorbarKey === "vector") { // used for vector
        colors = [
            { r: 220, g: 50,  b: 50  },  // red
            { r: 255, g: 140, b: 0   },  // orange
            { r: 255, g: 215, b: 0   },  // yellow
            { r: 255, g: 0,   b: 255 },  // magenta
            { r: 255, g: 255, b: 255 }   // white
        ];
    } else { // used for temperature, salinity, contaminant, ...
        colors = [
            { r: 255, g: 0,   b: 0   },    // red
            { r: 255, g: 165, b: 0   },   // orange
            { r: 255, g: 255, b: 0   },   // yellow
            { r: 100, g: 150, b: 255 },   // light blue 
            { r: 0,   g: 0,   b: 255 },   // blue
        ];
    }
    const binCount = colors.length - 1;
    const scaledT = t1 * binCount;
    const lower = Math.floor(scaledT);
    const upper = Math.min(colors.length - 1, lower + 1);
    const frac = scaledT - lower;
    const c1 = colors[lower], c2 = colors[upper];
    const r = Math.round(c1.r + (c2.r - c1.r) * frac);
    const g = Math.round(c1.g + (c2.g - c1.g) * frac);
    const b = Math.round(c1.b + (c2.b - c1.b) * frac);
    return { r, g, b, a: 1 };
}

// Update color for colorbar
export function updateColorbar(min, max, title, colorbarKey, bar_color, bar_title, bar_label) {
    bar_title.innerHTML = title.replace(/\n/g, '<br>');
    // Generate 5 color stops
    const colorStops = [], numStops = 5;
    // Minimum difference
    const minDiff = 1e-2, epsilon = 1e-6;
    if (max - min < minDiff) max = min + minDiff;
    // Update 5 labels
    const labels = bar_label.children;
    for (let i = 0; i < numStops; i++) {
        const percent = i / 4; // 0,0.25,0.5,0.75,1
        let value;
        if (min + epsilon > 0 && max + epsilon > 0) {
            const logMin = Math.log(min + epsilon);
            const logMax = Math.log(max + epsilon);
            value = Math.exp(logMin + percent * (logMax - logMin));
        } else { value = min + percent * (max - min);}
        labels[numStops - i - 1].textContent = valueFormatter(value, minDiff);
    }
    // Generate color for colorbar
    for (let i = 0; i < numStops; i++) {
        const t = i / (numStops - 1);
        let value;
        if (min + epsilon > 0 && max + epsilon > 0) {
            const logMin = Math.log(min + epsilon);
            const logMax = Math.log(max + epsilon);
            value = Math.exp(logMin + t * (logMax - logMin));
        } else { value = min + t * (max - min); }
        const color = getColorFromValue(value, min, max, colorbarKey);
        colorStops.push(`rgb(${color.r}, ${color.g}, ${color.b}) ${(t * 100).toFixed(1)}%`);
    }
    // Update gradient
    bar_color.style.background = `linear-gradient(to top, ${colorStops.join(", ")})`;
}

export function updateMapByTime(layerMap, values, vmin, vmax, colorbarKey) {
    for (let i = 0; i < getState().mapLayer.length; i++) {
        const id = getState().mapLayer[i];
        const value = values[id];
        if (value === null || value === undefined) continue;
        const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey);
        const colorKey = `${r},${g},${b},${a}`;
        if (getState().lastFeatureColors[id] === colorKey) continue;
        getState().lastFeatureColors[id] = colorKey;
        layerMap.setFeatureStyle(id, { 
            fill: true, fillColor: `rgb(${r},${g},${b})`, 
            fillOpacity: a, weight: 0, opacity: 1 
        });
    }
    setState({ lastFeatureColors: getState().lastFeatureColors });
}

// Load data
export async function loadData(query, key, projectName){
    const response = await fetch('/process_data', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query: query, key: key, projectName: projectName})});
    const data = await response.json();
    return data;
}

// Split lines into smaller segments and sort by distance
export function splitLines(pointContainer, polygonCentroids, subset_dis) {
    const interpolatedPoints = [];
    // Convert Lat, Long to x, y
    for (let i = 0; i < pointContainer.length - 1; i++) {
        const p1 = pointContainer[i], p2 = pointContainer[i + 1];
        const pt1 = L.Projection.SphericalMercator.project(L.latLng(p1.lat, p1.lng));
        const pt2 = L.Projection.SphericalMercator.project(L.latLng(p2.lat, p2.lng));
        const dx = pt2.x - pt1.x, dy = pt2.y - pt1.y;
        const segmentDist = Math.sqrt(dx * dx + dy * dy);
        const segments = Math.max(1, Math.floor(segmentDist / subset_dis));
        // Add the first point
        const originDist = L.latLng(p1.lat, p1.lng).distanceTo(pointContainer[0]);
        interpolatedPoints.push([originDist, p1.value, p1.lat, p1.lng]);
        // Add the intermediate points        
        for (let j = 1; j < segments; j++) {
            const ratio = j / segments;
            const interpX = pt1.x + ratio * dx, interpY = pt1.y + ratio * dy;
            const latlngInterp = L.Projection.SphericalMercator.unproject(L.point(interpX, interpY));
            // Interpolate
            const location = L.latLng(latlngInterp.lat, latlngInterp.lng);
            const interpValue = interpolateValue(location, polygonCentroids);
            // Fall back to nearest centroid if interpolation fails
            if (interpValue === null || interpValue === undefined) {
                interpValue = p1.value + ratio * (p2.value - p1.value);
            }
            // Compute distance            
            const distInterp = location.distanceTo(pointContainer[0]);
            interpolatedPoints.push([distInterp, interpValue, latlngInterp.lat, latlngInterp.lng]);
        }
        // Add the last point
        const lastDist = L.latLng(p2.lat, p2.lng).distanceTo(pointContainer[0]);
        interpolatedPoints.push([lastDist, p2.value, p2.lat, p2.lng]);
    }
    // Sort by distance
    interpolatedPoints.sort((a, b) => a[0] - b[0]);
    return interpolatedPoints;
}

export async function initOptions(comboBox, key) {
    startLoading('Loading Options. Please wait...'); 
    try {
        const response = await fetch('/initiate_options', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({key: key, projectName: getState().projectName})});
        const data = await response.json();
        if (data.status === "ok") {
            // Add none option in case of vector
            if (key === 'vector' || key === 'thermocline_waq'){
                comboBox().innerHTML = '';
                // Add hint to the velocity object
                const hint = document.createElement('option');
                hint.value = ''; hint.selected = true;
                hint.text = '- No Selection -'; 
                comboBox().add(hint);
            }
            // Add options
            data.content.forEach(item => {
                const option = document.createElement('option');
                option.value = item[0]; option.text = item[1];
                comboBox().add(option);
            });
            // Select the first option
            if (key !== 'vector' && key !== 'thermocline_waq') {comboBox().value = -1;}
        } else if (data.status === "error") {alert(data.message); return;}
    } catch (error) {alert(error);}
    showLeafletMap();
}

export async function loadList(fileName, key, folder_check = '') {
    const response = await fetch('/select_project', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: fileName, key: key, folder_check: folder_check})});
    const data = await response.json();
    if (data.status === "error") { alert(data.message); return null; }
    return data;
}

export async function fileUploader(targetFile, targetText, projectName, gridName, message, type){
    if (projectName === '') return;
    window.parent.postMessage({type: 'showOverlay', message: message}, '*');
    const file = targetFile.files[0], formData = new FormData();
    formData.append('file', file); formData.append('projectName', projectName);
    formData.append('fileName', gridName); formData.append('type', type);
    if (targetText !== null) {targetText.value = file?.name || "";}
    const response = await fetch('/upload_data', { method: 'POST', body: formData });
    const data = await response.json();
    window.parent.postMessage({type: 'hideOverlay'}, '*');
    if (data.status === "error") {
        if (targetText !== null) {targetText.value = '';}
        alert(data.message); targetFile.value = ''; return;
    }
    alert(data.message);
}

function updateChart(windowContainer, plotDiv, checkboxObj, selectBoxObj, plotTitle) {
    const checkboxes = checkboxObj.querySelectorAll('input[type="checkbox"]');
    const selectedColumns = Array.from(checkboxes)
        .filter(cb => cb.checked && cb.value !== 'All').map(cb => cb.value);
    const {data, chartTitle, titleX, titleY, undefined} = getState().globalChartData;
    plotTimeSeries(windowContainer, plotDiv, checkboxObj, selectBoxObj, plotTitle,
        data, chartTitle, titleX, titleY, selectedColumns);
}

export function populateCheckboxList(windowContainer, plotDiv, checkboxObj, selectBoxObj, plotTitle, columns) {
    checkboxObj.innerHTML = '';
    // Create "All" checkbox
    const allLabel = document.createElement('label');
    allLabel.innerHTML = `<input type="checkbox" value="All" checked> All`;
    const allCheckbox = allLabel.querySelector('input');
    checkboxObj.appendChild(allLabel);
    // Create checkbox for each column
    let maxWidth = allLabel.scrollWidth;
    const colCheckBoxes = [];
    columns.forEach(col => {
        const label = document.createElement('label');
        label.innerHTML = `<input type="checkbox" value="${col}"> ${col}`;
        const cb = label.querySelector('input');
        cb.checked = true;
        checkboxObj.appendChild(label); colCheckBoxes.push(cb);
        maxWidth = Math.max(maxWidth, label.scrollWidth);
    });
    // Select all columns by default
    allCheckbox.addEventListener('change', () => {
        if (allCheckbox.checked) colCheckBoxes.forEach(cb => cb.checked = true);
        else colCheckBoxes.forEach(cb => cb.checked = false);
        updateChart(windowContainer, plotDiv, checkboxObj, selectBoxObj, plotTitle);
    })
    // Select other columns
    colCheckBoxes.forEach(cb => {
        cb.addEventListener('change', () => {
            allCheckbox.checked = colCheckBoxes.every(cb => cb.checked);
            updateChart(windowContainer, plotDiv, checkboxObj, selectBoxObj, plotTitle);
        });
    });
    // Set width of checkbox list
    selectBoxObj.style.width = maxWidth + "px";
}

// Draw the chart using Plotly
export async function plotTimeSeries(windowContainer, plotDiv, checkboxList, selectBox,
    plotTitle, data, chartTitle, titleX, titleY, selectedColumns=null) {
    const cols = data.columns, rows = data.data;
    let checkboxInputs = checkboxList.querySelectorAll('input[type="checkbox"]');
    const x = rows.map(r => r[0]);
    if (selectedColumns === null) checkboxInputs = [];
    // Populate checkbox list
    if (checkboxInputs.length === 0) {
        const validColumns = [];
        for (let i = 1; i < cols.length; i++) {
            const y = rows.map(r => r[i]);
            const hasValid = y.some(val => val !== null && !isNaN(val));
            if (hasValid) validColumns.push(i);
        }
        // Update global variable
        setState({ globalChartData: { data, chartTitle, titleX, titleY, validColumns }});
        populateCheckboxList(windowContainer, plotDiv, checkboxList, selectBox, plotTitle, validColumns.map(i => data.columns[i]));
        checkboxInputs = checkboxList.querySelectorAll('input[type="checkbox"]');
    }
    // Get selected columns
    if (!selectedColumns) {
        selectedColumns = Array.from(checkboxInputs)
            .filter(cb => cb.checked && cb.value !== 'All').map(cb => cb.value);
    }
    const allCheckbox = Array.from(checkboxInputs).find(cb => cb.value === 'All');
    let drawColumns, traceIndex = 0;
    if (allCheckbox && allCheckbox.checked) drawColumns = cols.slice(1);
    else drawColumns = selectedColumns;
    if (drawColumns.length === 0) { Plotly.purge(plotDiv); return; }
    const traces = [], n = drawColumns.length;  
    for (const colName of drawColumns) {
        const i = cols.indexOf(colName);
        if (i === -1) continue;
        const y = rows.map(r => r[i]);
        const t = n <= 1 ? 0 : traceIndex / (n - 1);
        const color = interpolateJet(1-t);
        traces.push({ x: x, y: y, name: cols[i], type: 'scatter', mode: 'lines', line: { color: color } });
        traceIndex++;
    }
    if (traces.length === 0) { Plotly.purge(plotDiv); return; }
    const layout = {
        margin: {l: 60, r: 20, t: 50, b: 20}, paper_bgcolor: '#c2bdbdff', plot_bgcolor: '#c2bdbdff',
        title: { text: chartTitle, x: 0.5, xanchor: 'center', y: 0.95, yanchor: 'top',
            font: { size: 20, color: 'black', weight: 'bold' } },
        xaxis: {
            title:{text: titleX, font: { size: 16, weight: 'bold', color: 'black' }},
            showgrid: false, linecolor: 'black', tickfont: { color: 'black' },
            automargin: true, ticks: 'outside', linewidth: 1, tickmode: 'auto'
        },
        yaxis: {
            title:{ text: titleY, automargin: true, font: { size: 16, weight: 'bold', color: 'black' }}, 
            showgrid: false, linecolor: 'black', tickfont: { color: 'black' },
            automargin: true, ticks: 'outside', linewidth: 1, tickmode: 'auto'
        },
        legend: { orientation: 'h', x: 0.5, xanchor: 'center', y: -0.25,
            font: { size: 14, color: 'black', weight: 'bold' } }
    };
    plotTitle.innerHTML = chartTitle; // Update the header and maintain the close button
    windowContainer.style.display = "flex"; // Show the chart
    setTimeout(() => {
        Plotly.react(plotDiv, traces, layout, { responsive: true });
        new ResizeObserver(() => {
            Plotly.Plots.resize(plotDiv);
        }).observe(plotDiv.parentElement);
    }, 50);
}

function formatDateTime(value) {
    const d = new Date(value);
    if (isNaN(d)) return value;
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ` +
        `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

// Export chart data to new tab as CSV format
export function viewDatafromPlot(plotDiv) {
    const data = plotDiv.data?.[0];
    if (!data) { alert("No data to view."); return; }
    // Get the y values
    const numTraces = plotDiv.data.length;
    const title = plotDiv.layout?.title?.text || "Chart";
    const titleText = typeof title === "string"
        ? (title.includes(':') ? title.split(':')[1].trim() : title) : "Chart";
    const titleY = plotDiv.layout?.yaxis?.title?.text || "Value";
    let csvHeader = plotDiv.layout?.xaxis?.title?.text || 'Unknown';
    for (let i = 0; i < numTraces; i++) {
        const traceName = plotDiv.data[i].name || `${titleText}_${titleY}_${i}`;
        csvHeader += `,${traceName}`;
    }
    let csvContent = `${csvHeader}\n`;
    for (let i = 0; i < plotDiv.data[0].x.length; i++) {
        let rawTime = plotDiv.data[0].x[i];
        let formattedTime = formatDateTime(rawTime);
        let row = `${formattedTime}`;
        for (let j = 0; j < numTraces; j++) {
            row += `,${numberFormatter(plotDiv.data[j].y[i], 5)}`;
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
        body.appendChild(pre); doc.body = body;
    } else { alert("Pop-up blocked. Please allow popups for this site."); }
}

// Save to Excel
export function saveToExcelFromPlot(plotDiv) {
    const data = plotDiv.data?.[0];
    if (!data) { alert("No data to save."); return; }
    // Get the y values
    const numTraces = plotDiv.data.length;
    const title = plotDiv.layout?.title?.text || "Chart";
    const titleText = typeof title === "string"
        ? (title.includes(':') ? title.split(':')[1].trim() : title): "Chart";
    const titleY = plotDiv.layout?.yaxis?.title?.text || "Value";
    // Prepare the data
    const title_ = plotDiv.layout?.xaxis?.title?.text || 'Unknown';
    const headers = [title_];
    for (let i = 0; i < numTraces; i++) {
        const traceName = plotDiv.data[i].name || `${titleText}_${titleY}_${i}`;
        headers.push(traceName);
    }
    const table = [headers], numPoints = plotDiv.data[0].x.length;
    for (let i = 0; i < numPoints; i++) {
        const row = [plotDiv.data[0].x[i]];
        for (let j = 0; j < numTraces; j++) {
            row.push(numberFormatter(plotDiv.data[j].y[i], 4));
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
