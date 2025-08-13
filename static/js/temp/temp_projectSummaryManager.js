import { closeMenu } from './temp_uiManager.js';
import { loadData } from './utils.js';

let Dragging = false;

const summaryWindow = () => document.getElementById("summaryWindow");
const summaryHeader = () => document.getElementById("summaryHeader");
const projectSummaryOption = () => document.getElementById('projectSummaryOption');
const closeSummaryOption = () => document.getElementById('closeSummaryOption');


async function openProjectSummary(filename) {
    const data = await loadData(filename, 'summary');
    const content = document.getElementById("summaryContent");
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
        content.innerHTML = html;
        // Open the summary window
        summaryWindow().style.display = "flex";
    } else { summaryWindow().style.display = "none";}
    closeMenu();
}

export function toggleProjectSummary(filename) {
    projectSummaryOption().addEventListener('click', () => {
        openProjectSummary(filename);
    });
}

export function closeProjectSummary() {
    closeSummaryOption().addEventListener('click', () => {
        summaryWindow().style.display = "none";
    })
}

// Move summary window
export function projectSummaryEvents() {
    let offsetX = 0, offsetY = 0;
    summaryHeader().addEventListener("mousedown", function(e) {
        // setIsDragging_infor(true);
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
};