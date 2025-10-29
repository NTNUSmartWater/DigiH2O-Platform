import { startLoading, showLeafletMap} from "./mapManager.js";
import { loadData, interpolateJet, interpolateValue, getMinMaxFromDict, getColors } from "./utils.js";
import { getState, setState } from "./constants.js";

let Dragging = false;

export const plotWindow = () => document.getElementById('plotWindow');
const plotHeader = () => document.getElementById('plotHeader');
const plotTitle = () => document.getElementById('plotTitle');
const closePlotOption = () => document.getElementById('closePlotBtn');
const dropdown = () => document.getElementById("select-object");
const selectBox = () => dropdown().querySelector('.select-box');
const checkboxList = () => dropdown().querySelector('.checkbox-list');
const chartDiv = () => document.getElementById('myChart');
const viewDataBtn = () => document.getElementById('viewDataBtn');
const downloadBtn = () => document.getElementById('downloadExcel');

export async function plotChart(query, key, chartTitle, titleX, titleY) {
    startLoading('Preparing Data for Chart. Please wait...'); // Show spinner
    const data = await loadData(query, key); // Load data
    if (data.status === 'error') { showLeafletMap(); alert(data.message); return; }
    drawChart(data.content, chartTitle, titleX, titleY);
    showLeafletMap(); // Hide the spinner and show the map
}

export function plotEvents() {
    // Move summary window
    let offsetX = 0, offsetY = 0;
    plotHeader().addEventListener("mousedown", function(e) {
        Dragging = true;
        offsetX = e.clientX - plotWindow().offsetLeft;
        offsetY = e.clientY - plotWindow().offsetTop;
    });
    document.addEventListener("mousemove", function(e) {
        if (Dragging) {
            plotWindow().style.left = (e.clientX - offsetX) + "px";
            plotWindow().style.top = (e.clientY - offsetY) + "px";
        }
    });
    // Resize the chart window
    document.addEventListener("mouseup", function() { 
        Plotly.Plots.resize(chartDiv()); Dragging = false; 
    });
    // Open dropdown
    selectBox().addEventListener("click", () => {
        checkboxList().style.display = checkboxList().style.display === 'block' ? 'none' : 'block';
    });
    // Close dropdown when click outside
    document.addEventListener('click', e => {
        if (!dropdown().contains(e.target)) checkboxList().style.display = 'none';
    });   
    // Download chart
    viewDataBtn().addEventListener("click", () => { viewData(); });
    // Download data as Excel
    downloadBtn().addEventListener("click", () => { saveToExcel(); });
    // Close plot
    closePlotOption().addEventListener('click', () => { plotWindow().style.display = "none"; });
}

function updateChart() {
    const checkboxes = checkboxList().querySelectorAll('input[type="checkbox"]');
    const selectedColumns = Array.from(checkboxes)
        .filter(cb => cb.checked && cb.value !== 'All')
        .map(cb => cb.value);
    const {data, chartTitle, titleX, titleY, undefined} = getState().globalChartData;
    drawChart(data, chartTitle, titleX, titleY, selectedColumns);
}

function populateCheckboxList(columns) {
    const list = checkboxList();
    list.innerHTML = '';
    // Create "All" checkbox
    const allLabel = document.createElement('label');
    allLabel.innerHTML = `<input type="checkbox" value="All" checked> All`;
    const allCheckbox = allLabel.querySelector('input');
    list.appendChild(allLabel);
    // Create checkbox for each column
    let maxWidth = allLabel.scrollWidth;
    const colCheckBoxes = [];
    columns.forEach(col => {
        const label = document.createElement('label');
        label.innerHTML = `<input type="checkbox" value="${col}"> ${col}`;
        const cb = label.querySelector('input');
        cb.checked = true;
        list.appendChild(label); colCheckBoxes.push(cb);
        maxWidth = Math.max(maxWidth, label.scrollWidth);
    });
    // Select all columns by default
    allCheckbox.addEventListener('change', () => {
        if (allCheckbox.checked) colCheckBoxes.forEach(cb => cb.checked = true);
        else colCheckBoxes.forEach(cb => cb.checked = false);
        updateChart();
    })
    // Select other columns
    colCheckBoxes.forEach(cb => {
        cb.addEventListener('change', () => {
            allCheckbox.checked = colCheckBoxes.every(cb => cb.checked);
            updateChart();
        });
    });
    // Set width of checkbox list
    selectBox().style.width = maxWidth + "px";
}

// Draw the chart using Plotly
export function drawChart(data, chartTitle, titleX, titleY, selectedColumns=null) {
    const cols = data.columns, rows = data.data;
    const obj = '#select-object .checkbox-list input[type="checkbox"]';
    let checkboxInputs = document.querySelectorAll(obj);
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
        populateCheckboxList(validColumns.map(i => data.columns[i]));
        checkboxInputs = document.querySelectorAll(obj);
    }
    // Get selected columns
    if (!selectedColumns){
        selectedColumns = Array.from(checkboxInputs)
                .filter(cb => cb.checked && cb.value !== 'All').map(cb => cb.value);
    }
    const allCheckbox = Array.from(checkboxInputs).find(cb => cb.value === 'All');
    let drawColumns;
    if (allCheckbox && allCheckbox.checked) drawColumns = cols.slice(1);
    else drawColumns = selectedColumns;
    if (drawColumns.length === 0) { Plotly.purge(chartDiv()); return; }
    const traces = [];
    let traceIndex = 0;
    const n = drawColumns.length;  
    for (const colName of drawColumns) {
        const i = cols.indexOf(colName);
        if (i === -1) continue;
        const y = rows.map(r => r[i]);
        const t = n <= 1 ? 0 : traceIndex / (n - 1);
        const color = interpolateJet(1-t);
        traces.push({ x: x, y: y, name: cols[i],
            type: 'scatter', mode: 'lines', line: { color: color }
        });
        traceIndex++;
    }
    if (traces.length === 0) { Plotly.purge(chartDiv()); return; }
    const layout = {
        margin: {l: 60, r: 0, t: 5, b: 70}, paper_bgcolor: '#c2bdbdff', plot_bgcolor: '#c2bdbdff',
        xaxis: {
            title:{text: titleX, font: { size: 16, weight: 'bold', color: 'black' }},
            showgrid: false, linecolor: 'black', tickfont: { color: 'black' },
            automargin: true, ticks: 'outside', linewidth: 1, tickmode: 'auto'
        },
        yaxis: {
            title:{text: titleY, font: { size: 16, weight: 'bold', color: 'black' }}, 
            showgrid: false, linecolor: 'black', tickfont: { color: 'black' },
            automargin: true, ticks: 'outside', linewidth: 1, tickmode: 'auto'
        },
    };
    Plotly.purge(chartDiv()); // Clear the chart
    Plotly.newPlot('myChart', traces, layout, {responsive: true});
    Plotly.Plots.resize(chartDiv()); // Resize the chart
    plotTitle().innerHTML = chartTitle; // Update the header and maintain the close button
    plotWindow().style.display = "flex"; // Show the chart
}

function numberFormatter(num, decimals) {
    if (num === null || num === undefined || isNaN(num)) return '';
    if (num === 0) return '0';
    if (Math.abs(num) < 1e-3 || Math.abs(num) >= 1e6) {
        return num.toExponential(decimals);
    }
    return num.toFixed(decimals);
}

// Export chart data to new tab as CSV format
function viewData() {
    const data = chartDiv().data?.[0];
    if (!data) {
        alert("No data to view."); return;
    }
    // Get the y values
    const numTraces = chartDiv().data.length;
    const title = chartDiv().layout?.title?.text || "Chart";
    const titleText = typeof title === "string"
        ? (title.includes(':') ? title.split(':')[1].trim() : title)
        : "Chart";
    const titleY = chartDiv().layout?.yaxis?.title?.text || "Value";
    let csvHeader = chartDiv().layout?.xaxis?.title?.text || 'Unknown';
    for (let i = 0; i < numTraces; i++) {
        const traceName = chartDiv().data[i].name || `${titleText}_${titleY}_${i}`;
        csvHeader += `,${traceName}`;
    }
    let csvContent = `${csvHeader}\n`;
    for (let i = 0; i < chartDiv().data[0].x.length; i++) {
        let row = `${chartDiv().data[0].x[i]}`;
        for (let j = 0; j < numTraces; j++) {
            row += `,${numberFormatter(chartDiv().data[j].y[i], 4)}`;
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
export function saveToExcel() {
    const data = chartDiv().data?.[0];
    if (!data) {
        alert("No data to save.");
        return;
    }
    // Get the y values
    const numTraces = chartDiv().data.length;
    const title = chartDiv().layout?.title?.text || "Chart";
    const titleText = typeof title === "string"
        ? (title.includes(':') ? title.split(':')[1].trim() : title): "Chart";
    const titleY = chartDiv().layout?.yaxis?.title?.text || "Value";
    // Prepare the data
    const title_ = chartDiv().layout?.xaxis?.title?.text || 'Unknown';
    const headers = [title_];
    for (let i = 0; i < numTraces; i++) {
        const traceName = chartDiv().data[i].name || `${titleText}_${titleY}_${i}`;
        headers.push(traceName);
    }
    const table = [headers];
    const numPoints = chartDiv().data[0].x.length;
    for (let i = 0; i < numPoints; i++) {
        const row = [chartDiv().data[0].x[i]];
        for (let j = 0; j < numTraces; j++) {
            row.push(numberFormatter(chartDiv().data[j].y[i], 4));
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
export function plotProfileSingleLayer(pointContainer, polygonCentroids, title, titleY, titleX='Distance (m)', n_decimals) {
    const subset_dis = 20, interpolatedPoints = [];
    // Convert Lat, Long to x, y
    for (let i = 0; i < pointContainer.length - 1; i++) {
        const p1 = pointContainer[i], p2 = pointContainer[i + 1];
        const pt1 = L.Projection.SphericalMercator.project(L.latLng(p1.lat, p1.lng));
        const pt2 = L.Projection.SphericalMercator.project(L.latLng(p2.lat, p2.lng));
        const dx = pt2.x - pt1.x, dy = pt2.y - pt1.y;
        const segmentDist = Math.sqrt(dx * dx + dy * dy);
        const segments = Math.max(1, Math.floor(segmentDist / subset_dis));
        // Add the first point
        const originDist = numberFormatter(L.latLng(p1.lat, p1.lng).distanceTo(pointContainer[0]), n_decimals);
        interpolatedPoints.push([originDist, p1.value]);
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
            const distInterp = numberFormatter(location.distanceTo(pointContainer[0]), n_decimals);
            interpolatedPoints.push([distInterp, interpValue]);
        }
        // Add the last point
        const lastDist = numberFormatter(L.latLng(p2.lat, p2.lng).distanceTo(pointContainer[0]), n_decimals);
        interpolatedPoints.push([lastDist, p2.value]);
    }
    // Sort by distance
    interpolatedPoints.sort((a, b) => a[0] - b[0]);
    const input = {
        columns: [titleX, titleY], data: interpolatedPoints
    };
    drawChart(input, title, titleX, titleY, false);
}

export function plotProfileMultiLayer(windowContainer, data, title, unit, decimals) { 
    const chartDiv = windowContainer().querySelector('#chartDiv'); 
    const playPauseBtn = windowContainer().querySelector('#chartPlayPauseBtn'); 
    const colorCombo = windowContainer().querySelector('#chartColorCombo'); 
    const minValue = windowContainer().querySelector('#chartMinValue'); 
    const maxValue = windowContainer().querySelector('#chartMaxValue'); 
    const durationValue = windowContainer().querySelector('#chartDurationValue'); 
    chartDiv.style.border = "1px solid #aaa"; 
    chartDiv.style.borderRadius = "10px"; 
    chartDiv.style.boxShadow = "0 2px 8px rgba(0,0,0,0.15)"; 
    if (windowContainer()._resizeObserver) windowContainer()._resizeObserver.disconnect(); 
    const { timestamps, ids, depths, values, minmax } = data; 
    minValue.value = minmax[0].toFixed(decimals); maxValue.value = minmax[1].toFixed(decimals); 
    let animating = false, frameIndex = 0, duration = parseFloat(durationValue.value)*1000; 
    const nColors = parseInt(colorCombo.value); 
    windowContainer()._resizeObserver = renderPlot(chartDiv, timestamps, ids, depths, 
                                                values, nColors, title, unit, decimals); 
    // === Play / Pause control === 
    async function playAnimation() { 
        while (animating && frameIndex < timestamps.length) { 
            Plotly.animate(chartDiv, [timestamps[frameIndex]], { 
                mode: 'next', transition: { duration: 0 },
                frame: { duration: duration, redraw: true }, 
            }); 
            Plotly.relayout(chartDiv, { 'sliders[0].active': frameIndex }); 
            frameIndex++; 
            await new Promise(r => setTimeout(r, duration)); } 
            if (frameIndex >= timestamps.length) { 
                animating = false; playPauseBtn.textContent = '▶ Play'; 
                frameIndex = 0; // Reset index
            } 
        } 
    playPauseBtn.onclick = () => { 
        duration = parseFloat(durationValue.value)*1000;
        if (!animating){ 
            animating = true; playPauseBtn.textContent = '⏸ Pause'; 
            playAnimation(); 
        } else { 
            if (!animating) return; 
            animating = false; playPauseBtn.textContent = '▶ Play'; 
        } 
    };
    // === Slider control === 
    chartDiv.on('plotly_sliderchange', (e) => { 
        const currentLabel = e.step.label || e.value; 
        frameIndex = timestamps.indexOf(currentLabel);
    }); 
    // === Color control === 
    colorCombo.addEventListener('change', () => { 
        animating = false; playPauseBtn.textContent = '▶ Play'; 
        windowContainer()._resizeObserver = renderPlot(chartDiv, timestamps, ids, depths, 
            values, parseInt(colorCombo.value), title, unit, decimals); 
        frameIndex = 0; 
    }) 
    windowContainer().style.display = "flex";
}

function renderPlot(plotDiv, timestamps, ids, depths, values, nColors, title, unit, decimals){
    const discreteColors = getColors(nColors);
    const xLabels = ids.map(String), reversedDepths = [...depths];
    const reverseDepth = reversedDepths.every(d => d >= 0);
    // Generate animation frames
    const frames = timestamps.map(time => {
        const val = values[time];
        // Find min and max
        const { minVal: vmin, maxVal: vmax } = getMinMaxFromDict(val);
        const range = vmax - vmin;
        const boundaries = range === 0
            ? Array.from({ length: nColors + 1 }, () => vmin)
            : Array.from({ length: nColors + 1 }, (_, i) => vmin + (i * range) / nColors);
        // Build colorScale for Plotly (discrete)
        const colorScale = [], step = 1 / nColors;
        for (let i = 0; i < nColors; i++) {
            colorScale.push([i * step, discreteColors[i]]);
            colorScale.push([(i + 1) * step, discreteColors[i]]);
        }
        return { name: time,
            data: [{ z: val, x: xLabels, y: reversedDepths, type: 'heatmap', zsmooth: 'best',
                colorscale: colorScale, zmin: vmin, zmax: vmax, showscale: true,
                colorbar: {
                    title: { text: unit, font: { color: 'black' }}, tickfont: { color: 'black' },
                    tickvals: boundaries.slice(0, nColors + 1),
                    ticktext: boundaries.slice(0, nColors + 1).map(v => v.toFixed(decimals))
                }
            }]
        };
    });
    // === Layout ===
    const layout = { title: { text: title, font: { color: 'black', weight: 'bold', size: 20 } },
        paper_bgcolor: '#c2bdbdff', plot_bgcolor: '#c2bdbdff',
        xaxis: {
            title: {text: `Slice indexes (Selected slices: ${ids.length})`, font: { color: 'black' }},
            type: 'category', automargin: true, mirror: true, showgrid: false, tickmode: 'auto',
            showline: true, linewidth: 1, linecolor: 'black', tickfont: { color: 'black' }
        },
        yaxis: {
            title: {text: 'Depth (m)', font: { color: 'black' }}, autorange: reverseDepth ? 'reversed' : true,
            mirror: true, showline: true, linewidth: 1, linecolor: 'black', 
            showgrid: false, tickfont: { color: 'black' }, tickmode: 'auto'
        },
        margin: { l: 70, r: true ? 60 : 20, t: 50, b: 50 },
        sliders: [{
            active: 0, y: -0.1, len: 1.0, pad: { t: 50 },
            currentvalue: { prefix: 'Time: ', font: { size: 14, color: 'black' } },
            steps: timestamps.map(t => ({
                label: t, method: 'animate',
                args: [[t], { mode: 'immediate', frame: { duration: 0, redraw: true } }]
            }))
        }]
    };
    const config = {
        responsive: true, displaylogo: false, displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    };
    // === Plot ===
    const firstFrame = frames[0]?.data || [];
    Plotly.newPlot(plotDiv, firstFrame, layout, config).then(() => {
        Plotly.addFrames(plotDiv, frames);
        const resizeObserver = new ResizeObserver(() => Plotly.Plots.resize(plotDiv));
        resizeObserver.observe(plotDiv);
        return resizeObserver;
    });
}