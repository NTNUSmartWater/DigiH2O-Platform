const projectSelector = () => document.getElementById("options");
const runBtn = () => document.getElementById("run-button");
const progressbar = () => document.getElementById("progressbar");
const progressText = () => document.getElementById("progress-text");
const infoArea = () => document.getElementById('textarea');
const checkboxContainer = () => document.getElementById('checkbox-container');
const showCheckbox = () => document.getElementById('show-checkbox');
const textareaWrapper = () => document.getElementById('form-row-textarea');

let ws = null, content = '', currentProject = null, height = 0, isRunning = false;

async function sendQuery(functionName, content){
    const response = await fetch(`/${functionName}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(content)});
    const data = await response.json();
    return data;
}

function checkboxUpdate(){
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

function statusUpdate(info, barObject, textObject) {
    if (info.startsWith("[ERROR]")) { 
        alert(info.replace('[ERROR]','')); 
        textObject().innerText = "Simulation finished unseccessfully.";
        return false;
    }
    if (info.startsWith("[PROGRESS]")) {
        // Update progress
        const values = info.replace('[PROGRESS] ', '').trim().split('|');
        const percent = parseFloat(values[0] || 0), time_used = values[1] || 'N/A', time_left = values[2] || 'N/A';
        textObject().innerText = `Completed: ${percent}% [Used: ${time_used} → Left: ${time_left}]`;
        barObject().value = percent;
    }
    if (info.startsWith("[FINISHED]")) textObject().innerText = info.replace('[FINISHED]','');
    return true;
}

function updateSelection(){
    getProjectList(projectSelector());
    showCheckbox().addEventListener('change', checkboxUpdate);
    projectSelector().addEventListener('change', async() => {
        const projectName = projectSelector().value;
        if (!projectName) {
            checkboxContainer().style.display = 'none';
            progressText().innerText = "No simulation running."; progressbar().value = 0;
            textareaWrapper().style.display = 'none';
            alert('Please select a project.'); return;
        }
        checkboxContainer().style.display = 'block'; textareaWrapper().style.display = 'block';
        const statusRes = await sendQuery('check_sim_status_hyd', {projectName: projectName});
        if (statusRes.status === "running") {
            if (!ws || ws.readyState === WebSocket.CLOSED) {
                ws = new WebSocket(`ws://${window.location.host}/sim_progress_hyd/${projectName}`);
                ws.onmessage = (event) => {
                    if (!event.data.includes("[PROGRESS]")) { content += event.data + '\n';}
                    infoArea().value = content;
                    statusUpdate(event.data, progressbar, progressText);
                };
            }
            showCheckbox().checked = true;
        } else {
            showCheckbox().checked = false;
            progressText().innerText = "No simulation running."; progressbar().value = 0;
        }
        checkboxUpdate();
    });
    // Run new simulation
    runBtn().addEventListener('click', async () => {
        if (isRunning) return; isRunning = true;
        const projectName = projectSelector().value;
        if (!projectName) {alert('Please select a project.'); return;}
        // Check if simulation is running
        const statusRes = await sendQuery('check_sim_status_hyd', {projectName: projectName});
        if (statusRes.status === "running") {
            alert("Simulation is already running for this project."); return;
        }
        const res = await sendQuery('check_folder', {projectName: projectName, folder: ['output']});
        if (res.status === "ok") {
            if (!confirm("Output exists. Re-run will overwrite it. Continue?")) return;
        }
        const start = await sendQuery('start_sim_hyd', {projectName: projectName});
        if (start.status === "error") {alert(start.message); return;}
        currentProject = projectName; content = ''; infoArea().value = ''; progressbar().value = 0;
        progressText().innerText = 'Start running hydrodynamic simulation...';
        // Run hydrodynamics simulation
        if (ws) ws.close();
        ws = new WebSocket(`ws://${window.location.host}/sim_progress_hyd/${projectName}`);
        ws.onmessage = (event) => {
            if (!event.data.includes("[PROGRESS]")) { content += event.data + '\n';}
            infoArea().value = content;
            statusUpdate(event.data, progressbar, progressText);
            if (event.data.includes("[FINISHED]")) isRunning = false;
        };
    });
}
updateSelection();