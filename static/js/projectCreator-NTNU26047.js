import { fillTable, getDataFromTable, removeRowFromTable, tableClear, deleteTable, copyPaste } from "./tableManager.js";
import { csvUploader, mapPicker, renderProjects } from "./tableManager.js";
import { saveProject } from "./projectSaver.js";


const projectName = () => document.getElementById('project-name');
const projects = () => document.getElementById("project-list");
const projectCreator = () => document.getElementById('create-project-button');
const saveProjectBtn = () => document.getElementById('complete-button');
const getLocation = () => document.getElementById('location-picker');
const latitude = () => document.getElementById('latitude');
const nLayers = () => document.getElementById('n-layer');
const gridPath = () => document.getElementById('unstructured-grid');
const referenceDate = () => document.getElementById('reference-date');
const startDate = () => document.getElementById('start-date');
const stopDate = () => document.getElementById('stop-date');
const userTimestepDate = () => document.getElementById('user-time-step-date');
const userTimestepTime = () => document.getElementById('user-time-step-time');
const nodalTimestepDate = () => document.getElementById('nodal-update-interval-date');
const nodalTimestepTime = () => document.getElementById('nodal-update-interval-time');
const obsPointName = () => document.getElementById('observation-point');
const obsPointLatitude = () => document.getElementById('observation-point-latitude');
const obsPointLongitude = () => document.getElementById('observation-point-longitude');
const obsPointPicker = () => document.getElementById('observation-point-picker');
const obsPointSave = () => document.getElementById('observation-point-save');
const obsPointRemove = () => document.getElementById('observation-point-remove');
const obsPointUpload = () => document.getElementById('observation-point-csv');
const obsPointTable = () => document.getElementById('observation-point-table');
const crossSectionName = () => document.getElementById('observation-cross-section');
const crossSectionPicker = () => document.getElementById('observation-cross-section-picker');
const crossSectionRemove = () => document.getElementById('observation-cross-section-remove');
const crossSectionTable = () => document.getElementById('observation-cross-section-table');
const boundaryName = () => document.getElementById('boundary-name');
const boundaryPicker = () => document.getElementById('boundary-picker');
const boundaryTable = () => document.getElementById('boundary-table');
const boundaryRemove = () => document.getElementById('boundary-remove');
const boundarySelector = () => document.getElementById('option-boundary-edit');
const boundaryTypeSelector = () => document.getElementById('option-boundary-type');
const boundaryEditTable = () => document.getElementById('boundary-edit-table');
const boundaryEditUpdate = () => document.getElementById('boundary-update');
const boundaryEditRemove = () => document.getElementById('boundary-edit-remove');
const boundarySelectorView = () => document.getElementById('option-boundary-type-view');
const boundaryViewContainer = () => document.getElementById('boundary-textarea-container');
const boundaryText = () => document.getElementById('boundary-data-view');
const sourceName = () => document.getElementById('source-name');
const sourceOptionNew = () => document.getElementById('source-sink-new');
const sourceOptionExist = () => document.getElementById('source-sink-exist');
const sourceOptionList = () => document.getElementById('source-sink-list');
const sourceOptionPicker = () => document.getElementById('source-picker');
const sourceLatitude = () => document.getElementById('source-latitude');
const sourceLongitude = () => document.getElementById('source-longitude');
const sourceTable = () => document.getElementById('source-table');
const sourceSelectionList = () => document.getElementById('option-source');
const sourceUpload = () => document.getElementById('source-csv-file');

const sourcePlotBtn = () => document.getElementById('plot-source-btn');
const sourceSaveBtn = () => document.getElementById('save-source-btn');

let projectList = [];


// const hisIntervalDate = () => document.getElementById('his-ouput-interval-date');
// const hisIntervalTime = () => document.getElementById('his-ouput-interval-time');
// const mapIntervalDate = () => document.getElementById('map-ouput-interval-date');
// const mapIntervalTime = () => document.getElementById('map-ouput-interval-time');
// const wqIntervalDate = () => document.getElementById('water-quality-ouput-interval-date');
// const wqIntervalTime = () => document.getElementById('water-quality-ouput-interval-time');
// const rstIntervalDate = () => document.getElementById('restart-interval-date');
// const rstIntervalTime = () => document.getElementById('restart-interval-time');
// const statisticDate = () => document.getElementById('statistic-ouput-interval-date');
// const statisticTime = () => document.getElementById('statistic-ouput-interval-time');
// const timingDate = () => document.getElementById('timing-statistic-ouput-interval-date');
// const timingTime = () => document.getElementById('timing-statistic-ouput-interval-time');

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
        // Activate first sub-button in the selected panel
        const defaultRadio = selectedPanel.querySelectorAll('.row-radio');
        if(defaultRadio.length>0) radioSelector(defaultRadio[0]);
        // sourceStart().value = startDate().value; sourceStop().value = stopDate().value;
        const subButtonPanels = selectedPanel.querySelectorAll('.tab-btn');
        if(subButtonPanels.length === 0) return;
        const firstSubBtn = subButtonPanels[0];
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
    const response = await fetch('/select_project', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: '', key: 'getProjects'})});
    const data = await response.json();
    if (data.status === "ok") projectList = data.content;
}
function sourceChange(target){
    const check = target.checked;
    if (!check) return;
    sourceLatitude().value = ''; sourceLongitude().value = '';
    // Clear table and name
    const tbody = sourceTable().querySelector("tbody");
    tbody.innerHTML = ""; sourceName().value = ''; sourceUpload().value = '';
}

async function fileUploader(target, projectName, gridName){
    if (projectName === '') return;
    window.parent.postMessage({type: 'showOverlay', message: 'Uploading grid to project...'}, '*');
    const file = target.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('projectName', projectName);
    formData.append('gridName', gridName);
    const response = await fetch('/upload_data', { method: 'POST', body: formData });
    const data = await response.json();
    window.parent.postMessage({type: 'hideOverlay'}, '*');
    if (data.status === "error") {alert(data.message), target.value = ''; return;}
}


function updateOption(){
    // Update location
    mapPicker(getLocation(), 'pickLocation');
    mapPicker(obsPointPicker(), 'pickPoint', () => getDataFromTable(obsPointTable(), true));
    mapPicker(crossSectionPicker(), 'pickCrossSection', () => getDataFromTable(crossSectionTable(), true));
    mapPicker(boundaryPicker(), 'pickBoundary', () => getDataFromTable(boundaryTable(), true));
    mapPicker(sourceOptionPicker(), 'pickSource');
    // Event when user uploads CSV file
    csvUploader(obsPointUpload(), obsPointTable(), 3);
    csvUploader(sourceUpload(), sourceTable(), 5, false, sourceName(), sourceLatitude(), sourceLongitude());
    // Upload file to server
    gridPath().addEventListener('change', () =>  fileUploader(gridPath(), projectName().value, 'FlowFM_net.nc'));
    // Copy and paste to tables
    copyPaste(obsPointTable(), 3);
    copyPaste(boundaryEditTable(), 2);
    copyPaste(sourceTable(), 5);
    // Get data from main page
    window.addEventListener('message', (event) => {
        if (event.data.type === 'locationPicked') {
            const lat = Number(event.data.content.lat).toFixed(1);
            latitude().value = lat;
        }
        if (event.data.type === 'pointPicked') {
            const lat = Number(event.data.content.lat).toFixed(12);
            const lon = Number(event.data.content.lng).toFixed(12);
            obsPointLatitude().value = lat; obsPointLongitude().value = lon;
            if (obsPointName().value.trim() === '') obsPointName().value = `Point_${Number(lat).toFixed(2)}_${Number(lon).toFixed(2)}`;
        }
        if (event.data.type === 'crossSectionPicked') {
            const content = event.data.content;
            let value = crossSectionName().value.trim();
            if (value === '') {
                value = `Cross-Section`; crossSectionName().value = value;
            }
            const data_arr = content.map((row, idx) => [`${value}_${idx + 1}`, Number(row.lat).toFixed(12), Number(row.lng).toFixed(12)]);
            fillTable(data_arr, crossSectionTable(), true);
        }
        if (event.data.type === 'boundaryPicked') {
            const content = event.data.content;
            let value = boundaryName().value.trim();
            if (value === '') {
                value = `Boundary`; boundaryName().value = value;
            }
            const data_arr = content.map((row, idx) => [`${value}_${idx + 1}`, Number(row.lat).toFixed(12), Number(row.lng).toFixed(12)]);
            fillTable(data_arr, boundaryTable(), true);
            // Update boundary option
            const options = data_arr.map(row => `<option value="${row[0]}">${row[0]}</option>`).join(' ');
            const defaultOption = `<option value="" selected>--- No selected ---</option>`;
            boundarySelector().innerHTML = defaultOption + options;
        }
        if (event.data.type === 'sourcePicked') {
            const content = event.data.content;
            let value = sourceName().value.trim();
            if (value === '') { value = `Source/Sink`; sourceName().value = value; }
            sourceLatitude().value = Number(content.lat).toFixed(16);
            sourceLongitude().value = Number(content.lng).toFixed(16);

            // const data_arr = content.map((row, idx) => [`${value}_${idx + 1}`, Number(row.lat).toFixed(12), Number(row.lng).toFixed(12)]);
        }



    });
    // Save point to table
    obsPointSave().addEventListener('click', () => {
        const name = obsPointName().value.trim();
        const lat = obsPointLatitude().value.trim();
        const lon = obsPointLongitude().value.trim();
        if (name === '' || lat === '' || lon === '' || isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
            alert('Please check name, latitude, and longitude of the observation point.'); return;}
        // Add to table
        const data_arr = [[name, lat, lon]];
        fillTable(data_arr, obsPointTable(), false);
        // Clear input
        obsPointName().value = ''; obsPointLatitude().value = ''; obsPointLongitude().value = '';
    });
    // Remove point from table
    obsPointRemove().addEventListener('click', () => {
        const name = obsPointName().value.trim();
        removeRowFromTable(obsPointTable(), name);
        obsPointName().value = '';
    });
    // Event when user change radio button for observation points
    tableClear(document.getElementById('observation-point-new'), obsPointTable());
    tableClear(document.getElementById('observation-point-exist'), obsPointTable());
    // Event when user delete
    deleteTable(crossSectionRemove(), crossSectionTable(), crossSectionName(), 'clearCrossSection');
    deleteTable(boundaryRemove(), boundaryTable(), boundaryName(), 'clearBoundary');
    deleteTable(boundaryEditRemove(), boundaryEditTable());
    // Update boundary option
    boundaryEditUpdate().addEventListener('click', async () => {
        const nameProject = projectName().value.trim();
        const nameBoundary = boundaryName().value.trim();
        const subBoundary = boundarySelector().value;
        const boundaryType = boundaryTypeSelector().value;
        const refDate = referenceDate().value;
        if (nameProject === '' || nameBoundary === '' || subBoundary === '' || boundaryType === '' || refDate === '') {
            alert('Please check: \n     1. Name of Boundary is required.' + '\n     2. Name of Sub-boundary is required.' +
                '\n     3. Boundary type is required.' + '\n     4. Reference date is required.'); return;
        }
        const refSimulation = new Date(`${refDate}`);
        const content = getDataFromTable(boundaryEditTable());
        if (content.rows.length === 0) {
            alert('No data in the table.'); return;
        }
        // Create boundary
        const response = await fetch('/update_boundary', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({projectName: nameProject, refDate: refSimulation,
            subBoundaryName: subBoundary, boundaryType: boundaryType, boundaryData: content.rows})});
        const data = await response.json();
        alert(data.message);
    })
    // View boundary condition
    boundarySelectorView().addEventListener('change', async () => {
        if (boundarySelectorView().value === '') {
            boundaryViewContainer().style.display = 'none'; return;
        }
        const type = boundarySelectorView().value;
        // Create boundary
        const response = await fetch('/view_boundary', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({projectName: nameProject, boundaryType: type})
        });
        const data = await response.json();
        if (data.status === "error") {
            boundaryViewContainer().style.display = 'none';
            alert(data.message); return;
        };
        console.log(data.content);
        boundaryText().value = ''; boundaryText().value = data.content;
        boundaryViewContainer().style.display = 'flex';
    });
    // Working on source/sink option
    sourceOptionNew().addEventListener('change', () => {
        sourceChange(sourceOptionNew());
        sourceStart().value = startDate().value; sourceStop().value = stopDate().value;
        sourceOptionPicker().style.display = 'block';
    });
    sourceOptionExist().addEventListener('change', () => {
        sourceChange(sourceOptionExist());
        sourceOptionPicker().style.display = 'none';
    });
    sourceOptionList().addEventListener('change', async () => {
        sourceChange(sourceOptionList());
        sourceOptionPicker().style.display = 'none';
        const response = await fetch('/get_files', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        });
        const data = await response.json();
        if (data.status === "error") { alert(data.message); return; }
        const sourceSelector = sourceSelectionList();
        sourceSelector.innerHTML = '';
        // Add hint to the velocity object
        const hint = document.createElement('option');
        hint.value = ''; hint.selected = true;
        hint.text = '- No Selection -'; 
        sourceSelector.add(hint);
        // Add options
        data.content.forEach(item => {
            const option = document.createElement('option');
            option.value = item; option.text = item;
            sourceSelector.add(option);
        });
    });
    // Select source from list
    sourceSelectionList().addEventListener('change', async () => {
        const name = sourceSelectionList().value;
        if (name === '') return;
        window.parent.postMessage({type: 'showOverlay', 
            message: 'Reading source/sink and exacting data to table...'}, '*'); // Show overlay
        const response = await fetch('/get_source', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filename: name})
        });
        const data = await response.json();
        if (data.status === "error") alert(data.message);
        sourceLatitude().value = data.content.lat;
        sourceLongitude().value = data.content.lon;
        sourceName().value = name;
        // Convert to 2D array
        const lines = data.content.data;
        const data_arr = lines.map(line => line.trim().split(","));
        fillTable(data_arr, sourceTable());
        window.parent.postMessage({type: 'hideOverlay'}, '*');  // Hide overlay
    });
    // Plot source
    sourcePlotBtn().addEventListener('click', () => {
        // Get data from table
        const {columns, rows} = getDataFromTable(sourceTable());
        if (rows.length === 0) {
            alert('No data to plot. Please check the table.'); return;
        }
        // Plot: Send message to parent
        window.parent.postMessage({type: 'plotSource', columns: columns, rows: rows}, '*');        
    });
    // Save source to project
    sourceSaveBtn().addEventListener('click', async () => {
        const table = getDataFromTable(sourceTable());
        const nameProject = projectName().value.trim();
        const refDate = referenceDate().value;
        const name = sourceName().value;
        const lat = sourceLatitude().value;
        const lon = sourceLongitude().value;
        if (table.rows.length === 0) { alert('No data to save. Please check the table.'); return; }
        if (refDate === ''){ alert('Please check reference date of simulation.'); return; }
        if (lat === '' || lon === '' || name === ''){ alert('Please check Name/Latitude/Longitude.'); return; }
        const refSimulation = new Date(`${refDate}T00:00:00`);
        const response = await fetch('/save_source', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({projectName: nameProject, nameSource: name,
                refDate: refSimulation,lat: lat, lon: lon, data: table.rows})
        });
        const data = await response.json();
        alert(data.message);
    });

    





    


    // Save project
    saveProjectBtn().addEventListener('click', async () => {
        // saveProject();
        console.log(referenceDate().value);
    });
}


function initializeProject(){
    // Update project name
    projectName().addEventListener('input', (e) => { renderProjects(projects(), projectList, e.target.value); });
    projectName().addEventListener('blur', () => { projects().style.display = "none"; });
    // Create new project
    projectCreator().addEventListener('click', () => {
        const name = projectName().value;
        if (!name || name.trim() === '') { alert('Please define project name.'); return; }
        window.parent.postMessage({type: 'projectPreparation', name: name}, '*')
        // Show tabs
        document.getElementById('parent-tab').style.display = "block";
    });
}


await getProjectList();
initializeProject();
setupTabs(document);
updateOption();
