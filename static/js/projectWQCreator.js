import { fillTable, getDataFromTable, removeRowFromTable } from "./tableManager.js";
import { renderProjects, sendQuery, deleteTable, copyPaste } from "./tableManager.js";
import { toUTC } from "./projectSaver.js";

const projectName = () => document.getElementById('project-name');
const projects = () => document.getElementById("project-list");
const projectCreator = () => document.getElementById('create-project-button');
const sectionTab = () => document.getElementById('parent-tab');
const sectionDescription = () => document.getElementById('desription-tab');
const hydFilename = () => document.getElementById("hyd-filename");
const nLayers = () => document.getElementById("n-layer");
const startTime = () => document.getElementById("start-time");
const stopTime = () => document.getElementById("stop-time");
const sourcesContainer = () => document.getElementById("wq-sources-container");
const sourcesTable = () => document.getElementById("wq-sources-table");
const obsPointName = () => document.getElementById('wq-obs-point');
const obsPointLatitude = () => document.getElementById('wq-obs-latitude');
const obsPointLongitude = () => document.getElementById('wq-obs-longitude');
const obsPointPicker = () => document.getElementById('wq-obs-picker');
const obsPointSave = () => document.getElementById('wq-obs-save');
const obsPointRemove = () => document.getElementById('wq-obs-remove');
const obsPointTable = () => document.getElementById('wq-obs-table');
const loadsPointName = () => document.getElementById('wq-loads-point');
const loadsPointLatitude = () => document.getElementById('wq-loads-latitude');
const loadsPointLongitude = () => document.getElementById('wq-loads-longitude');
const loadsPointPicker = () => document.getElementById('wq-loads-picker');
const loadsPointSave = () => document.getElementById('wq-loads-save');
const loadsPointRemove = () => document.getElementById('wq-loads-remove');
const loadsPointTable = () => document.getElementById('wq-loads-table');
const timeTable = () => document.getElementById('wq-time-series-table');
const inputFile = () => document.getElementById('input-csv');
const csvTable = () => document.getElementById('time-series-csv');
const removeTable = () => document.getElementById('time-series-remove');
const timePreviewContainer = () => document.getElementById('wq-textarea-container');
const timePreview = () => document.getElementById('wq-data-view');
const chemicalSelector = () => document.getElementById('wq-chemical');
const chemicalName = () => document.getElementById('wq-chemical-name');
const physicalSelector = () => document.getElementById('wq-physical');
const physicalName = () => document.getElementById('wq-physical-name');
const microbialSelector = () => document.getElementById('wq-microbial');
const microbialName = () => document.getElementById('wq-microbial-name');


let projectList=[], subKey='', folderName='', usefors=null, from_usefors=null, to_usefors=null, pointSelected=null, 
    timeStep1=0, timeStep2='', nSegments=0, attrPath_='', volPath='', exchange_x=0, exchange_y=0, exchange_z=0, 
    ptrPath='', areaPath='', flowPath='', lengthPath='', srfPath='', vdfPath='', temPath='', maxiter=null, tolerance=null,
    scheme=null, salPath='', from_initial=null, initial_value=null, initial_area=null, initialList=[], progressbar=null, progressText=null;

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

function substanceChanger(target, name){
    target.addEventListener('change', () => {
        if (target.value === '') return;
        const key = target.value;
        if (key === 'simple-oxygen') subKey = 'Simple_Oxygen';
        else if (key === 'oxygen-bod-water') subKey = 'Oxygen_BOD';
        else if (key === 'cadmium') subKey = 'Cadmium';
        else if (key === 'eutrophication') subKey = 'Eutrophication';
        else if (key === 'trace-metals') subKey = 'Trace_Metals';
        else if (key === 'conservative-tracers') subKey = 'Conservative_Tracers';
        else if (key === 'suspend-sediment') subKey = 'Suspend_Sediment';
        else if (key === 'coliform') subKey = 'Coliform';
        name.value = subKey;
    });
}

function updatePoint(target, objName, objLat, objLon, table){
    target.addEventListener('click', () => {
        const name = objName.value.trim(), lat = objLat.value.trim(), lon = objLon.value.trim();
        if (name === '' || lat === '' || lon === '' || isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
            alert('Please check name, latitude, and longitude of the observation point.'); return;}
        // Add to table
        const data_arr = [[name, lat, lon]];
        fillTable(data_arr, table, false);
        // Clear input
        objName.value = ''; objLat.value = ''; objLon.value = '';
    });
}

function updateOption(){
    // Update location
    obsPointPicker().addEventListener('click', () => {
        pointSelected = 'obsPoint'; 
        window.parent.postMessage({type: 'pickPoint', data: getDataFromTable(obsPointTable(), true)}, '*');
    });
    loadsPointPicker().addEventListener('click', () => {
        pointSelected = 'loadsPoint'; 
        window.parent.postMessage({type: 'pickPoint', data: getDataFromTable(loadsPointTable(), true)}, '*');
    });
    // Copy and paste to tables
    copyPaste(obsPointTable(), 3); copyPaste(loadsPointTable(), 3);
    copyPaste(timeTable(), 4); copyPaste(sourcesTable(), 3);
    // Update when user change Combobox
    substanceChanger(chemicalSelector(), chemicalName());
    substanceChanger(physicalSelector(), physicalName());
    substanceChanger(microbialSelector(), microbialName());
    // Delete table
    deleteTable(removeTable(), timeTable());
    // Upload CSV
    csvTable().addEventListener('click', () => { 
        inputFile().click();
        inputFile().addEventListener('change', () => {
            if (inputFile().files.length > 0) {
                const file = inputFile().files[0];
                const reader = new FileReader();
                reader.onload = (e) => {
                    const text = e.target.result;
                    // Get the first row
                    const firstLine = text.split(/\r?\n/)[0];
                    const columns = firstLine.split(/\t|,/);
                    if (columns.length !== 4) { 
                    alert(`The current table has ${columns.length} columns.\nNumber of columns must be 4.`); 
                        inputFile().value = ''; return; 
                    }
                    const rows = text.split(/\r?\n/).slice(1).filter(row => row.trim() !== ''); // Split into rows 
                    const data_arr = rows.map(row => row.split(/\t|,/).slice(0, 4)); // Split into columns
                    fillTable(data_arr, timeTable(), true);
                    inputFile().value = "";
                };
                reader.readAsText(file, 'UTF-8');
            }
        }, {once: true});
    });
    // Save point to table
    updatePoint(obsPointSave(), obsPointName(), obsPointLatitude(), obsPointLongitude(), obsPointTable());
    updatePoint(loadsPointSave(), loadsPointName(), loadsPointLatitude(), loadsPointLongitude(), loadsPointTable());
    // Remove point from table
    obsPointRemove().addEventListener('click', () => {
        const name = obsPointName().value.trim();
        removeRowFromTable(obsPointTable(), name);
        obsPointName().value = '';
    });
    loadsPointRemove().addEventListener('click', () => {
        const name = loadsPointName().value.trim();
        removeRowFromTable(loadsPointTable(), name);
        loadsPointName().value = ''; 
    });
    removeTable().addEventListener('click', () => { 
        removeTable(removeTable(), timeTable());
        timePreview().value = '';
        timePreviewContainer().style.display = 'none'; 
    });
    // Get data from main page
    window.addEventListener('message', (event) => {
        if (event.data.type === 'pointPicked') {
            const lat = Number(event.data.content.lat).toFixed(12);
            const lon = Number(event.data.content.lng).toFixed(12);
            if (pointSelected === 'obsPoint') {
                if (obsPointName().value.trim() === '') obsPointName().value = `Point_${Number(lat).toFixed(2)}_${Number(lon).toFixed(2)}`;
                obsPointLatitude().value = lat; obsPointLongitude().value = lon;
            }
            else if (pointSelected === 'loadsPoint') {
                if (loadsPointName().value.trim() === '') loadsPointName().value = `Load_${Number(lat).toFixed(2)}_${Number(lon).toFixed(2)}`;
                loadsPointLatitude().value = lat; loadsPointLongitude().value = lon;
            }
        }
    });
    // Check function to process time-series
    document.querySelectorAll('.wq-process-time-series').forEach(btn => {
        btn.addEventListener('click', async () => {
            timePreview().value = '';
            const loadsData = getDataFromTable(loadsPointTable(), true);
            if (loadsData.rows.length === 0) {
                alert("No loads data found in the table.\nPlease check the load table in tab 'Point Settings'."); 
                timePreviewContainer().style.display = 'none'; return; 
            }
            const timeData = getDataFromTable(timeTable(), false);
            if (timeData.rows.length === 0) {
                alert("No time-series data found in the table.\nPlease check the table 'Time-Series Preparation'."); 
                timePreviewContainer().style.display = 'none'; return; 
            }
            if (btn.id === 'wq-chemical') {
                subKey = chemicalSelector().value.trim();
                folderName = chemicalName().value.trim();
            } else if (btn.id === 'wq-physical') {
                subKey = physicalSelector().value.trim();
                folderName = physicalName().value.trim();
            } else if (btn.id === 'wq-microbial') {
                subKey = microbialSelector().value.trim();
                folderName = microbialName().value.trim();
            }
            if (subKey === '') { alert('Please specify type of simulation.'); return; }
            if (folderName === '') { alert('Please specify name of substance.'); return; }
            const data = await sendQuery('wq_time', { key: subKey, folderName: folderName, loadsData: loadsData.rows, timeData: timeData.rows });
            timePreview().value = ''; 
            if (data.status === "error") {
                timePreviewContainer().style.display = 'none'; alert(data.message); return;
            };
            timePreview().value = data.content; timePreviewContainer().style.display = 'flex';
            // Assign value to USEFORS
            if (btn.id === 'wq-chemical') {
                from_usefors = document.getElementById('wq-chemical-usefors-from');
                to_usefors = document.getElementById('wq-chemical-usefors-to');
                usefors = document.getElementById('wq-usefors-chemical');
                from_initial = document.getElementById('wq-chemical-initial-from');
                initial_value = document.getElementById('wq-chemical-initial');
                initial_area = document.getElementById('wq-initial-chemical');
            } else if (btn.id === 'wq-physical') {
                from_usefors = document.getElementById('wq-physical-usefors-from');
                to_usefors = document.getElementById('wq-physical-usefors-to');
                usefors = document.getElementById('wq-usefors-physical');
                from_initial = document.getElementById('wq-physical-initial-from');
                initial_value = document.getElementById('wq-physical-initial');
                initial_area = document.getElementById('wq-initial-physical');
            } else if (btn.id === 'wq-microbial') {
                from_usefors = document.getElementById('wq-microbial-usefors-from');
                to_usefors = document.getElementById('wq-microbial-usefors-to');
                usefors = document.getElementById('wq-usefors-microbial');
                from_initial = document.getElementById('wq-microbial-initial-from');
                initial_value = document.getElementById('wq-microbial-initial');
                initial_area = document.getElementById('wq-initial-microbial');
            }
            from_usefors.innerHTML = ''; to_usefors.innerHTML = '';
            usefors.value = ''; from_initial.innerHTML = ''; initialList = data.froms;
            data.froms.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                from_usefors.add(option); 
            })
            data.tos.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                to_usefors.add(option);
            });
            data.froms.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                from_initial.add(option);
            });
        });
    });
    // Update USEFORS data
    document.querySelectorAll('.wq-usefors').forEach(btn => {
        btn.addEventListener('click', () => {
            const txt = `USEFOR '${from_usefors.value}' '${to_usefors.value}'`;
            let content = usefors.value;
            content = content === '' ? txt : content + '\n' + txt;
            // Split and remove duplicates
            content = [...new Set(content.split('\n'))].join('\n');
            usefors.value = content;
        });
    });
    // Update initial data
    document.querySelectorAll('.wq-initial').forEach(btn => {
        btn.addEventListener('click', () => {
            const txt = `${from_initial.value} ${initial_value.value}`;
            let content = initial_area.value;
            content = content === '' ? txt : content + '\n' + txt;
            content = [...new Set(content.split('\n'))].join('\n');
            initial_area.value = content;
        });
    });
    // Check function to run water quality simulation
    document.querySelectorAll('.wq-simulation').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (btn.dataset.info === 'chemical') {
                progressbar = document.getElementById('progressbar-chemical');
                progressText = document.getElementById('progress-text-chemical');
                maxiter = document.getElementById('max-iterations-chemical');
                tolerance = document.getElementById('tolerance-chemical');
                scheme = document.getElementById('wq-scheme-chemical');
            } else if (btn.dataset.info === 'physical') {
                progressbar = document.getElementById('progressbar-physical');
                progressText = document.getElementById('progress-text-physical');
                maxiter = document.getElementById('max-iterations-physical');
                tolerance = document.getElementById('tolerance-physical');
                scheme = document.getElementById('wq-scheme-physical');
            } else if (btn.dataset.info === 'microbial') {
                progressbar = document.getElementById('progressbar-microbial');
                progressText = document.getElementById('progress-text-microbial');
                maxiter = document.getElementById('max-iterations-microbial');
                tolerance = document.getElementById('tolerance-microbial');
                scheme = document.getElementById('wq-scheme-microbial');
            }
            const name = projectName().value.trim();
            if (!name || name === '') { alert('Please define project.'); return; }
            const hydPath = hydFilename().value.trim();
            if (!hydPath || hydPath === '') { alert('Please define hydrological (*.hyd) file.'); return; }
            const timeTable = timePreview().value.trim();
            if (!timeTable || timeTable === '') { alert("Post-processing field is required"); return; }
            if (!folderName || folderName === '') { alert("Name of substance is required"); return; }
            const start = startTime().value.trim(), stop = stopTime().value.trim();
            if (!start || start === '' || !stop || stop === '') { alert("The fields 'Start time' and 'Stop time' are required"); return; }
            const userforValue = usefors.value.trim();
            if (userforValue === '') { alert("The field 'Assigned Substance' must has at least one value"); return; }
            const initialValue = initial_area.value.trim();
            const obsTable = getDataFromTable(obsPointTable(), true);
            const sourceTable = getDataFromTable(sourcesTable(), true);
            const loadTable = getDataFromTable(loadsPointTable(), true);
            if (loadTable.rows.length === 0) { alert('No loads data found. Please add at least one load.'); return; }
            if (maxiter.value === '' || parseInt(maxiter.value) <= 0) { alert('Please define maximum number of iterations.'); return; }
            if (tolerance.value === '' || parseFloat(tolerance.value) <= 0) { alert('Please define tolerance.'); return; }
            const ws = new WebSocket(`ws://${window.location.host}/run_wq`);
            ws.onopen = () => {
                // Send message to the server to start the simulation
                ws.send(JSON.stringify({projectName: name, key: subKey, hydName: hydPath, folderName: folderName, usefors: userforValue,
                    timeStep1: timeStep1, timeStep2: timeStep2, nSegments: nSegments, attrPath: attrPath_, volPath: volPath, exchangeY: exchange_y,
                    exchangeX: exchange_x, exchangeZ: exchange_z, ptrPath: ptrPath, areaPath: areaPath, flowPath: flowPath, lengthPath: lengthPath,
                    nLayers: nLayers().value, sources: sourceTable.rows, loadsData: loadTable.rows, srfPath: srfPath, vdfPath: vdfPath,
                    temPath: temPath, initial: initialValue, initialList: initialList, startTime: toUTC(start), stopTime: toUTC(stop),
                    obsPoints: obsTable.rows, timeTable: timeTable, maxiter: maxiter.value, tolerance: tolerance.value, scheme: scheme.value, salPath: salPath
                }));
                progressText.innerText = ''; progressbar.value = 0;
            }
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.error) { alert(data.error); return; }
                if (data.status !== undefined) progressText.innerText = data.status;
                if (data.progress !== undefined) {
                    progressText.innerText = 'Completed: ' + data.progress + '%';
                    progressbar.value = data.progress;
                }
            }
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
        sourcesContainer().style.display = data.content.sink_sources.length > 0 ? "block":"none";
        fillTable(data.content.sink_sources, sourcesTable(), true);
        // Assign values
        hydFilename().value = data.content.filename; volPath = data.content.vol_path;
        timeStep1 = data.content.time_step1; timeStep2 = data.content.time_step2;
        nSegments = data.content.n_segments; attrPath_ = data.content.attr_path;
        exchange_x = data.content.exchange_x; exchange_z = data.content.exchange_z;
        if (data.content.exchange_y) exchange_y = data.content.exchange_y;
        ptrPath = data.content.ptr_path; areaPath = data.content.area_path;
        flowPath = data.content.flow_path; lengthPath = data.content.length_path;
        if (data.content.n_layers) nLayers().value = data.content.n_layers;
        srfPath = data.content.srf_path; vdfPath = data.content.vdf_path;
        temPath = data.content.tem_path; salPath = data.content.sal_path;
        startTime().value = data.content.start_time; stopTime().value = data.content.stop_time;
    });
}

await getProjectList(); initializeProject();
setupTabs(document); updateOption();