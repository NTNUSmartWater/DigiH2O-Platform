import { fillTable, getDataFromTable, addRowToTable, removeRowFromTable,
    deleteTable, copyPaste, csvUploader, mapPicker, renderProjects, 
    pointUpdate, updateTable, plotTable, sendQuery } from "./tableManager.js";
import { saveProject, timeStepCalculator } from "./projectSaver.js";
import { getState } from "./constants.js";
import { loadList } from "./utils.js";

const sectionDescription = () => document.getElementById('desription-tab');
const sectionTab = () => document.getElementById('parent-tab');
const projects = () => document.getElementById("project-list");
const projectName = () => document.getElementById('project-name');
const projectCreator = () => document.getElementById('create-project-button');
const projectCloner = () => document.getElementById('duplicate-project-button');
const projectRemover = () => document.getElementById('remove-project-button');
const saveProjectBtn = () => document.getElementById('complete-button');
const getLocation = () => document.getElementById('location-picker');
const userTimestepDate = () => document.getElementById('user-time-step-date');
const userTimestepTime = () => document.getElementById('user-time-step-time');
const nodalTimestepDate = () => document.getElementById('nodal-update-interval-date');
const nodalTimestepTime = () => document.getElementById('nodal-update-interval-time');
const obsPointName = () => document.getElementById('observation-point');
const obsPointLatitude = () => document.getElementById('observation-point-latitude');
const obsPointLongitude = () => document.getElementById('observation-point-longitude');
const obsPointPicker = () => document.getElementById('observation-point-picker');
const obsPointAddList = () => document.getElementById('observation-point-add-list');
const obsPointAddRow = () => document.getElementById('observation-point-add-row');
const obsPointRemove = () => document.getElementById('observation-point-remove');
const obsPointUploadFile = () => document.getElementById('observation-point-file');
const obsPointUploadText = () => document.getElementById('observation-point-text');
const obsPointUpdate = () => document.getElementById('observation-point-update');
const crossSectionPicker = () => document.getElementById('observation-cross-section-picker');
const crossSectionRemove = () => document.getElementById('observation-cross-section-remove');
const boundaryPicker = () => document.getElementById('boundary-picker');
const boundaryRemove = () => document.getElementById('boundary-remove');
const boundarySelector = () => document.getElementById('option-boundary-edit');
const boundaryTypeSelector = () => document.getElementById('option-boundary-type');
const boundaryAddRow = () => document.getElementById('boundary-add-row');
const boundaryEditTable = () => document.getElementById('boundary-edit-table');
const boundaryEditUpdate = () => document.getElementById('boundary-update');
const boundaryEditRemove = () => document.getElementById('boundary-edit-remove');
const boundarySelectorView = () => document.getElementById('option-boundary-type-view');
const boundaryViewContainer = () => document.getElementById('textarea-container');
const boundaryText = () => document.getElementById('data-view');
const sourceName = () => document.getElementById('source-name');
const sourceOptionNew = () => document.getElementById('source-sink-new');
const sourceOptionExist = () => document.getElementById('source-sink-exist');
const sourceOptionList = () => document.getElementById('source-sink-list');
const sourceOptionPicker = () => document.getElementById('source-picker');
const sourceLatitude = () => document.getElementById('source-latitude');
const sourceLongitude = () => document.getElementById('source-longitude');
const sourceTable = () => document.getElementById('source-table');
const sourceSelectionList = () => document.getElementById('option-source');
const sourceUploadFile = () => document.getElementById('source-csv-file');
const sourceUploadText = () => document.getElementById('source-csv-text');
const sourceAddBtn = () => document.getElementById('add-source-btn');
const sourcePlotBtn = () => document.getElementById('plot-source-btn');
const sourceSaveBtn = () => document.getElementById('save-source-btn');
const sourceSelectorRemove = () => document.getElementById('option-source-remove');
const sourceRemoveBtn = () => document.getElementById('source-remove');
const sourceRemoveTable = () => document.getElementById('source-remove-table');
const sourceDeleteTableBtn = () => document.getElementById('delete-source-btn');
const meteoAddBtn = () => document.getElementById('add-meteo-btn');
const meteoPlotBtn = () => document.getElementById('plot-meteo-btn');
const meteoDeleteBtn = () => document.getElementById('delete-meteo-btn');
const meteoSaveBtn = () => document.getElementById('save-meteo-btn');
const meteoTable = () => document.getElementById('edit-meteo-table');
const meteoUploadFile = () => document.getElementById('meteo-picker-file');
const meteoUploadText = () => document.getElementById('meteo-picker-text');
const weatherPanel = () => document.getElementById('weather-upload-panel');
const weatherSelector = () => document.getElementById('option-weather');
const weatherUpload = () => document.getElementById('weather-update');
const weatherAddRow = () => document.getElementById('weather-add-row');
const weatherRemove = () => document.getElementById('weather-remove');
const weatherCSVUploadFile = () => document.getElementById('weather-update-file');
const weatherCSVUploadText = () => document.getElementById('weather-update-text');
const weatherTable = () => document.getElementById('weather-edit-table');
const hisIntervalDate = () => document.getElementById('his-output-interval-date');
const hisIntervalTime = () => document.getElementById('his-output-interval-time');
const mapIntervalDate = () => document.getElementById('map-output-interval-date');
const mapIntervalTime = () => document.getElementById('map-output-interval-time');
const wqIntervalDate = () => document.getElementById('water-quality-output-interval-date');
const wqIntervalTime = () => document.getElementById('water-quality-output-interval-time');
const rstIntervalDate = () => document.getElementById('restart-interval-date');
const rstIntervalTime = () => document.getElementById('restart-interval-time');
const statisticDate = () => document.getElementById('statistic-output-interval-date');
const statisticTime = () => document.getElementById('statistic-output-interval-time');
const timingDate = () => document.getElementById('timing-statistic-output-interval-date');
const timingTime = () => document.getElementById('timing-statistic-output-interval-time');
const latitude = () => document.getElementById('latitude');
const nLayers = () => document.getElementById('n-layer');
const gridPathFile = () => document.getElementById('unstructured-grid-file');
const gridPathText = () => document.getElementById('unstructured-grid-text');
const gridTool = () => document.getElementById('activate-grid');
const startDate = () => document.getElementById('start-date');
const stopDate = () => document.getElementById('stop-date');
const obsPointTable = () => document.getElementById('observation-point-table');
const crossSectionTable = () => document.getElementById('observation-cross-section-table');
const crossSectionName = () => document.getElementById('observation-cross-section');
const boundaryName = () => document.getElementById('boundary-name');
const boundaryTable = () => document.getElementById('boundary-table');
const salinity = () => document.getElementById('use-salinity');
const temperature = () => document.getElementById('option-temperature');
const initWaterLevel = () => document.getElementById('initial-water-level');
const initSalinity = () => document.getElementById('initial-salinity');
const initTemperature = () => document.getElementById('initial-temperature');
const outputHis = () => document.getElementById('write-his-file');
const hisStart = () => document.getElementById('his-output-start');
const hisStop = () => document.getElementById('his-output-end');
const outputMap = () => document.getElementById('write-map-file');
const mapStart = () => document.getElementById('map-output-start');
const mapStop = () => document.getElementById('map-output-end');
const outputWQ = () => document.getElementById('write-water-quality-file');
const wqStart = () => document.getElementById('water-quality-output-start');
const wqStop = () => document.getElementById('water-quality-output-end');
const outputRestart = () => document.getElementById('write-restart-file');
const rtsStart = () => document.getElementById('restart-output-start');
const rtsStop = () => document.getElementById('restart-output-end');

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
    const data = await loadList(getState().projectName, 'getProjects', 'input');
    if (data.status === "ok") {projectList = data.content;} else {projectList = [];}
}
function sourceChange(target){
    const check = target.checked;
    if (!check) return;
    sourceLatitude().value = ''; sourceLongitude().value = '';
    // Clear table and name
    const tbody = sourceTable().querySelector("tbody");
    tbody.innerHTML = ""; sourceName().value = ''; sourceUploadText().value = '';
}

function assignOutput(target, start, end, startDate, stopDate){
    target.addEventListener('change', () => { 
        if (!target.checked) { start.value = ''; end.value = ''; return; }
        start.value = startDate.value !== '' ? startDate.value : '';
        end.value = stopDate.value !== '' ? stopDate.value : '';
    });
}

async function fileUploader(targetFile, targetText, projectName, gridName){
    if (projectName === '') return;
    window.parent.postMessage({type: 'showOverlay', message: 'Uploading grid to project...'}, '*');
    const file = targetFile.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('projectName', projectName);
    formData.append('gridName', gridName);
    targetText.value = file?.name || "";
    const response = await fetch('/upload_data', { method: 'POST', body: formData });
    const data = await response.json();
    window.parent.postMessage({type: 'hideOverlay'}, '*');
    if (data.status === "error") {alert(data.message), targetFile.value = '', targetText.value = ''; return;}
    alert(data.message);
}

function updateOption(){
    // Update location
    mapPicker(getLocation(), 'pickLocation');
    mapPicker(obsPointPicker(), 'pickPoint', () => getDataFromTable(obsPointTable(), true), 'obsPoint');
    mapPicker(crossSectionPicker(), 'pickCrossSection', () => getDataFromTable(crossSectionTable(), true));
    mapPicker(boundaryPicker(), 'pickBoundary', () => getDataFromTable(boundaryTable(), true));
    mapPicker(sourceOptionPicker(), 'pickSource');
    // Event when user uploads CSV file
    obsPointUploadText().addEventListener('click', () => { obsPointUploadFile().click(); });
    obsPointUploadFile().addEventListener('change', async (event) => { 
        await csvUploader(event, obsPointUploadText(), obsPointTable(), 3); 
    });
    sourceUploadText().addEventListener('click', () => { sourceUploadFile().click(); });
    sourceUploadFile().addEventListener('change', async (event) => { 
        await csvUploader(event, sourceUploadText(), sourceTable(), 5, false, sourceName(), sourceLatitude(), sourceLongitude()); 
    });
    meteoUploadText().addEventListener('click', () => { meteoUploadFile().click(); });
    meteoUploadFile().addEventListener('change', async (event) => {
        await csvUploader(event, meteoUploadText(), meteoTable(), 5);
    })
    weatherCSVUploadText().addEventListener('click', () => { weatherCSVUploadFile().click(); });
    weatherCSVUploadFile().addEventListener('change', async (event) => {
        await csvUploader(event, weatherCSVUploadText(), weatherTable(), 3);
    })
    // Upload file to server
    gridPathText().addEventListener('click', () => { gridPathFile().click(); });
    gridPathFile().addEventListener('change', async() => {
        await fileUploader(gridPathFile(), gridPathText(), projectName().value, 'FlowFM_net.nc')
        window.parent.postMessage({type: 'showGrid', projectName: projectName().value, 
            gridName: 'FlowFM_net.nc', message: 'Uploading grid to project...'}, '*');
    });
    gridTool().addEventListener('click', () => { window.parent.postMessage({type: 'showGridTool'}, '*'); });
    // Copy and paste to tables
    copyPaste(boundaryEditTable(), 2); copyPaste(sourceTable(), 5); 
    copyPaste(meteoTable(), 5); copyPaste(weatherTable(), 3); copyPaste(obsPointTable(), 3);
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
            if (obsPointName().value.trim() === '') {
                obsPointName().value = `Point_${Number(lat).toFixed(2)}_${Number(lon).toFixed(2)}`;
            }
        }
        if (event.data.type === 'crossSectionPicked') {
            const content = event.data.content;
            let value = crossSectionName().value.trim();
            if (value === '') { value = `Cross-Section`; crossSectionName().value = value; }
            const data_arr = content.map((row, idx) => [`${value}_${idx + 1}`, Number(row.lat).toFixed(12), Number(row.lng).toFixed(12)]);
            fillTable(data_arr, crossSectionTable(), true);
        }
        if (event.data.type === 'boundaryPicked') {
            const content = event.data.content;
            let value = boundaryName().value.trim();
            if (value === '') { value = `Boundary`; boundaryName().value = value; }
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
            if (value === '') { value = `Source_Sink`; sourceName().value = value; }
            sourceLatitude().value = Number(content.lat).toFixed(16);
            sourceLongitude().value = Number(content.lng).toFixed(16);
        }
    });
    // Add point to table
    obsPointAddList().addEventListener('click', () => {
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
    // Add a new row to the table
    obsPointAddRow().addEventListener('click', () => addRowToTable(obsPointTable(), ['Name', 'Latitude', 'Longitude']));
    boundaryAddRow().addEventListener('click', () => addRowToTable(boundaryEditTable(), ['YYYY-MM-DD HH:MM:SS', 'Value']));
    sourceAddBtn().addEventListener('click', () => addRowToTable(sourceTable(), ['YYYY-MM-DD HH:MM:SS', 'Discharge', 'Salinity', 'Temperature', 'Contaminant']));
    meteoAddBtn().addEventListener('click', () => addRowToTable(meteoTable(), ['YYYY-MM-DD HH:MM:SS', 'Humidity', 'Air temperature', 'Cloud coverage', 'Solar radiation']));
    weatherAddRow().addEventListener('click', () => addRowToTable(weatherTable(), ['YYYY-MM-DD HH:MM:SS', 'Magnitude', 'Direction']));
    // Remove point from table
    obsPointRemove().addEventListener('click', () => {
        const name = obsPointName().value.trim();
        removeRowFromTable(obsPointTable(), name); obsPointName().value = '';
    });
    // Event when user change radio button for observation points
    pointUpdate(document.getElementById('observation-point-new'), obsPointTable(),
        false, ["Name", "Latitude", "Longitude"]);
    pointUpdate(document.getElementById('observation-point-exist'), 
        obsPointTable(), true, [obsPointName(), obsPointLatitude(), obsPointLongitude()]);
    // Update observation point on map
    obsPointUpdate().addEventListener('click', () => {
        const content = getDataFromTable(obsPointTable(), true);
        if (content.rows.length === 0) {alert('No observation points found.'); return;}
        window.parent.postMessage({type: 'updateObsPoint', data: content}, '*');
    });
    // Event when user delete
    crossSectionRemove().addEventListener('click', () => deleteTable(crossSectionTable(), crossSectionName(), 'clearCrossSection'));
    boundaryEditRemove().addEventListener('click', () => { deleteTable(boundaryEditTable()); boundaryAddRow().click(); });
    sourceDeleteTableBtn().addEventListener('click', () => { deleteTable(sourceTable()); sourceAddBtn().click(); });
    meteoDeleteBtn().addEventListener('click', () => { deleteTable(meteoTable()); meteoAddBtn().click(); });
    weatherRemove().addEventListener('click', () => { deleteTable(weatherTable()); weatherAddRow().click(); });
    // Event when user plot table
    plotTable(sourcePlotBtn(), sourceTable()); plotTable(meteoPlotBtn(), meteoTable());
    // Update boundary option
    boundaryEditUpdate().addEventListener('click', async () => {
        const nameProject = projectName().value.trim(), nameBoundary = boundaryName().value.trim();
        const subBoundary = boundarySelector().value, boundaryType = boundaryTypeSelector().value;
        if (nameProject === '' || nameBoundary === '' || subBoundary === '' || boundaryType === '') {
            alert('Please check: \n     1. Name of project/boundary/sub-boundary option is required.' + 
                '\n     2. Boundary type is required.' + '\n     3. Reference date is required.'); return;
        }
        const boundaryData = getDataFromTable(boundaryTable(), true);
        if (boundaryData.rows.length === 0) { alert('No data in the table. Please check boundary condition.'); return; }
        const subBoundaryData = getDataFromTable(boundaryEditTable());
        if (subBoundaryData.rows.length === 0) { alert('No data in the table. Please check sub-boundary condition.'); return; }
        // Create boundary
        const content = {projectName: nameProject, boundaryName: nameBoundary, boundaryData: boundaryData.rows,
            subBoundaryName: subBoundary, boundaryType: boundaryType, subBoundaryData: subBoundaryData.rows}
        const data = await sendQuery('update_boundary', content);
        alert(data.message); boundarySelectorView().value = '';
        boundaryViewContainer().style.display = 'none'; boundaryText().value = '';
    });
    // Update parameters of boundary from file
    boundarySelector().addEventListener('change', async () => {
        const boundaryName = boundarySelector().value, boundaryType = boundaryTypeSelector().value;
        const content = {projectName: projectName().value.trim(), boundaryName: boundaryName, boundaryType: boundaryType};
        const data = await sendQuery('get_boundary_params', content);
        if (data.status === 'new') { boundaryEditRemove().click(); return; }
        if (data.status === 'error') { alert(data.message); return; }
        boundaryEditRemove().click(); fillTable(data.content, boundaryEditTable());
    });
    boundaryTypeSelector().addEventListener('change', async () => {
        const boundaryName = boundarySelector().value, boundaryType = boundaryTypeSelector().value;
        const content = {projectName: projectName().value.trim(), boundaryName: boundaryName, boundaryType: boundaryType};
        const data = await sendQuery('get_boundary_params', content);
        if (data.status === 'new') { boundaryEditRemove().click(); return; }
        if (data.status === 'error') { alert(data.message); return; }
        boundaryEditRemove().click(); fillTable(data.content, boundaryEditTable());
    })
    // View boundary condition
    boundarySelectorView().addEventListener('change', async () => {
        if (boundarySelectorView().value === '') { boundaryViewContainer().style.display = 'none'; return; }
        if (projectName().value === '') {
            alert('Name of project is required.'); 
            boundaryViewContainer().style.display = 'none'; return;
        }
        const value = boundarySelectorView().value;
        boundaryText().value = '';
        // Create boundary
        const data = await sendQuery('view_boundary', {projectName: projectName().value, boundaryType: value});
        if (data.status === "error") {
            boundarySelectorView().value = ''; alert(data.message);
            boundaryViewContainer().style.display = 'none'; return;
        };
        boundaryText().value = data.content; boundaryViewContainer().style.display = 'flex';
    });
    // Reset sub-boundary condition
    boundaryRemove().addEventListener('click', async () => {
        const nameBoundary = boundaryName().value.trim();
        if (nameBoundary === '') { alert('Name of boundary is required.'); return; }
        // Delete boundary
        const data = await sendQuery('delete_boundary', {projectName: projectName().value, boundaryName: nameBoundary});
        alert(data.message); deleteTable(boundaryTable(), undefined, 'clearBoundary');
        const tbody = boundaryEditTable().querySelector("tbody"); tbody.innerHTML = "";
        boundarySelectorView().value = ''; boundarySelector().value = ''; boundarySelector().innerHTML = '';
        boundaryViewContainer().style.display = 'none'; boundaryText().value = ''; boundaryName().value = '';
    });
    // Working on source/sink option
    sourceOptionNew().addEventListener('change', () => {
        sourceChange(sourceOptionNew()); deleteTable(sourceTable()); sourceAddBtn().click();
        sourceOptionPicker().style.display = 'block';
    });
    sourceOptionExist().addEventListener('change', () => {
        sourceChange(sourceOptionExist()); deleteTable(sourceTable()); sourceAddBtn().click();
        sourceOptionPicker().style.display = 'none';
    });
    sourceOptionList().addEventListener('change', async () => {
        sourceChange(sourceOptionList()); deleteTable(sourceTable()); sourceAddBtn().click();
        sourceOptionPicker().style.display = 'none';
        const data = await sendQuery('get_files', {});
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
        const value = sourceSelectionList().value;
        if (value === '') return;
        window.parent.postMessage({type: 'showOverlay', 
            message: 'Reading source/sink and exacting data to table...'}, '*'); // Show overlay
        const data = await sendQuery('get_source', {filename: value});
        if (data.status === "error") alert(data.message);
        sourceLatitude().value = data.content.lat;
        sourceLongitude().value = data.content.lon;
        sourceName().value = value;
        // Convert to 2D array
        const lines = data.content.data;
        const data_arr = lines.map(line => line.trim().split(","));
        fillTable(data_arr, sourceTable());
        window.parent.postMessage({type: 'hideOverlay'}, '*');  // Hide overlay
    });
    // Remove source from project
    sourceRemoveBtn().addEventListener('click', async () => {
        const nameProject = projectName().value.trim();
        if (nameProject === ''){ alert('Please check project name.'); return; }
        const name = sourceSelectorRemove().value;
        removeRowFromTable(sourceRemoveTable(), name); deleteTable(sourceTable());
        const content = getDataFromTable(sourceRemoveTable(), true).rows;
        updateTable(sourceRemoveTable(), sourceSelectorRemove(), nameProject, content);
    });
    // Change output options
    assignOutput(outputHis(), hisStart(), hisStop(), startDate(), stopDate());
    assignOutput(outputMap(), mapStart(), mapStop(), startDate(), stopDate());
    assignOutput(outputWQ(), wqStart(), wqStop(), startDate(), stopDate());
    assignOutput(outputRestart(), rtsStart(), rtsStop(), startDate(), stopDate());
    // Save source to project
    sourceSaveBtn().addEventListener('click', async () => {
        const nameProject = projectName().value.trim();
        if (nameProject === ''){ alert('Please check project name.'); return; }
        const table = getDataFromTable(sourceTable());
        const name = sourceName().value;
        const lat = sourceLatitude().value;
        const lon = sourceLongitude().value;
        if (table.rows.length === 0) { alert('No data to save. Please check the table.'); return; }
        if (lat === '' || lon === '' || name === ''){ alert('Please check Name/Latitude/Longitude.'); return; }
        const content = {projectName: nameProject, nameSource: name, lat: lat, lon: lon, data: table.rows}
        const data = await sendQuery('save_source', content);
        updateTable(sourceRemoveTable(), sourceSelectorRemove(), nameProject);
        alert(data.message);
    });
    // Save meteo data to project
    meteoSaveBtn().addEventListener('click', async () => {
        const nameProject = projectName().value.trim();
        if (nameProject === ''){ alert('Please check project name.'); return; }        
        const table = getDataFromTable(meteoTable());
        if (table.rows.length === 0) { alert('No data to save. Please check the table.'); return; }
        const data = await sendQuery('save_meteo', {projectName: nameProject, data: table.rows});
        alert(data.message);
    });
    // Weather data
    weatherSelector().addEventListener('change', () => {
        if (weatherSelector().value === '') {
            weatherPanel().style.display = 'none'; weatherTable().style.display = 'none';
            weatherRemove().style.display = 'none'; weatherUpload().style.display = 'none'; return;
        }
        weatherPanel().style.display = 'block'; weatherTable().style.display = 'block'; 
        weatherRemove().style.display = 'block'; weatherUpload().style.display = 'block'; 
        deleteTable(weatherTable());
        // Add row after above function finished
        requestAnimationFrame(() => { weatherAddRow().click(); });
    });
    weatherUpload().addEventListener('click', async () => {
        const nameProject = projectName().value.trim();
        if (nameProject === ''){ alert('Please check project name.'); return; }        
        const table = getDataFromTable(weatherTable());
        if (table.rows.length === 0) { alert('No data to save. Please check the table.'); return; }
        const data = await sendQuery('save_weather', {projectName: nameProject, data: table.rows});
        alert(data.message);
    })
    // Save project
    saveProjectBtn().addEventListener('click', async () => { 
        const userTimeSec = timeStepCalculator(userTimestepDate().value, userTimestepTime().value);
        const nodalTimeSec = timeStepCalculator(nodalTimestepDate().value, nodalTimestepTime().value);
        const hisInterval = timeStepCalculator(hisIntervalDate().value, hisIntervalTime().value);
        const mapInterval = timeStepCalculator(mapIntervalDate().value, mapIntervalTime().value);
        const wqInterval = timeStepCalculator(wqIntervalDate().value, wqIntervalTime().value);
        const rtsInterval = timeStepCalculator(rstIntervalDate().value, rstIntervalTime().value);
        const sttInterval = timeStepCalculator(statisticDate().value, statisticTime().value);
        const timingInterval = timeStepCalculator(timingDate().value, timingTime().value);
        const elements = { projectName, latitude, nLayers, gridPathText, startDate, stopDate,
            userTimeSec, nodalTimeSec, obsPointTable, crossSectionName, crossSectionTable, salinity, 
            temperature, initWaterLevel, initSalinity, initTemperature , outputHis, hisInterval, hisStart, 
            hisStop, outputMap, mapInterval, mapStart, mapStop, outputWQ, wqInterval, wqStart, wqStop, 
            outputRestart, rtsInterval, rtsStart, rtsStop, sttInterval, timingInterval };
        await saveProject(elements); 
    });
}

async function loadScenario(scenarioName){
    // Get average latitude
    const data = await sendQuery('get_scenario', {projectName: scenarioName});
    if (data.status === 'new') { return; }
    if (data.status === 'error') { alert(data.message); return; }
    latitude().value = data.content.avgLat;
    gridPathText().value = data.content.gridPath;
    nLayers().value = data.content.nLayers;
    startDate().value = data.content.startDate;
    stopDate().value = data.content.stopDate;
    userTimestepDate().value = data.content.userTimestepDate;
    userTimestepTime().value = data.content.userTimestepTime;
    nodalTimestepDate().value = data.content.nodalTimestepDate;
    nodalTimestepTime().value = data.content.nodalTimestepTime;
    fillTable(data.content.obsPointTable, obsPointTable());
    fillTable(data.content.crossSectionTable, crossSectionTable());
    fillTable(data.content.boundaryTable, boundaryTable());
    // Update boundary option
    const options = data.content.boundaryTable.map(row => `<option value="${row[0]}">${row[0]}</option>`).join(' ');
    const defaultOption = `<option value="" selected>--- No selected ---</option>`;
    boundarySelector().innerHTML = defaultOption + options;
    initWaterLevel().value = data.content.initWaterLevel;
    initSalinity().value = data.content.initSalinity;
    initTemperature().value = data.content.initTemperature;
    // Get source data if exist
    updateTable(sourceRemoveTable(), sourceSelectorRemove(), scenarioName);
    if (data.content.meteoPath !== '') { 
        meteoUploadText().value = 'FlowFM_meteo.tim';
        fillTable(data.content.meteoPath, meteoTable());
    }
    if (data.content.weatherPath !== '') { 
        weatherSelector().value = data.content.weatherType;
        fillTable(data.content.weatherPath, weatherTable());
    }
    hisIntervalDate().value = data.content.hisIntervalDate;
    hisIntervalTime().value = data.content.hisIntervalTime;
    hisStart().value = data.content.hisStart; hisStop().value = data.content.hisStop;
    if (hisStart().value !== '' || hisStop().value !== '') { outputHis().checked = true; }
    mapIntervalDate().value = data.content.mapIntervalDate;
    mapIntervalTime().value = data.content.mapIntervalTime;
    mapStart().value = data.content.mapStart; mapStop().value = data.content.mapStop;
    if (mapStart().value !== '' || mapStop().value !== '') { outputMap().checked = true; }
    wqIntervalDate().value = data.content.wqIntervalDate;
    wqIntervalTime().value = data.content.wqIntervalTime;
    wqStart().value = data.content.wqStart; wqStop().value = data.content.wqStop;
    if (wqStart().value !== '' || wqStop().value !== '') { outputWQ().checked = true; }
    statisticDate().value = data.content.statisticDate; statisticTime().value = data.content.statisticTime;
    timingDate().value = data.content.timingDate; timingTime().value = data.content.timingTime;
}

async function initializeProject(){
    // Update project name
    projectName().addEventListener('click', async () => {
        await getProjectList();
        if (projectList.length === 0) return;
        projects().innerHTML = '';
        projectList.forEach(p => {
            const li = document.createElement("li");
            li.textContent = p;
            li.addEventListener('mousedown', () => {
                projectName().value = p; projects().style.display = "none";
            });
            projects().appendChild(li);
        })
        projects().style.display = "block";
    });
    projectName().addEventListener('input', (e) => { 
        const value = e.target.value.trim();
        if (value === '') {
            sectionTab().style.display = "none"; 
            sectionDescription().style.display = "block";
        }
        renderProjects(projects(), projectList, value);
    });
    projectName().addEventListener('blur', () => { 
        setTimeout(() => { projects().style.display = "none"; }, 100);
     });
    // Create new project
    projectCreator().addEventListener('click', async () => {
        const name = projectName().value.trim(); let project = '';
        if (!name || name.trim() === '') { alert('Please define scenario name.'); return; }
        if (name.includes('/')) { project = name.split('/').pop(); } else { project = name; }
        window.parent.postMessage({type: 'projectPreparation', name: project}, '*')
        // Show tabs
        sectionTab().style.display = "block"; sectionDescription().style.display = "none";
        // If project name already exist, load parameters
        await loadScenario(name);
    });
    // Copy project
    projectCloner().addEventListener('click', async () => {
        const name = projectName().value.trim();
        if (!name || name.trim() === '') { alert('Please select scenario from the dropdown list first.'); return; }
        // Ask for a new name
        const newName = prompt('Please enter a name for the new scenario:\nCloning a scenario will take some time. Please be patient.');
        if (!newName || newName.trim() === '') { alert('Please define scenario name.'); return; }
        projectCloner().innerHTML = 'Cloning...';
        const data = await sendQuery('copy_project', {oldName: name, newName: newName});
        alert(data.message); projectList = []; projectName().value = ''; await getProjectList(); projectCloner().innerHTML = 'Clone Scenario';
    })
    // Delete project
    projectRemover().addEventListener('click', async () => {
        // Ask for confirmation
        if (!confirm('Are you sure you want to delete this scenario?')) { return; }
        const name = projectName().value.trim();
        if (!name || name.trim() === '') { alert('Please define scenario.'); return; }
        projectRemover().innerHTML = 'Deleting...';
        const data = await sendQuery('delete_project', {projectName: name});
        alert(data.message); projectList = []; projectName().value = ''; await getProjectList(); projectRemover().innerHTML = 'Delete Scenario';
    });
}

await getProjectList(); await initializeProject();
setupTabs(document); updateOption();