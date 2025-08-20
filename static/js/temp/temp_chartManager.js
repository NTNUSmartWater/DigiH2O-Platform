import { startLoading, showLeafletMap} from "./temp_mapManager.js";
import { loadData, interpolateJet, interpolateValue } from "./utils.js";
import { getGlobalChartData, setGlobalChartData } from "./temp_constants.js";

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

export async function plotChart(filename, key, chartTitle, titleX, titleY, swap) {
    startLoading(); // Show spinner
    const data = await loadData(filename, key); // Load data
    drawChart(data.content, chartTitle, titleX, titleY, swap);
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
    const {data, chartTitle, titleX, titleY, undefined, swap} = getGlobalChartData();
    drawChart(data, chartTitle, titleX, titleY, swap, selectedColumns);
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
export function drawChart(data, chartTitle, titleX, titleY, swap, selectedColumns=null) {
    const cols = data.columns, rows = data.data;
    const obj = '#select-object .checkbox-list input[type="checkbox"]';
    let checkboxInputs = document.querySelectorAll(obj);
    if (selectedColumns === null) checkboxInputs = [];
    // Populate checkbox list
    if (checkboxInputs.length === 0) {
        const validColumns = [];
        const startCol = swap ? 1 : 1;
        for (let i = startCol; i < cols.length; i++) {
            const y = rows.map(r => swap ? r[0] : r[i]);
            const hasValid = y.some(val => val !== null && !isNaN(val));
            if (hasValid) validColumns.push(i);
        }
        // Update global variable
        setGlobalChartData({ data, chartTitle, titleX, titleY, validColumns, swap });
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
    if (drawColumns.length === 0) {
        Plotly.purge(chartDiv());
        return;
    }
    const x = rows.map(r => swap ? r.slice(1) : r[0]);
    const traces = [];
    let traceIndex = 0;
    const n = drawColumns.length;  
    for (const colName of drawColumns) {
        const i = cols.indexOf(colName);
        if (i === -1) continue;
        const y = rows.map(r => swap ? r[0] : r[i]);
        const xVals = swap ? rows.map(r => r[i]) : x;  
        const t = n <= 1 ? 0 : traceIndex / (n - 1);
        const color = interpolateJet(1-t);
        traces.push({
            x: xVals, y: y, name: cols[i],
            type: 'scatter', mode: 'lines', line: { color: color }
        });
        traceIndex++;
    }
    if (traces.length === 0) {
        Plotly.purge(chartDiv());
        return;
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
    Plotly.purge(chartDiv()); // Clear the chart
    Plotly.newPlot('myChart', traces, layout, {responsive: true});
    Plotly.Plots.resize(chartDiv()); // Resize the chart
    // Update the header and maintain the close button
    plotTitle().innerHTML = chartTitle;
    swap = false; plotWindow().style.display = "flex"; // Show the chart
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
        alert("No data to view.");
        return;
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

export function plotProfile(pointContainer, polygonCentroids, titleY, titleX='Distance (m)', n_decimals) {
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
    drawChart(input, 'Profile', titleX, titleY, false);
}