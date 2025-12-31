const scenarioSelector = () => document.getElementById("options-scenario");
const labelScenario = () => document.getElementById("label-scenario");
const waqSelector = () => document.getElementById("options-waq");
const labelWAQ = () => document.getElementById("label-waq");
const runBtn = () => document.getElementById("run-button");
const progressbar = () => document.getElementById("progressbar");
const progressText = () => document.getElementById("progress-text");
const infoArea = () => document.getElementById('textarea');
const checkboxContainer = () => document.getElementById('checkbox-container');
const showCheckbox = () => document.getElementById('show-checkbox');
const textareaWrapper = () => document.getElementById('form-row-textarea');

let currentProject = null, height = 0, logIntervalHYD = null, 
    logIntervalWAQ = null, lastOffsetHYD = 0, lastOffsetWAQ = 0;
const APP_MODE = window.APP_MODE; 

async function sendQuery(functionName, content){
    const response = await fetch(`/${functionName}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(content)});
    const data = await response.json();
    return data;
}

function checkboxUpdate(){
    if (APP_MODE === 'waq' && scenarioSelector().value !== '') { 
        labelWAQ().style.display = 'flex'; waqSelector().style.display = 'flex'; 
    } else { labelWAQ().style.display = 'none'; waqSelector().style.display = 'none'; }
    const show = showCheckbox().checked;
    textareaWrapper().style.display = show ? 'block' : 'none';
    height = show ? 250 : 120;
    requestAnimationFrame(() => { window.parent.postMessage({ type: 'resize-simulation', height }, '*'); });
}

async function getProjectList(target){
    // Update project
    const data = await sendQuery('select_project', {filename: '', key: 'getProjects', folder_check: 'input'});
    if (!data || !data.content) {
        target.innerHTML = `<option value="">--- No projects found ---</option>`; return;
    }
    const options = data.content.map(name => `<option value="${name}">${name}</option>`).join('');
    const defaultOption = `<option value="" selected>--- No selected ---</option>`;
    target.innerHTML = defaultOption + options;
    showCheckbox().checked = false; checkboxUpdate();
}

function updateLogHYD(project, progress_bar, progress_text, info, seconds){
    logIntervalHYD = setInterval(async () => {
        try {
            const statusRes = await sendQuery('check_sim_status_hyd', {projectName: project});
            if (statusRes.status === "running") {
                progress_text.innerText = statusRes.message;
                progress_bar.value = statusRes.progress;
            } else {
                progress_text.innerText = statusRes.message;
                info.value += statusRes.message;
                progress_bar.value = statusRes.progress;
                if (logIntervalHYD) { clearInterval(logIntervalHYD); logIntervalHYD = null; }
            }
            const res = await fetch(`/sim_log_tail_hyd/${project}?offset=${lastOffsetHYD}&log_file=log_hyd.txt`);
            if (!res.ok) return;
            const data = await res.json();
            for (const line of data.lines) { info.value += line + "\n"; }
            lastOffsetHYD = data.offset;
        } catch (error) { clearInterval(logIntervalHYD); logIntervalHYD = null; }
    }, seconds * 1000);
}

function updateLogWAQ(project, progress_bar, progress_text, info, seconds) {
    logIntervalWAQ = setInterval(async () => {
        try {
            const statusRes = await sendQuery('check_sim_status_waq', {projectName: project});
            if (statusRes.status === "running") {
                progress_text.innerText = statusRes.message;
                progress_bar.value = statusRes.progress;
            } else {
                progress_text.innerText = statusRes.message;
                progress_bar.value = statusRes.progress;
                if (logIntervalWAQ) { clearInterval(logIntervalWAQ); logIntervalWAQ = null; }
            }
            const res = await fetch(`/sim_log_tail_waq/${project}?offset=${lastOffsetWAQ}&log_file=log_waq.txt`);
            if (!res.ok) return;
            const data = await res.json(); if (info.value !== '') { info.value = ''; }
            for (const line of data.lines) { info.value += line + "\n"; }
            lastOffsetWAQ = data.offset;
        } catch (error) { clearInterval(logIntervalWAQ); logIntervalWAQ = null; }
    }, seconds * 1000);
}

function updateSelection(){
    getProjectList(scenarioSelector());
    showCheckbox().addEventListener('change', checkboxUpdate);
    scenarioSelector().addEventListener('change', async() => {
        const projectName = scenarioSelector().value;
        if (!projectName) {
            checkboxContainer().style.display = 'none'; progressText().innerText = ""; progressbar().value = 0;
            labelWAQ().style.display = 'none'; waqSelector().style.display = 'none';
            textareaWrapper().style.display = 'none'; return;
        }
        if (APP_MODE === 'hyd') { // Work with HYD simulation
            const statusRes = await sendQuery('check_sim_status_hyd', {projectName: projectName});
            if (statusRes.status === "running") {
                const res = await fetch(`/sim_log_full/${projectName}?log_file=log_hyd.txt`);
                if (res.ok) {
                    const data = await res.json();
                    infoArea().value = data.content || ''; lastOffsetHYD = data.offset;
                }
                showCheckbox().checked = true;
                // Run hydrodynamics simulation and Update logs every 10 seconds
                updateLogHYD(projectName, progressbar(), progressText(), infoArea(), 10);
            } else { showCheckbox().checked = false; }
            progressText().innerText = statusRes.message; progressbar().value = statusRes.progress;
        } else if (APP_MODE === 'waq'){ // Work with WAQ simulation
            const data = await sendQuery('select_project', {filename: projectName, key: 'getWAQs', folder_check: 'input'});
            if (data.status === "error") {
                alert(data.message); labelWAQ().style.display = 'none'; 
                waqSelector().style.display = 'none'; return;
            }
            labelWAQ().style.display = 'flex'; waqSelector().style.display = 'flex'; showCheckbox().checked = false;
            waqSelector().innerHTML = data.content.map(name => `<option value="${name}">${name}</option>`).join('');
            const statusRes = await sendQuery('check_sim_status_waq', {projectName: projectName});
            if (statusRes.status === "running") {
                const res = await fetch(`/sim_log_full/${projectName}?log_file=log_waq.txt`);
                if (res.ok) {
                    const data = await res.json();
                    infoArea().value = data.content || ''; lastOffsetWAQ = data.offset;
                }
                showCheckbox().checked = true;
                // Run water quality simulation and Update logs every 0.5 seconds
                updateLogWAQ(projectName, progressbar(), progressText(), infoArea(), 0.5);
            } else { showCheckbox().checked = false; }
            progressText().innerText = statusRes.message; progressbar().value = statusRes.progress;
        }
        checkboxContainer().style.display = 'block'; textareaWrapper().style.display = 'block'; checkboxUpdate(); 
    });
    // Run new simulation
    runBtn().addEventListener('click', async () => {
        currentProject = scenarioSelector().value;
        if (!currentProject || currentProject === '') {alert('Please select a scenario.'); return;}
        if (APP_MODE === 'hyd') { // Check if HYD simulation is running
            const statusRes = await sendQuery('check_sim_status_hyd', {projectName: currentProject});
            if (statusRes.status === "running") { alert("HYD simulation is already running."); return; }
            const res = await sendQuery('check_folder', {projectName: currentProject, folder: 'output', key: 'hyd'});
            if (res.status === "ok") { if (!confirm("Output exists. Re-run will overwrite it. Continue?")) return; }
            const start = await sendQuery('start_sim_hyd', {projectName: currentProject});
            if (start.status === "error") {alert(start.message); return;}
            infoArea().value = ''; progressbar().value = 0;
            progressText().innerText = 'Preparing data for the HYD simulation...';
            updateLogHYD(currentProject, progressbar(), progressText(), infoArea(), 10);
        } else if (APP_MODE === 'waq'){ // Check if WAQ simulation is running
            const statusRes = await sendQuery('check_sim_status_waq', {projectName: currentProject});
            if (statusRes.status === "running") { alert("WAQ simulation is already running."); return; }
            const res = await sendQuery('check_folder', {projectName: currentProject, folder: waqSelector().value, key: 'waq'});
            if (res.status === "ok") { if (!confirm("Output exists. Re-run will overwrite it. Continue?")) return; }
            progressText().innerText = 'Preparing data for the WAQ simulation...';
            infoArea().value = ''; progressbar().value = 0;
            const start = await sendQuery('start_sim_waq', {projectName: currentProject, waqName: waqSelector().value});
            if (start.status === "error") {alert(start.message); return;}
            updateLogWAQ(currentProject, progressbar(), progressText(), infoArea(), 0.5);
        }
    });
}
updateSelection();