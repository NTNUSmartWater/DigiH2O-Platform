import { fillTable, getDataFromTable, removeRowFromTable, addRowToTable,
    renderProjects, sendQuery, deleteTable, copyPaste } from "./tableManager.js";
import { toUTC } from "./projectSaver.js";

const projectName = () => document.getElementById('project-name');
const projects = () => document.getElementById("project-list");
const waqSelector = () => document.getElementById("waq-name");
const waqLabel = () => document.getElementById("label-waq");
const projectCreator = () => document.getElementById('create-project-button');
const projectCloner = () => document.getElementById('duplicate-project-button');
const projectDeleter = () => document.getElementById('delete-project-button');
const sectionTab = () => document.getElementById('parent-tab');
const sectionDescription = () => document.getElementById('desription-tab');
const hydFilename = () => document.getElementById("hyd-filename");
const nLayers = () => document.getElementById("n-layer");
const startTime = () => document.getElementById("start-time");
const stopTime = () => document.getElementById("stop-time");
const sourcesContainer = () => document.getElementById("wq-sources-container");
const sourcesTable = () => document.getElementById("wq-sources-table");
const obsPointName = () => document.getElementById('wq-obs-point');
const obsPointPicker = () => document.getElementById('wq-obs-picker');
const obsPointRemove = () => document.getElementById('wq-obs-remove');
const obsPointTable = () => document.getElementById('wq-obs-table');
const loadsPointName = () => document.getElementById('wq-loads-point');
const loadsPointPicker = () => document.getElementById('wq-loads-picker');
const loadsPointRemove = () => document.getElementById('wq-loads-remove');
const loadsPointTable = () => document.getElementById('wq-loads-table');
const timeTable = () => document.getElementById('wq-time-series-table');
const timeTableAddRow = () => document.getElementById('time-series-add-row');
const inputFile = () => document.getElementById('input-csv');
const csvTable = () => document.getElementById('time-series-csv');
const removeTable = () => document.getElementById('time-series-remove');
const timePreviewContainer = () => document.getElementById('wq-textarea-container');
const timePreview = () => document.getElementById('wq-data-view');
const physicalSelector = () => document.getElementById('wq-physical');
const physicalName = () => document.getElementById('wq-physical-name');
const useforsFromPhysical = () => document.getElementById('wq-physical-usefors-from');
const useforsToPhysical = () => document.getElementById('wq-physical-usefors-to');
const useforsPhysical = () => document.getElementById('wq-usefors-physical');
const initialFromPhysical = () => document.getElementById('wq-physical-initial-from');
const initialToPhysical = () => document.getElementById('wq-physical-initial');
const initialAreaPhysical = () => document.getElementById('wq-initial-physical');
const schemePhysical = () => document.getElementById('wq-scheme-physical');
const maxInterPhysical = () => document.getElementById('max-iterations-physical');
const tolerancePhysical = () => document.getElementById('tolerance-physical');
const chemicalSelector = () => document.getElementById('wq-chemical');
const chemicalName = () => document.getElementById('wq-chemical-name');
const useforsFromChemical = () => document.getElementById('wq-chemical-usefors-from');
const useforsToChemical = () => document.getElementById('wq-chemical-usefors-to');
const useforsChemical = () => document.getElementById('wq-usefors-chemical');
const initialFromChemical = () => document.getElementById('wq-chemical-initial-from');
const initialToChemical = () => document.getElementById('wq-chemical-initial');
const initialAreaChemical = () => document.getElementById('wq-initial-chemical');
const schemeChemical = () => document.getElementById('wq-scheme-chemical');
const maxInterChemical = () => document.getElementById('max-iterations-chemical');
const toleranceChemical = () => document.getElementById('tolerance-chemical');
const microbialSelector = () => document.getElementById('wq-microbial');
const microbialName = () => document.getElementById('wq-microbial-name');
const useforsFromMirobial = () =>document.getElementById('wq-microbial-usefors-from');
const useforsToMirobial = () => document.getElementById('wq-microbial-usefors-to');
const useforsMicrobial = () => document.getElementById('wq-usefors-microbial');
const initialFromMirobial = () => document.getElementById('wq-microbial-initial-from');
const initialToMirobial = () => document.getElementById('wq-microbial-initial');
const initialAreaMirobial = () => document.getElementById('wq-initial-microbial');
const schemeMirobial = () => document.getElementById('wq-scheme-microbial');
const maxInterMirobial = () => document.getElementById('max-iterations-microbial');
const toleranceMirobial = () => document.getElementById('tolerance-microbial');

let projectList=[], subKey='', folderName='', usefors=null, from_usefors=null, to_usefors=null, pointSelected=null, nPoints=0,
    timeStep1=0, timeStep2=0, nSegments=0, n_layers='', attrPath_='', volPath='', exchange_x=0, exchange_y=0, exchange_z=0, nLoads=0,
    ptrPath='', areaPath='', flowPath='', lengthPath='', srfPath='', vdfPath='', temPath='', maxiter=null, tolerance=null,
    scheme=null, salPath='', from_initial=null, initial_value=null, initial_area=null, useforsFrom=[], useforsTo=[], waqContent=[];

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
      radioPanels.forEach(p => { p.style.display = (p.getAttribute('data-panel')!==name)?'none':'block'; })
    }
    function checkboxSelector(target){
        const name = target.getAttribute('data-tab');
        const checkObj = target.querySelector('input');
        const panel = root.querySelectorAll(`[data-panel="${name}"]`);
        if(panel.length === 0) return;
        panel.forEach(p => { p.style.display = checkObj.checked ? 'flex' : 'none'; })
    }
    // Show Simulator panel
    if(buttonPanels.length > 0) activate(buttonPanels[0]);
    // Click to change tab
    buttonPanels.forEach(btn => { btn.addEventListener('click', () => { activate(btn); }); });
    // Change Radio button
    radioBtns.forEach(btn => { btn.addEventListener('click', () => { radioSelector(btn); }); });
    // Change checkbox button
    checkboxBtns.forEach(box => { box.addEventListener('change', () => { checkboxSelector(box); }); });
}

async function getProjectList(){
    const data = await sendQuery('select_project', {filename: '', key: 'getProjects', folder_check: ''});
    if (data.status === "ok") projectList = data.content;
}

function substanceChanger(waqModel, target, name, type){
    target.addEventListener('change', async () => {
        if (type === 'wq-chemical') {
            from_usefors = useforsFromChemical(); to_usefors = useforsToChemical();
            usefors = useforsChemical(); from_initial = initialFromChemical();
            initial_area = initialAreaChemical(); scheme = schemeChemical();
            maxiter = maxInterChemical(); tolerance = toleranceChemical();
            initial_value = initialToChemical();
        } else if (type === 'wq-physical') {
            from_usefors = useforsFromPhysical(); to_usefors = useforsToPhysical();
            usefors = useforsPhysical(); from_initial = initialFromPhysical();
            initial_area = initialAreaPhysical(); scheme = schemePhysical();
            maxiter = maxInterPhysical(); tolerance = tolerancePhysical();
            initial_value = initialToPhysical();
        } else if (type === 'wq-microbial') {
            from_usefors = useforsFromMirobial(); to_usefors = useforsToMirobial();
            usefors = useforsMicrobial(); from_initial = initialFromMirobial();
            initial_area = initialAreaMirobial(); scheme = schemeMirobial();
            maxiter = maxInterMirobial(); tolerance = toleranceMirobial();
            initial_value = initialToMirobial();
        }
        from_usefors.innerHTML = ''; from_initial.innerHTML = ''; 
        initial_area.value = ''; initial_value.value = '0';
        scheme.value = '15'; maxiter.value = '500'; tolerance.value = '1E-07';
        const key = target.value;        
        if (key === 'simple-oxygen') {subKey = 'Simple_Oxygen';}
        else if (key === 'oxygen-bod-water') { subKey = 'Oxygen_BOD'; }
        else if (key === 'cadmium') { subKey = 'Cadmium'; }
        else if (key === 'eutrophication') { subKey = 'Eutrophication'; }
        else if (key === 'trace-metals') { subKey = 'Trace_Metals'; }
        else if (key === 'conservative-tracers') { subKey = 'Conservative_Tracers'; }
        else if (key === 'suspend-sediment') { subKey = 'Suspend_Sediment'; }
        else if (key === 'coliform') { subKey = 'Coliform'; }
        else { 
            timePreviewContainer().style.display = 'none'; timePreview().value = '';
            name.value = ''; to_usefors.innerHTML = ''; usefors.value = ''; return;
        }
        if (waqModel.value !== '') { subKey = waqModel.value; }
        const data = await sendQuery('wq_time_from_waq', { key: subKey });
        if (data.status === "error") {
            timePreviewContainer().style.display = 'none'; 
            timePreview().value = ''; alert(data.message); return;
        };
        name.value = subKey; useforsFrom = data.froms;
        [from_usefors, from_initial].forEach(select => { 
            data.froms.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                select.add(option);
            }); 
        });
    });
}

function updateOption(){
    // Update location
    obsPointPicker().addEventListener('click', () => {
        pointSelected = 'obsPoint';
        const obsPoints = getDataFromTable(obsPointTable(), true);
        const loadsPoints = getDataFromTable(loadsPointTable(), true);
        window.parent.postMessage({type: 'pickPoint', data: [loadsPoints, obsPoints], pointType: 'waqPoint'}, '*');
    });
    loadsPointPicker().addEventListener('click', () => {
        pointSelected = 'loadsPoint'; 
        const obsPoints = getDataFromTable(obsPointTable(), true);
        const loadsPoints = getDataFromTable(loadsPointTable(), true);
        window.parent.postMessage({type: 'pickPoint', data: [obsPoints, loadsPoints], pointType: 'loadsPoint'}, '*');
    });
    // Copy and paste to tables
    copyPaste(obsPointTable(), 3); copyPaste(loadsPointTable(), 3);
    copyPaste(timeTable(), 4); copyPaste(sourcesTable(), 3);
    // Update when user change Combobox
    substanceChanger(waqSelector(), chemicalSelector(), chemicalName(), 'wq-chemical');
    substanceChanger(waqSelector(), physicalSelector(), physicalName(), 'wq-physical');
    substanceChanger(waqSelector(), microbialSelector(), microbialName(), 'wq-microbial');
    // Add new row to table
    timeTableAddRow().addEventListener('click', () => {
        deleteTable(timeTable()); addRowToTable(timeTable(), ['YYYY-MM-DD HH:MM:SS', 'PointName', 'Substance', 'Value']);
    });
    // Delete table
    removeTable().addEventListener('click', () => { 
        deleteTable(timeTable()); timePreview().value = ''; timePreviewContainer().style.display = 'none';
        addRowToTable(timeTable(), ['YYYY-MM-DD HH:MM:SS', 'PointName', 'Substance', 'Value']);
    });
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
    // Remove point from table
    obsPointRemove().addEventListener('click', () => {
        const name = obsPointName().value.trim();
        if (name === '') { alert('Please enter name of observation point from list to remove.'); return; }
        removeRowFromTable(obsPointTable(), name); obsPointName().value = '';
    });
    loadsPointRemove().addEventListener('click', () => {
        const name = loadsPointName().value.trim();
        if (name === '') { alert('Please enter name of loads point from list to remove.'); return; }
        removeRowFromTable(loadsPointTable(), name);
        loadsPointName().value = ''; 
    });
    // Get data from main page
    window.addEventListener('message', (event) => {
        if (event.data.type === 'pointPicked') {
            const lat = Number(event.data.content.lat).toFixed(12);
            const lon = Number(event.data.content.lng).toFixed(12);
            if (pointSelected === 'obsPoint') {
                let name = ''; nPoints++;
                // Define name of point
                if (obsPointName().value.trim() !== '') name = obsPointName().value.trim();
                else name = `Obs_${nPoints}`;
                const data_arr = [[name, lat, lon]];
                fillTable(data_arr, obsPointTable(), false);
            }
            else if (pointSelected === 'loadsPoint') {
                let name = ''; nLoads++;
                if (loadsPointName().value.trim() !== '') name = loadsPointName().value.trim();
                else name = `Load_${nLoads}`; 
                const data_arr = [[name, lat, lon]];
                fillTable(data_arr, loadsPointTable(), false);
            }
        }
    });
    // Check function to process time-series
    document.querySelectorAll('.wq-process-time-series').forEach(btn => {
        btn.addEventListener('click', async () => {
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
                subKey = chemicalSelector().value; folderName = chemicalName().value.trim();
                initial_area = initialAreaChemical(); usefors = useforsChemical();
                to_usefors = useforsToChemical(); initial_value = initialToChemical();
            } else if (btn.id === 'wq-physical') {
                subKey = physicalSelector().value; folderName = physicalName().value.trim();
                initial_area = initialAreaPhysical(); usefors = useforsPhysical();
                to_usefors = useforsToPhysical(); initial_value = initialToPhysical();
            } else if (btn.id === 'wq-microbial') {
                subKey = microbialSelector().value; folderName = microbialName().value.trim();
                initial_area = initialAreaMirobial(); usefors = useforsMicrobial();
                to_usefors = useforsToMirobial(); initial_value = initialToMirobial();
            }
            timePreview().value = ''; initial_area.value = ''; usefors.value = ''; initial_value.value = '0';
            if (subKey === '') { alert('Please specify type of simulation.'); return; }
            if (folderName === '') { alert('Please specify name of substance.'); return; }
            const data = await sendQuery('wq_time_to_waq', { folderName: folderName, 
                loadsData: loadsData.rows, timeData: timeData.rows });
            if (data.status === "error") {
                timePreviewContainer().style.display = 'none'; 
                timePreview().value = ''; alert(data.message); return;
            };
            timePreview().value = data.content; useforsTo = data.tos;
            timePreviewContainer().style.display = 'flex'; to_usefors.innerHTML = '';
            data.tos.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                to_usefors.add(option);
            });
        });
    });
    // Update USEFORS data
    document.querySelectorAll('.wq-usefors').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.info === 'physical') {
                from_usefors = useforsFromPhysical(); to_usefors = useforsToPhysical();
                usefors = useforsPhysical();
            } else if (btn.dataset.info === 'chemical') {
                from_usefors = useforsFromChemical(); to_usefors = useforsToChemical();
                usefors = useforsChemical();
            } else if (btn.dataset.info === 'microbial') {
                from_usefors = useforsFromMirobial(); to_usefors = useforsToMirobial();
                usefors = useforsMicrobial();
            }
            const txt = `USEFOR '${from_usefors.value}' '${to_usefors.value}'`;
            let content = usefors.value;
            content = content === '' ? txt : content + '\n' + txt;
            // Split and remove duplicates
            usefors.value = [...new Set(content.split('\n'))].join('\n');
        });
    });
    // Update initial data
    document.querySelectorAll('.wq-initial').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.info === 'physical') {
                from_initial = initialFromPhysical(); initial_value = initialToPhysical();
                initial_area = initialAreaPhysical();
            } else if (btn.dataset.info === 'chemical') {
                from_initial = initialFromChemical(); initial_value = initialToChemical();
                initial_area = initialAreaChemical();
            } else if (btn.dataset.info === 'microbial') {
                from_initial = initialFromMirobial(); initial_value = initialToMirobial();
                initial_area = initialAreaMirobial();
            }
            const txt = `${from_initial.value} ${initial_value.value}`;
            let content = initial_area.value;
            content = content === '' ? txt : content + '\n' + txt;
            content = [...new Set(content.split('\n'))].join('\n');
            initial_area.value = content;
        });
    });
    // Save and run water quality simulation
    document.querySelectorAll('.wq-simulation').forEach(btn => {
        btn.addEventListener('click', async () => {
            const name = projectName().value.trim();
            if (!name || name === '') { alert('Please define project.'); return; }
            const hydPath = hydFilename().value.trim();
            if (!hydPath || hydPath === '') { alert('Please define hydrological (*.hyd) file.'); return; }
            const start = startTime().value, stop = stopTime().value;
            if (!start || start === '' || !stop || stop === '') { alert("The fields 'Start time' and 'Stop time' are required"); return; }
            const data = await sendQuery('select_hyd', {projectName: name});
            if (data.status === "error") { alert(data.message); return; }
            timeStep1 = data.content.time_step1; timeStep2 = data.content.time_step2;
            attrPath_ = data.content.attr_path; volPath = data.content.vol_path;
            nSegments = data.content.n_segments; ptrPath = data.content.ptr_path;
            exchange_x = data.content.exchange_x; exchange_z = data.content.exchange_z;
            if (data.content.exchange_y) { exchange_y = data.content.exchange_y; }
            flowPath = data.content.flow_path; lengthPath = data.content.length_path;
            areaPath = data.content.area_path; n_layers = nLayers().value.trim();
            if (!n_layers || n_layers === '') { alert("The field 'Nr. sigma layers' is required"); return; }
            srfPath = data.content.srf_path; vdfPath = data.content.vdf_path;
            temPath = data.content.tem_path; salPath = data.content.sal_path;
            const sourceTable = getDataFromTable(sourcesTable(), true);         
            const obsTable = getDataFromTable(obsPointTable(), true);
            const loadTable = getDataFromTable(loadsPointTable(), true);
            if (loadTable.rows.length === 0) { alert('No loads data found. Please add at least one load.'); return; }
            const timeData = timePreview().value.trim();
            if (!timeData || timeData === '') { alert("Post-processing field is required"); return; }
            if (btn.dataset.info === 'chemical') {
                subKey = chemicalSelector().value; folderName = chemicalName().value.trim();
                useforsFrom = useforsFromChemical(); useforsTo = useforsToChemical();
                usefors = useforsChemical(); initial_area = initialAreaChemical();
                maxiter = maxInterChemical(); tolerance = toleranceChemical(); scheme = schemeChemical(); 
            } else if (btn.dataset.info === 'physical') {
                subKey = physicalSelector().value; folderName = physicalName().value.trim();
                useforsFrom = useforsFromPhysical(); useforsTo = useforsToPhysical();
                usefors = useforsPhysical(); initial_area = initialAreaPhysical();
                maxiter = maxInterPhysical(); tolerance = tolerancePhysical(); scheme = schemePhysical();
            } else if (btn.dataset.info === 'microbial') {
                subKey = microbialSelector().value; folderName = microbialName().value.trim();
                useforsFrom = useforsFromMirobial(); useforsTo = useforsToMirobial();
                usefors = useforsMicrobial(); initial_area = initialAreaMirobial();
                maxiter = maxInterMirobial(); tolerance = toleranceMirobial(); scheme = schemeMirobial();
            }
            if (!folderName || folderName === '') { alert("Name of substance is required"); return; }
            const userforValue = usefors.value.trim();
            if (userforValue === '') { alert("The field 'Assigned Substance' must has at least one value"); return; }
            const valueFrom = Array.from(useforsFrom.options).map(option => option.value);
            const valueTo = Array.from(useforsTo.options).map(option => option.value);
            const initialArea = initial_area.value.trim();
            if (maxiter.value === '' || parseInt(maxiter.value) <= 0) { alert('Please define maximum number of iterations.'); return; }
            if (tolerance.value === '' || parseFloat(tolerance.value) <= 0) { alert('Please define tolerance.'); return; }
            const params = { mode: btn.dataset.info, projectName: name, key: subKey, folderName: folderName,
                hydName: hydPath, nLayers: n_layers, timeStep1: timeStep1, timeStep2: timeStep2, nSegments: nSegments,
                startTime: toUTC(start), stopTime: toUTC(stop), exchangeY: exchange_y, exchangeX: exchange_x,
                exchangeZ: exchange_z, attrPath: attrPath_, volPath: volPath, ptrPath: ptrPath, areaPath: areaPath, 
                flowPath: flowPath, lengthPath: lengthPath, srfPath: srfPath, vdfPath: vdfPath, temPath: temPath,
                salPath: salPath, useforsFrom: valueFrom, useforsTo: valueTo, usefors: userforValue,
                sources: sourceTable.rows, obsPoints: obsTable.rows, loadsData: loadTable.rows, timeTable: timeData, 
                initial: initialArea, maxiter: maxiter.value, tolerance: tolerance.value, scheme: scheme.value
            }
            const waq_config = await sendQuery('waq_config_writer', params);
            if (waq_config.status === 'error') { alert(waq_config.message); return; }
            alert(waq_config.message);
        });
    });
}

function initializeProject(){
    // Update project name
    projectName().addEventListener('click', () => {
        if (projects().children.length === 0) {
            projectList.forEach(p => {
                const li = document.createElement("li");
                li.textContent = p;
                li.addEventListener('mousedown', () => {
                    projectName().value = p; projects().style.display = "none";
                });
                projects().appendChild(li);
            });
        }
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
    projects().addEventListener('mousedown', async () => {
        const name = projectName().value.trim();
        const data = await sendQuery('select_waq', {projectName: name});
        if (!name || name === '' || data.status === "error") { 
            waqSelector().style.display = "none"; waqSelector().value = '';
            waqLabel().style.display = "none"; projectCloner().style.display = "none"; 
            projectDeleter().style.display = "none"; return; 
        }
        waqContent = data.content;
        const waqTemp = waqContent.map(name => `<option value="${name}">${name}</option>`).join('');
        const defaultWAQ = `<option value="">-- New WAQ model --</option>`;
        waqSelector().innerHTML = defaultWAQ + waqTemp; waqSelector().value = '';
        waqSelector().style.display = "flex"; waqLabel().style.display = "flex"; 
        projectCloner().style.display = "flex"; projectDeleter().style.display = "flex";
    });
    // Create new project
    projectCreator().addEventListener('click', async () => {
        const name = projectName().value.trim();
        if (!name || name.trim() === '') { alert('Please define project.'); return; }
        // Find .hyd file
        const data = await sendQuery('select_hyd', {projectName: name});
        if (data.status === "error") {alert(data.message); return;}
        setupTabs(document);
        // Show tabs
        sectionTab().style.display = "block"; sectionDescription().style.display = "none";
        sourcesContainer().style.display = data.content.sink_sources.length > 0 ? "block":"none";
        fillTable(data.content.sink_sources, sourcesTable(), true);
        // Assign values
        hydFilename().value = data.content.filename; volPath = data.content.vol_path;
        timeStep1 = data.content.time_step1; timeStep2 = data.content.time_step2;
        nSegments = data.content.n_segments; attrPath_ = data.content.attr_path;
        exchange_x = data.content.exchange_x; exchange_z = data.content.exchange_z;
        if (data.content.exchange_y) { exchange_y = data.content.exchange_y; }
        ptrPath = data.content.ptr_path; areaPath = data.content.area_path;
        flowPath = data.content.flow_path; lengthPath = data.content.length_path;
        if (data.content.n_layers) { nLayers().value = data.content.n_layers; }
        srfPath = data.content.srf_path; vdfPath = data.content.vdf_path;
        temPath = data.content.tem_path; salPath = data.content.sal_path;
        startTime().value = data.content.start_time; stopTime().value = data.content.stop_time;
        // Set default values
        deleteTable(obsPointTable()); addRowToTable(obsPointTable(), ['Name', 'Latitude', 'Longitude']);
        deleteTable(loadsPointTable()); addRowToTable(loadsPointTable(), ['Name', 'Latitude', 'Longitude']);
        // Physical tab
        physicalSelector().value = ''; physicalName().value = ''; 
        useforsFromPhysical().innerHTML = ''; useforsToPhysical().innerHTML = '';
        useforsPhysical().value = ''; initialFromPhysical().innerHTML = '';
        initialAreaPhysical().value = ''; schemePhysical().value = '15';
        maxInterPhysical().value = '500'; tolerancePhysical().value = '1E-07';
        // Chemical tab
        chemicalSelector().value = ''; chemicalName().value = '';
        useforsFromChemical().innerHTML = ''; useforsToChemical().innerHTML = '';
        useforsChemical().value = ''; initialFromChemical().innerHTML = '';
        initialAreaChemical().value = ''; schemeChemical().value = '15';
        maxInterChemical().value = '500'; toleranceChemical().value = '1E-07';
        // Microbial tab
        microbialSelector().value = ''; microbialName().value = '';
        useforsFromMirobial().innerHTML = ''; useforsToMirobial().innerHTML = '';
        useforsMicrobial().value = ''; initialFromMirobial().innerHTML = '';
        initialAreaMirobial().value = ''; schemeMirobial().value = '15';
        maxInterMirobial().value = '500'; toleranceMirobial().value = '1E-07';
        timePreview().value = ''; timePreviewContainer().style.display = 'none';
        const waqValue = waqSelector().value;
        if (waqValue !== '') { 
            const data = await sendQuery('load_waq', {projectName: name, waqName: waqValue});
            if (data.status === "error") {alert(data.message); return;}
            if (data.content.obs.length > 0) { fillTable(data.content.obs, obsPointTable(), true); }
            fillTable(data.content.loads, loadsPointTable(), true);
            deleteTable(timeTable()); fillTable(data.content.time_data, timeTable(), true);
            if (data.content.mode === 'physical') {
                physicalSelector().value = data.content.key;
                physicalName().value = data.content.name;
                chemicalSelector().value = ''; chemicalName().value = '';
                microbialSelector().value = ''; microbialName().value = '';
                from_usefors = useforsFromPhysical(); to_usefors = useforsToPhysical();
                from_initial = initialFromPhysical(); usefors = useforsPhysical();
                initial_area = initialAreaPhysical(); scheme = schemePhysical();
                maxiter = maxInterPhysical(); tolerance = tolerancePhysical();
            } else if (data.content.mode === 'chemical') {
                chemicalSelector().value = data.content.key;
                chemicalName().value = data.content.name;
                physicalSelector().value = ''; physicalName().value = '';
                microbialSelector().value = ''; microbialName().value = '';
                from_usefors = useforsFromChemical(); to_usefors = useforsToChemical();
                from_initial = initialFromChemical(); usefors = useforsChemical();
                initial_area = initialAreaChemical(); scheme = schemeChemical();
                maxiter = maxInterChemical(); tolerance = toleranceChemical();
            } else if (data.content.mode === 'microbial') {
                microbialSelector().value = data.content.key;
                microbialName().value = data.content.name;
                physicalSelector().value = ''; physicalName().value = '';
                chemicalSelector().value = ''; chemicalName().value = '';
                from_usefors = useforsFromMirobial(); to_usefors = useforsToMirobial();
                from_initial = initialFromMirobial(); usefors = useforsMicrobial();
                initial_area = initialAreaMirobial(); scheme = schemeMirobial();
                maxiter = maxInterMirobial(); tolerance = toleranceMirobial();
            }
            usefors.value = data.content.usefors; initial_area.value = data.content.initial;
            scheme.value = data.content.scheme; maxiter.value = data.content.maxiter;
            tolerance.value = data.content.tolerance;
            data.content.useforsFrom.forEach(item => {
                [from_usefors, from_initial].forEach(select => {
                    const option = document.createElement('option');
                    option.value = item; option.text = item;
                    select.add(option);
                })
            });
            data.content.useforsTo.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                to_usefors.add(option);
            });
            timePreview().value = data.content.times; timePreviewContainer().style.display = 'block';
        }
    });
    projectCloner().addEventListener('click', async () => { 
        const name = projectName().value.trim();
        if (!name || name === '') { alert('Please select scenario first.'); return; }
        const newName = prompt('Please enter a name for the new WAQ scenario.');
        if (!newName || newName === '') { alert('Please define clone scenario name.'); return; }
        if (nameChecker(newName)) { alert('Scenario name contains invalid characters.'); return; }
        projectCloner().innerHTML = 'Cloning...';
        const data = await sendQuery('clone_waq', {
            projectName: name, oldName: waqSelector().value, newName: newName
        });
        projectCloner().innerHTML = 'Clone Scenario'; alert(data.message);
        if (data.status === "error") { return; }
        waqContent.push(newName); waqSelector().innerHTML = '';
        const defaultWAQ = `<option value="">-- New WAQ model --</option>`;
        const waqTemp = waqContent.map(name => `<option value="${name}">${name}</option>`).join('');
        waqSelector().innerHTML = defaultWAQ + waqTemp; waqSelector().value = newName; projectCreator().click();
    });
    projectDeleter().addEventListener('click', async () => {
        const name = projectName().value.trim(), waqName = waqSelector().value;
        projectDeleter().innerHTML = 'Deleting...';
        const data = await sendQuery('delete_file', { projectName: name, name: waqName });
        projectDeleter().innerHTML = 'Delete Scenario';
        alert(data.message);
        if (data.status === "error") { return; }
        waqSelector().innerHTML = '';
        waqContent = waqContent.filter(item => item !== waqName);
        const defaultWAQ = `<option value="">-- New WAQ model --</option>`;
        const waqTemp = waqContent.map(name => `<option value="${name}">${name}</option>`).join('');
        waqSelector().innerHTML = defaultWAQ + waqTemp; waqSelector().value = ''; projectCreator().click();
    });
    waqSelector().addEventListener('change', async () => { projectCreator().click(); });    
}
await getProjectList(); initializeProject(); updateOption();
