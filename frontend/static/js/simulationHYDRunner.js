const projectSelector = () => document.getElementById("options");
const runBtn = () => document.getElementById("run-button");
const progressbar = () => document.getElementById("progressbar");
const progressText = () => document.getElementById("progress-text");
const infoArea = () => document.getElementById('textarea');
const showCheckbox = () => document.getElementById('show-checkbox');
const textareaWrapper = () => document.getElementById('form-row-textarea');

let ws = null, content = '', currentProject = null, height = 0;

async function sendQuery(functionName, content){
    const response = await fetch(`/${functionName}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(content)});
    const data = await response.json();
    return data;
}

async function getProjectList(target){
    // Update project
    const data = await sendQuery('select_project', {filename: '', key: 'getProjects', folder_check: 'input'});
    const options = data.content.map(row => `<option value="${row}">${row}</option>`).join(' ');
    const defaultOption = `<option value="" selected>--- No selected ---</option>`;
    target.innerHTML = defaultOption + options;
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
        const percent = parseFloat(values[0]), time_used = values[1], time_left = values[2];
        textObject().innerText = 'Completed: ' + percent + '% [Time used: ' + time_used + ' -->  Time left: ' + time_left + ']';
        barObject().value = percent;
    }
    if (info.startsWith("[FINISHED]")) textObject().innerText = info.replace('[FINISHED]','');
    return true;
}

function updateSelection(){
    getProjectList(projectSelector());
    showCheckbox().addEventListener('change', () => {
        if (showCheckbox().checked) { textareaWrapper().style.display = 'block'; height = 250;
        } else { textareaWrapper().style.display = 'none'; height = 120; }
        setTimeout(() => { window.parent.postMessage({ type: 'resize-simulation', height }, '*'); }, 10);
    })
    projectSelector().addEventListener('change', async() => {
        const projectName = projectSelector().value;
        if (!projectName || projectName === '') {alert('Please select a project.'); return;}
        const statusRes = await sendQuery('check_sim_status_hyd', {projectName: projectName});
        if (statusRes.status === "running") {
            currentProject = projectName;
            content = statusRes.logs.join("\n");
            progressText().innerText = `Simulation is running: ${statusRes.progress}%`;
            progressbar().value = statusRes.progress;
            // Open websocket connection to get simulation progress
            ws = new WebSocket(`ws://${window.location.host}/sim_progress_hyd/${projectName}`);
            ws.onmessage = (event) => {
                const success = statusUpdate(event.data, progressbar, progressText);
                if (!success) return;
            };
        } else {
            progressText().innerText = "No simulation running."; progressbar().value = 0;
        }
    });
    // Run new simulation
    runBtn().addEventListener('click', async () => {
        const projectName = projectSelector().value;
        if (!projectName || projectName === '') {alert('Please select a project.'); return;}
        // Check if simulation is running
        const statusRes = await sendQuery('check_sim_status_hyd', {projectName: projectName});
        if (statusRes.status === "running") {
            alert("Simulation is already running for this project."); return;
        }
        const res = await sendQuery('check_folder', {projectName: projectName, folder: ['output']});
        if (res.status === "ok") {
            const result = confirm("Output is available in this project." + 
                "\nRe-run simulation will overwrite the existing output." +
                "\nDo you want to continue?"
            );
            if (!result) return;
        }
        const res_check = await sendQuery('start_sim_hyd', {projectName: projectName});
        if (res_check.status === "error") {alert(res_check.message); return;}
        currentProject = projectName; content = '';
        // Run hydrodynamics simulation
        ws = new WebSocket(`ws://${window.location.host}/sim_progress_hyd/${projectName}`);
        progressText().innerText = 'Start running hydrodynamic simulation...';
        ws.onmessage = (event) => {
            if (!event.data.includes("[PROGRESS]")) { content += event.data + '\n';}
            infoArea().value = content;
            const success = statusUpdate(event.data, progressbar, progressText);
            if (!success) return;
        };
    });
}

updateSelection(); //updateParentHeight();