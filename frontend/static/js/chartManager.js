import { startLoading, showLeafletMap} from "./mapManager.js";
import { loadData, interpolateJet, splitLines, getColors, valueFormatter } from "./utils.js";
import { getState, setState } from "./constants.js";
import { sendQuery } from "./tableManager.js";
import { deActivePathQuery, moveWindow } from "./generalOptionManager.js";

let Dragging = false, colorTicks = [], colorTickLabels = [], animationToken = 0;
let animating = false, frameIndex = 0, duration, nColors;

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
// Profile
export const profileWindow = () => document.getElementById('profileWindow');
const profileWindowHeader = () => document.getElementById('profileWindowHeader');
export const profileCloseBtn = () => document.getElementById('closeProfileWindow');
const chartDivProfile = () => document.getElementById('chartDiv'); 
const playPauseBtn = () => document.getElementById('chartPlayPauseBtn'); 
const colorCombo = () => document.getElementById('chartColorCombo'); 
const colorComboLabel = () => document.getElementById('chartColorComboLabel'); 
const minValue = () => document.getElementById('chartMinValue'); 
const minLabel = () => document.getElementById('chart-min-label'); 
const maxValue = () => document.getElementById('chartMaxValue'); 
const maxLabel = () => document.getElementById('chart-max-label'); 
const durationValue = () => document.getElementById('chartDurationValue'); 
const timeSlider = () => document.getElementById('timeSlider');
const timeLabel = () => document.getElementById('timeLabel');
const timeLabelStart = () => document.getElementById('timeLabelStart');
const timeLabelEnd = () => document.getElementById('timeLabelEnd');


export async function plotChart(query, key, chartTitle, titleX, titleY) {
    startLoading('Preparing Data for Chart. Please wait...'); // Show spinner
    const data = await loadData(query, key, getState().projectName); // Load data
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
        Dragging = false; 
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
    closePlotOption().addEventListener('click', () => { 
        plotWindow().style.display = "none"; deActivePathQuery();
    });
    profileCloseBtn().addEventListener('click', () => { 
        animating = false; playPauseBtn().textContent = '▶ Play';
        frameIndex = 0; animationToken++;
        // 2. Remove Plotly chart safely
        const div = chartDivProfile();
        try {
            if (div && div.data) Plotly.purge(div);
        } catch(e) { alert("Plotly purge error:" + e); }
        // Disconnect resize observer
        if (profileWindow()._resizeObserver) {
            profileWindow()._resizeObserver.disconnect(); 
            profileWindow()._resizeObserver = null;
        }
        // 4. Remove ALL listeners on buttons & sliders
        removeAllListeners(playPauseBtn()); removeAllListeners(timeSlider());
        removeAllListeners(durationValue()); removeAllListeners(colorCombo());
        profileWindow().style.display = "none"; deActivePathQuery();
    });
    moveWindow(profileWindow, profileWindowHeader); 
}

function removeAllListeners(el) {
    const clone = el.cloneNode(true);
    el.parentNode.replaceChild(clone, el);
    return clone;
}

function updateChart() {
    const checkboxes = checkboxList().querySelectorAll('input[type="checkbox"]');
    const selectedColumns = Array.from(checkboxes)
        .filter(cb => cb.checked && cb.value !== 'All').map(cb => cb.value);
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
    if (!selectedColumns) {
        selectedColumns = Array.from(checkboxInputs)
            .filter(cb => cb.checked && cb.value !== 'All').map(cb => cb.value);
    }
    const allCheckbox = Array.from(checkboxInputs).find(cb => cb.value === 'All');
    let drawColumns, traceIndex = 0;
    if (allCheckbox && allCheckbox.checked) drawColumns = cols.slice(1);
    else drawColumns = selectedColumns;
    if (drawColumns.length === 0) { Plotly.purge(chartDiv()); return; }
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

export function numberFormatter(num, decimals) {
    if (num === null || num === undefined || isNaN(num)) return '';
    if (num === 0) return '0';
    if (Math.abs(num) < 1e-3 || Math.abs(num) >= 1e6) { return num.toExponential(decimals); }
    return num.toFixed(decimals);
}

// Export chart data to new tab as CSV format
function viewData() {
    const data = chartDiv().data?.[0];
    if (!data) { alert("No data to view."); return; }
    // Get the y values
    const numTraces = chartDiv().data.length;
    const title = chartDiv().layout?.title?.text || "Chart";
    const titleText = typeof title === "string"
        ? (title.includes(':') ? title.split(':')[1].trim() : title) : "Chart";
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
    if (!data) { alert("No data to save."); return; }
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
    const table = [headers], numPoints = chartDiv().data[0].x.length;
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

export function plotProfileSingleLayer(pointContainer, polygonCentroids, title, titleY, titleX='Distance (m)') {
    const interpolatedPoints = splitLines(pointContainer, polygonCentroids, 20).map(([dist, val]) => [dist, val]);
    const input = { columns: [titleX, titleY], data: interpolatedPoints };
    drawChart(input, title, titleX, titleY, false);
}

export function plotProfileMultiLayer(key, query, data, title, unit) { 
    animationToken++;
    const myToken = animationToken;
    chartDivProfile().style.border = "1px solid #aaa"; 
    chartDivProfile().style.borderRadius = "10px"; 
    chartDivProfile().style.boxShadow = "0 2px 8px rgba(0,0,0,0.15)"; 
    if (profileWindow()._resizeObserver) profileWindow()._resizeObserver.disconnect(); 
    colorCombo().style.display = "block"; minValue().style.display = "block"; maxValue().style.display = "block";
    colorComboLabel().style.display = "block"; minLabel().style.display = "block"; maxLabel().style.display = "block";
    const { timestamps, distance, values, depths, local_minmax } = data;
    minValue().value = valueFormatter(local_minmax[0], 1e-3); maxValue().value = valueFormatter(local_minmax[1], 1e-3);
    nColors = parseInt(colorCombo().value);
    // Set up time slider
    timeSlider().min = 0; timeSlider().max = timestamps.length - 1;
    timeSlider().step = 1; timeSlider().value = 0;
    timeLabelStart().textContent = `Start: ${timestamps[0]}`;
    timeLabelEnd().textContent = `End: ${timestamps[timestamps.length - 1]}`;
    timeLabel().textContent = `Time: ${timestamps[0]}`;
    // Render plot
    profileWindow()._resizeObserver = renderPlot(chartDivProfile(), distance, depths, 
            values, local_minmax[0], local_minmax[1], nColors, title, unit);
    // Change header title of window
    profileWindowHeader().childNodes[0].nodeValue = 'Profile Plot';
    // Update a single frame
    async function updateFrame(index) {
        if (myToken !== animationToken) return;
        const queryContents = { key: key, query: query, idx: index, projectName: getState().projectName };
        const data = await sendQuery('select_meshes', queryContents);
        if (data.status === "error") { 
            alert(data.message); animating = false;
            playPauseBtn().textContent = '▶ Play'; return;
        }
        const { values, local_minmax } = data.content;
        minValue().value = valueFormatter(local_minmax[0], 1e-3); 
        maxValue().value = valueFormatter(local_minmax[1], 1e-3);
        nColors = parseInt(colorCombo().value);
        const discreteColors = getColors(nColors);
        const colorScale = [], step = 1 / nColors;
        for (let i = 0; i < nColors; i++) {
            colorScale.push([i * step, discreteColors[i]]);
            colorScale.push([(i + 1) * step, discreteColors[i]]);
        }
        // Update the frame
        colorTicks = colorbarTicks(local_minmax[0], local_minmax[1], nColors);
        colorTickLabels = colorTicks.map(v => valueFormatter(v, 1e-3));
        await Plotly.update(chartDivProfile(), { z: [values], zmin: [local_minmax[0]], 
            zmax: [local_minmax[1]], colorscale: [colorScale], showscale: [true], 
            colorbar: [{ title: { text: unit, font: { color: 'black' } }, tickvals: colorTicks, 
                ticktext: colorTickLabels, tickfont: { color: 'black' } }]
        }, {}, [0]);
        // Update time slider
        timeSlider().value = index; timeLabel().textContent = `Time: ${timestamps[index]}`;
    }
    // === Play / Pause control === 
    async function playAnimation() { 
        duration = parseFloat(durationValue().value)*1000
        while (animating && frameIndex < timestamps.length && myToken === animationToken) { 
            await updateFrame(frameIndex);
            frameIndex++;
            await new Promise(r => setTimeout(r, duration)); 
        }
        if (myToken !== animationToken) return;
        if (frameIndex >= timestamps.length) { 
            animating = false; playPauseBtn().textContent = '▶ Play'; 
            frameIndex = 0; // Reset index
        }
    }
    playPauseBtn().onclick = () => { 
        if (!animating){ 
            animating = true; playPauseBtn().textContent = '⏸ Pause'; 
            playAnimation(); 
        } else { animating = false; playPauseBtn().textContent = '▶ Play'; } 
    }
    // === Slider control === 
    timeSlider().addEventListener('input', resetAnimation);
    // === Duration control ===
    durationValue().addEventListener('change', resetAnimation);
    // === Color control === 
    colorCombo().addEventListener('change', async() => { 
        animating = false; playPauseBtn().textContent = '▶ Play';
        const queryContents = { key: key, query: query, idx: frameIndex, projectName: getState().projectName };
        const refreshed = await sendQuery('select_meshes', queryContents);
        if (refreshed.status === "error") { alert(data.message); return; }
        const { values, local_minmax } = refreshed.content;
        minValue().value = valueFormatter(local_minmax[0], 1e-3); 
        maxValue().value = valueFormatter(local_minmax[1], 1e-3);
        renderPlot(chartDivProfile(), distance, depths, values, local_minmax[0],
            local_minmax[1], parseInt(colorCombo().value), title, unit); 
    })
    profileWindow().style.display = "flex";
}

function resetAnimation(e) { 
    animating = false; playPauseBtn().textContent = '▶ Play'; 
    if (e) { frameIndex = parseInt(e.target.value); }
    else { frameIndex = 0; }
}

function renderPlot(plotDiv, distance, depths, values, vmin, vmax, nColors, title, unit){
    const discreteColors = getColors(nColors);
    const xLabels = distance.map(String), reversedDepths = [...depths];
    const reverseDepth = reversedDepths.every(d => d >= 0);
    // Build colorScale for Plotly (discrete)
    const colorScale = [], step = 1 / nColors;
    for (let i = 0; i < nColors; i++) {
        colorScale.push([i * step, discreteColors[i]]);
        colorScale.push([(i + 1) * step, discreteColors[i]]);
    }
    // === Layout ===
    let tickvals = xLabels, ticktext = xLabels;
    const maxXTicks = 20;
    if (xLabels.length > maxXTicks) {
        const step = Math.ceil(xLabels.length / maxXTicks);
        tickvals = xLabels.filter((_, i) => i % step === 0);
        ticktext = tickvals;
    }
    const layout = { title: { text: title, font: { color: 'black', weight: 'bold', size: 20 } },
        paper_bgcolor: '#c2bdbdff', plot_bgcolor: '#c2bdbdff',
        xaxis: {
            title: {text: 'Distance (m)', font: { color: 'black' }}, 
            type: 'category', automargin: true, mirror: true, tickmode: 'array',
            showgrid: false, tickvals: tickvals, ticktext: ticktext,
            showline: true, linewidth: 1, linecolor: 'black', tickfont: { color: 'black' }
        },
        yaxis: {
            title: {text: 'Depth (m)', font: { color: 'black' }}, autorange: reverseDepth ? 'reversed' : true,
            mirror: true, showline: true, linewidth: 1, linecolor: 'black', 
            showgrid: false, tickfont: { color: 'black' }, tickmode: 'auto'
        },
        margin: { l: 70, r: true ? 60 : 20, t: 50, b: 50 }
    };
    const config = {
        responsive: true, displaylogo: false, displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    };
    // Generate colorbar ticks
    colorTicks = colorbarTicks(vmin, vmax, nColors);
    colorTickLabels = colorTicks.map(v => valueFormatter(v, 1e-3));
    // === Plot ===
    Plotly.purge(plotDiv);
    Plotly.newPlot(plotDiv, [{
        z: values, x: xLabels, y: reversedDepths, type: 'heatmap', zsmooth: 'best',
        colorscale: colorScale, zmin: vmin, zmax: vmax, showscale: true,
        colorbar: {
            title: { text: unit, font: { color: 'black' }}, tickfont: { color: 'black' },
            tickvals: colorTicks, ticktext: colorTickLabels
        }
    }], layout, config).then(() => {
        const resizeObserver = new ResizeObserver(() => Plotly.Plots.resize(plotDiv));
        resizeObserver.observe(plotDiv);
        return resizeObserver;
    });
}

function colorbarTicks(min, max, numStops){
    if (Math.abs(max - min) < 1e-4) return [min];
    const ticks = [], step = (max - min) / (numStops - 1);
    for (let i = 0; i < numStops; i++) {
        ticks.push(min + i * step);
    }
    return ticks;
}

export function thermoclinePlotter(key, data, name, titleX, titleY, chartTitle) {
    animationToken++;
    const myToken = animationToken;
    chartDivProfile().style.border = "1px solid #aaa"; 
    chartDivProfile().style.borderRadius = "10px"; 
    chartDivProfile().style.boxShadow = "0 2px 8px rgba(0,0,0,0.15)"; 
    if (profileWindow()._resizeObserver) profileWindow()._resizeObserver.disconnect();
    // Hide components
    colorCombo().style.display = "none"; minValue().style.display = "none"; maxValue().style.display = "none";
    colorComboLabel().style.display = "none"; minLabel().style.display = "none"; maxLabel().style.display = "none";
    let animating = false, frameIndex = 0, duration;
    const { timestamps, depths, values } = data;
    // Set up time slider
    timeSlider().min = 0; timeSlider().max = timestamps.length - 1;
    timeSlider().step = 1; timeSlider().value = 0;
    timeLabelStart().textContent = `Start: ${timestamps[0]}`;
    timeLabelEnd().textContent = `End: ${timestamps[timestamps.length - 1]}`;
    timeLabel().textContent = `Time: ${timestamps[0]}`;
    // Render plot
    profileWindow()._resizeObserver = renderThermocline(key, chartDivProfile(), values,
            depths, name, titleX, titleY, chartTitle);
    // Change header title of window
    profileWindowHeader().childNodes[0].nodeValue = 'Thermocline Plot';
    // Update a single frame
    async function updateFrame(index) {
        if (myToken !== animationToken) return;
        const queryContents = { idx: index, type: 'thermocline_update', projectName: getState().projectName };
        const updateData = await sendQuery('select_thermocline', queryContents);
        if (updateData.status === "error") { 
            alert(updateData.message); animating = false;
            playPauseBtn().textContent = '▶ Play'; return;
        }
        const values = updateData.content;
        // Update the frame
        await Plotly.update(chartDivProfile(), { x: [values], y: [depths]}, {}, [0]);
        // Update time slider
        timeSlider().value = index; timeLabel().textContent = `Time: ${timestamps[index]}`;
    }
    // === Play / Pause control === 
    async function playAnimation() { 
        duration = parseFloat(durationValue().value)*1000
        while (animating && frameIndex < timestamps.length && myToken === animationToken) {
            await updateFrame(frameIndex);
            frameIndex++;
            await new Promise(r => setTimeout(r, duration)); 
        }
        if (myToken !== animationToken) return;
        if (frameIndex >= timestamps.length) { 
            animating = false; playPauseBtn().textContent = '▶ Play'; 
            frameIndex = 0; // Reset index
        }
    }
    playPauseBtn().onclick = () => { 
        if (!animating){ 
            animating = true; playPauseBtn().textContent = '⏸ Pause'; 
            playAnimation(); 
        } else { 
            animating = false; playPauseBtn().textContent = '▶ Play'; 
        } 
    };
    // === Slider control === 
    timeSlider().addEventListener('input', async(e) => {
        animating = false; playPauseBtn().textContent = '▶ Play';
        frameIndex = parseInt(e.target.value);
    });
    // === Duration control ===
    durationValue().addEventListener('change', () => { 
        animating = false; playPauseBtn().textContent = '▶ Play';
    });
    profileWindow().style.display = "flex"; setState({isThemocline: false});
}

function renderThermocline(key, plotDiv, xValues, yValues, legend, xTitle, yTitle, title){
    // === Layout ===
    const layout = { title: { text: title, font: { color: 'black', weight: 'bold', size: 20 } },
        paper_bgcolor: '#c2bdbdff', plot_bgcolor: '#c2bdbdff', showlegend: true,
        xaxis: {
            title: {text: xTitle, font: { color: 'black' }, standoff: 10}, type: 'category', zeroline: false,
            automargin: true, mirror: true, showgrid: false, tickmode: 'auto', ticks: 'outside',
            showline: true, linewidth: 1, linecolor: 'black', tickfont: { color: 'black' }
        },
        yaxis: {
            title: {text: yTitle, font: { color: 'black' }}, automargin: true, zeroline: false,
            mirror: true, showline: true, linewidth: 1, linecolor: 'black', 
            autorange: key === 'thermocline_hyd' ? 'reversed' : true,
            showgrid: false, tickfont: { color: 'black' }, tickmode: 'auto', ticks: 'outside'
        },
        margin: { l: 70, r: true ? 60 : 20, t: 50, b: 50 }
    };
    const config = {
        responsive: true, displaylogo: false, displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    };
    // === Trace ===
    const trace = { x: xValues, y: yValues, mode: 'lines',
        type: 'scatter', line: { color: 'blue', width: 2 }, name: legend
    };
    // === Plot ===
    Plotly.purge(plotDiv);
    Plotly.newPlot(plotDiv, [trace], layout, config).then(() => {
        const resizeObserver = new ResizeObserver(() => Plotly.Plots.resize(plotDiv));
        resizeObserver.observe(plotDiv);
        return resizeObserver;
    });
}
