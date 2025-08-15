import { startLoading, showLeafletMap} from "./temp_mapManager.js";
import { loadData, toNumber } from "./utils.js";
import { getGlobalChartData, setGlobalChartData } from "./temp_constants.js";
import { deactivePathQuery, deactivePointQuery } from "./temp_queryManager.js";

let Dragging = false;


export const plotWindow = () => document.getElementById('plotWindow');
const plotHeader = () => document.getElementById('plotHeader');
const plotTitle = () => document.getElementById('plotTitle');
const closePlotOption = () => document.getElementById('closePlotBtn');
const selectObject = () => document.getElementById("select-object");
const chartDiv = () => document.getElementById('myChart');
const viewDataBtn = () => document.getElementById('viewDataBtn');
const downloadBtn = () => document.getElementById('downloadExcel');


export function closePlotChart() {
    closePlotOption().addEventListener('click', () => {
        // Deactivate queries if it is active
        deactivePathQuery(); deactivePointQuery();
    })
}

export async function plotChart(filename, key, chartTitle, titleX, titleY, selectedColumnName, swap) {
    startLoading(); // Show spinner
    const data = await loadData(filename, key); // Load data
    drawChart(data.content, chartTitle, titleX, titleY, selectedColumnName, swap);
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
    // Update chart
    selectObject().addEventListener("change", function(e) {
        const { data, chartTitle, titleX, titleY, validColumns, columnIndexMap, swap } = getGlobalChartData();
        if (data) { drawChart(data, chartTitle, titleX, titleY, e.target.value, swap); 
        } else { alert("No data available to update chart.");}
    });
    // Download chart
    viewDataBtn().addEventListener("click", () => { viewData(); });
    // Download data as Excel
    downloadBtn().addEventListener("click", () => { saveToExcel(); });
}

// Draw the chart using Plotly
export function drawChart(data, chartTitle, titleX, titleY, selectedColumnName, swap) {
    const cols = data.columns, rows = data.data;
    const x = rows.map(r => swap ? r.slice(1) : r[0]);
    const traces = [];
    const validColumns = [];
    const columnIndexMap = {};
    const startCol = swap ? 1 : 1;
    for (let i = startCol; i < cols.length; i++) {
        const y = rows.map(r => swap ? r[0] : r[i]);
        const hasValid = y.some(val => val !== null && !isNaN(val));
        if (hasValid) {
            validColumns.push(i);
            columnIndexMap[cols[i]] = i;
        };
    }
    selectObject().innerHTML = '';
    if (validColumns.length > 1) {
        // Add "All" option
        const allOption = document.createElement('option');
        allOption.value = "All";
        allOption.textContent = "All";
        if (selectedColumnName === "All") { allOption.selected = true; }
        selectObject().appendChild(allOption);
    }
    // Add other options
    validColumns.forEach(i => {
        const colName = cols[i];
        const opt = document.createElement('option');
        opt.value = colName;
        opt.textContent = colName;
        if (colName === selectedColumnName) { opt.selected = true; }
        selectObject().appendChild(opt);
    })
    // Update global variable
    setGlobalChartData({ data, chartTitle, titleX, titleY, validColumns, columnIndexMap, swap });
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
        // const y = rows.map(r => swap ? r[0] : r[i]);
        const y = rows.map(r => toNumber(swap ? r[0] : r[i]));
        // const xVals = swap ? rows.map(r => r[i]) : x;
        const xVals = swap ? rows.map(r => toNumber(r[i])) : x;    
        const t = n <= 1 ? 0 : traceIndex / (n - 1);
        const color = interpolateJet(1-t);
        traces.push({
            x: xVals, y: y, name: cols[i],
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
    Plotly.purge(chartDiv()); // Clear the chart
    Plotly.newPlot('myChart', traces, layout, {responsive: true});
    Plotly.Plots.resize(chartDiv()); // Resize the chart
    // Update the header and maintain the close button
    plotTitle().innerHTML = chartTitle;
    swap = false; plotWindow().style.display = "flex"; // Show the chart
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
            row += `,${chartDiv().data[j].y[i]}`;
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
            row.push(chartDiv().data[j].y[i]);
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
