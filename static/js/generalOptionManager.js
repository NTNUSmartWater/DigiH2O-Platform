import { updatePointManager, updatePathManager, updateStationManager } from "./queryManager.js";
import { loadData } from './utils.js';
import { plotChart } from "./chartManager.js";

const summaryWindow = () => document.getElementById("summaryWindow");
const summaryHeader = () => document.getElementById("summaryHeader");
const summaryContent = () => document.getElementById("summaryContent");
const projectSummaryOption = () => document.getElementById('projectSummaryOption');
const closeSummaryOption = () => document.getElementById('closeSummaryOption');

let Dragging = false;

export function generalObtionsManager(summaryProjectFileName=null, stationFileName=null){
    projectSummaryEvents(summaryProjectFileName);
    updateStationManager(stationFileName);
    updatePointManager();
    updatePathManager();
    thermoclinePlot();
}

// ============================ Project Manager ============================
function projectSummaryEvents(filename){
    projectSummaryOption().addEventListener('click', () => {
        openProjectSummary(filename);
    });
    closeSummaryOption().addEventListener('click', () => {
        summaryWindow().style.display = "none";
    });
    // Move summary window
    let offsetX = 0, offsetY = 0;
    summaryHeader().addEventListener("mousedown", function(e) {
        Dragging = true;
        offsetX = e.clientX - summaryWindow().offsetLeft;
        offsetY = e.clientY - summaryWindow().offsetTop;
    });
    summaryHeader().addEventListener("mouseup", function() { Dragging = false; });
    document.addEventListener("mousemove", function(e) {
        if (Dragging) {
            summaryWindow().style.left = (e.clientX - offsetX) + "px";
            summaryWindow().style.top = (e.clientY - offsetY) + "px";
        }
    });
}

async function openProjectSummary(filename) {
    const data = await loadData(filename, 'summary');
    const currentDisplay = window.getComputedStyle(summaryWindow()).display;
    if (currentDisplay === "none") {
        // Create a table to display the summary
        let html = `<table><thead>
            <tr>
            <th style="text-align: center;">Parameter</th>
            <th style="text-align: center;">Value</th>
            </tr>
        </thead><tbody>`;
        data.content.forEach(item => {
            html += `
                <tr>
                    <td>${item.parameter}</td>
                    <td>${item.value}</td>
                </tr>
            `;
        });
        html += `</tbody></table>`;
        summaryContent().innerHTML = html;
        // Open the summary window
        summaryWindow().style.display = "flex";
    } else { summaryWindow().style.display = "none";}
}

// ============================ Thermocline Plot ============================
function thermoclinePlot(){
    // Set function for plot using Plotly
    document.querySelectorAll('.thermocline').forEach(plot => {
        plot.addEventListener('click', () => {
            const [filename, titleY, chartTitle] = plot.dataset.info.split('|');
            plotChart(filename, 'thermocline', chartTitle, 'Temperature (°C)', titleY, true);
        });
    });
}
