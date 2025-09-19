import { fillTable, getDataFromTable, removeRowFromTable, deleteTable, copyPaste } from "./tableManager.js";
import { csvUploader, mapPicker, renderProjects, pointUpdate, updateTable, plotTable, sendQuery } from "./tableManager.js";
import { saveProject, toUTC, timeStepCalculator } from "./projectSaver.js";

const projectName = () => document.getElementById('project-name');
const projects = () => document.getElementById("project-list");
const projectCreator = () => document.getElementById('create-project-button');
const sectionTab = () => document.getElementById('parent-tab');
const sectionDescription = () => document.getElementById('desription-tab');
const hydFilename = () => document.getElementById("hyd-filename");
const nLayers = () => document.getElementById("n-layer");
const referenceTime = () => document.getElementById("reference-time");
const startTime = () => document.getElementById("start-time");
const stopTime = () => document.getElementById("stop-time");
const sourceContainer = () => document.getElementById("source-sink-container");
const sourceTable = () => document.getElementById("source-sink-table");


let projectList = [];

function setupTabs(root) {
    const buttonPanels = root.querySelectorAll('#main-tabs button');
    const panels = root.querySelectorAll('.main-panel');
    const radioBtns = root.querySelectorAll('.row-radio');
    const radioPanels = root.querySelectorAll('.radio-panel');
    const checkboxBtns = root.querySelectorAll('.row-checkbox');    
    function activateSubButton(target, selectedPanel){
        const name = target.getAttribute('data-tab');
        const contents = selectedPanel.querySelectorAll('.tabpanel');
        const subButtons = selectedPanel.querySelectorAll('.tab-btn');
        // Show corresponding panel and hide others
        contents.forEach(p => {
            const panelNameActive = p.getAttribute('data-panel') === name;
            p.setAttribute('aria-hidden', String(!panelNameActive));
        })
        subButtons.forEach(btn => {
            btn.setAttribute('aria-selected', String(btn === target));
        });
    }
    function activate(target){
        const name = target.getAttribute('data-tab');
        // Set button aria-selected (highlighted)
        buttonPanels.forEach(btn => btn.setAttribute('aria-selected', String(btn === target)));
        // Show corresponding panel and hide others
        panels.forEach(p => {
            const panelNameActive = p.getAttribute('data-panel') === name;
            p.setAttribute('aria-hidden', String(!panelNameActive));
        })
        // Get sub-buttons in the selected panel
        const selectedPanel = root.querySelector(`[data-panel="${name}"]`);
        if(!selectedPanel) return;
        // Process radio
        const radios = selectedPanel.querySelectorAll('input[type="radio"]');
        if (radios.length > 0) {
            const checkedRadio = Array.from(radios).find(r => r.checked);
            if (checkedRadio) {
                // Select the checked radio
                radioSelector(checkedRadio.closest('.row-radio'));
            } else {
                // fallback: Select the first radio
                radios[0].checked = true;
                radioSelector(radios[0].closest('.row-radio'));
            }
        }
        const subButtonPanels = selectedPanel.querySelectorAll('.tab-btn');
        if(subButtonPanels.length === 0) return;
        const selectedSubBtn = Array.from(subButtonPanels).find(btn => btn.getAttribute('aria-selected') === "true");
        const firstSubBtn = selectedSubBtn || subButtonPanels[0];
        // Highlight first sub-button
        subButtonPanels.forEach(btn => btn.setAttribute('aria-selected', String(btn === firstSubBtn)));
        // Show corresponding sub-panel
        activateSubButton(firstSubBtn, selectedPanel);
        // Click to change sub-tab
        subButtonPanels.forEach(btn => {
            btn.addEventListener('click', () => { activateSubButton(btn, selectedPanel); });
        });
    }
    function radioSelector(target){
      const name = target.getAttribute('data-tab');
      // Show corresponding panel and hide others
      radioPanels.forEach(p => {
        p.style.display = (p.getAttribute('data-panel')!==name)?'none':'block';
      })
    }
    function checkboxSelector(target){
        const name = target.getAttribute('data-tab');
        const checkObj = target.querySelector('input');
        const panel = root.querySelectorAll(`[data-panel="${name}"]`);
        if(panel.length === 0) return;
        panel.forEach(p => {
            p.style.display = checkObj.checked ? 'flex' : 'none';
        })
    }
    // Show Simulator panel
    if(buttonPanels.length > 0) activate(buttonPanels[0]);
    // Click to change tab
    buttonPanels.forEach(btn => {
        btn.addEventListener('click', () => { activate(btn); });
    });
    // Change Radio button
    radioBtns.forEach(btn => {
        btn.addEventListener('click', () => { radioSelector(btn); });
    });
    // Change checkbox button
    checkboxBtns.forEach(box => {
        box.addEventListener('change', () => { checkboxSelector(box); });
    });
}

async function getProjectList(){
    const data = await sendQuery('select_project', {filename: '', key: 'getProjects', folder_check: ''});
    if (data.status === "ok") projectList = data.content;
}

function updateOption(){














    // Check function to run water quality simulation
    document.querySelectorAll('.wq-simulation').forEach(btn => {
        btn.addEventListener('click', async () => {
            const name = projectName().value.trim();
            if (!name || name === '') { alert('Please define project.'); return; }
            const hydPath = hydFilename().value.trim();
            if (!hydPath || hydPath === '') { alert('Please define hydrological (*.hyd) file.'); return; }
            const key = btn.dataset.info;
            const fileName = document.getElementById(key).value.trim();
            if (!fileName || fileName === '') { alert("The field 'Name' is required"); return; }
            const refTime = referenceTime().value.trim();
            if (!refTime || refTime === '') { alert("The field 'Reference time' is required"); return; }
            const startTime = startTime().value.trim(), stopTime = stopTime().value.trim();
            if (!startTime || startTime === '' || !stopTime || stopTime === '') { alert("The fields 'Start time' and 'Stop time' are required"); return; }
            window.parent.postMessage({type: 'showOverlay', message: `Running water quality simulation for '${fileName}'.\nPlease wait...`}, '*');
            const data = await sendQuery('run_wq', {projectName: name, key: key, hydName: hydPath, fileName: fileName,
                refTime: toUTC(refTime), startTime: toUTC(startTime), stopTime: toUTC(stopTime)});
            window.parent.postMessage({type: 'hideOverlay'}, '*');
            alert(data.message);
        });
    });
}

function initializeProject(){
    // Update project name
    projectName().addEventListener('input', (e) => { 
        const value = e.target.value.trim();
        if (value === '') {
            sectionTab().style.display = "none"; sectionDescription().style.display = "block";
        }
        renderProjects(projects(), projectList, value);
    });
    projectName().addEventListener('blur', () => { projects().style.display = "none"; });
    // Create new project
    projectCreator().addEventListener('click', async () => {
        const name = projectName().value.trim();
        if (!name || name.trim() === '') { alert('Please define project.'); return; }
        // Show tabs
        sectionTab().style.display = "block"; sectionDescription().style.display = "none";
        // Find .hyd file
        const data = await sendQuery('select_hyd', {projectName: name});
        if (data.status === "error") {alert(data.message); return;}
        // Assign values
        hydFilename().value = data.content.filename;
        nLayers().value = data.content.n_layers; referenceTime().value = data.content.ref_time;
        startTime().value = data.content.start_time; stopTime().value = data.content.stop_time;
        // Get source data if exist
        if (data.content.sources.length > 0) {
            sourceContainer().style.display = "block";
            fillTable(data.content.sources, sourceTable());
            // Add new markers
            window.parent.postMessage({type: 'addWQSource', sources: data.content.sources}, '*');
        } else sourceContainer().style.display = "none";
    });
}

await getProjectList(); initializeProject();
setupTabs(document); updateOption();