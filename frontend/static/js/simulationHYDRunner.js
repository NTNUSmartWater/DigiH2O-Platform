const projectSelector = () => document.getElementById("options");
const runBtn = () => document.getElementById("run-button");
const progressbar = () => document.getElementById("progressbar");
const progressText = () => document.getElementById("progress-text");
const infoArea = () => document.getElementById('textarea');
const checkboxContainer = () => document.getElementById('checkbox-container');
const showCheckbox = () => document.getElementById('show-checkbox');
const textareaWrapper = () => document.getElementById('form-row-textarea');

let currentProject = null, height = 0, isRunning = false, logInterval = null, lastOffset = 0;

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

function updateLogHYD(project, progress_bar, progress_text, info, seconds){
    logInterval = setInterval(async () => {
        try {
            const statusRes = await sendQuery('check_sim_status_hyd', {projectName: project});
            if (statusRes.status === "running" || statusRes.status === "not_started") {
                progress_text.innerText = statusRes.complete || '';
                progress_bar.value = statusRes.progress || 0;
            } else if (statusRes.status === "postprocessing") {
                progress_text.innerText = statusRes.message; 
                progress_bar.value = 100;
            } else if (statusRes.status === "finished") {
                progress_text.innerText = statusRes.message; 
                isRunning = false; progress_bar.value = 100;
                if (logInterval) { clearInterval(logInterval); logInterval = null; }
            } else {
                progress_text.innerText = statusRes.message;
                info.value += statusRes.message; isRunning = false; progress_bar.value = 0;
                if (logInterval) { clearInterval(logInterval); logInterval = null; }
            }
            const res = await fetch(`/sim_log_tail/${project}?offset=${lastOffset}&log_file=log_hyd.txt`);
            if (!res.ok) return;
            const data = await res.json();
            for (const line of data.lines) { info.value += line + "\n"; }
            lastOffset = data.offset;
        } catch (error) { clearInterval(logInterval); logInterval = null; }
    }, seconds * 1000);
}

function updateSelection(){
    getProjectList(projectSelector());
    showCheckbox().addEventListener('change', checkboxUpdate);
    projectSelector().addEventListener('change', async() => {
        const projectName = projectSelector().value;
        if (!projectName) {
            checkboxContainer().style.display = 'none';
            progressText().innerText = "No simulation running."; progressbar().value = 0;
            textareaWrapper().style.display = 'none'; alert('Please select a project.'); return;
        }
        checkboxContainer().style.display = 'block'; textareaWrapper().style.display = 'block';
        const statusRes = await sendQuery('check_sim_status_hyd', {projectName: projectName});
        if (statusRes.status === "running") {
            const res = await fetch(`/sim_log_full/${projectName}?log_file=log_hyd.txt`);
            if (res.ok) {
                const data = await res.json();
                infoArea().value = data.content || ''; lastOffset = data.offset;
                progressText().innerText = statusRes.complete || '';
                progressbar().value = statusRes.progress || 0;
            }
            showCheckbox().checked = true; isRunning = true; currentProject = projectName;
            // Run hydrodynamics simulation and Update logs every 10 seconds
            updateLogHYD(projectName, progressbar(), progressText(), infoArea(), 10);
        } else {
            progressText().innerText = "No simulation running."; 
            showCheckbox().checked = false; progressbar().value = 0;
        }
        checkboxUpdate();
    });
    // Run new simulation
    runBtn().addEventListener('click', async () => {
        currentProject = projectSelector().value;
        if (!currentProject) {alert('Please select a project.'); return;}
        // Check if simulation is running
        const statusRes = await sendQuery('check_sim_status_hyd', {projectName: currentProject});
        if (statusRes.status === "running") {
            alert("Simulation is already running for this project."); isRunning = true; return;
        }
        const res = await sendQuery('check_folder', {projectName: currentProject, folder: ['output']});
        if (res.status === "ok") { if (!confirm("Output exists. Re-run will overwrite it. Continue?")) return; }
        const start = await sendQuery('start_sim_hyd', {projectName: currentProject});
        if (start.status === "error") {alert(start.message); return;}
        infoArea().value = ''; progressbar().value = 0;
        progressText().innerText = 'Start running hydrodynamic simulation...';
        // Run hydrodynamics simulation and Update logs every 10 seconds
        updateLogHYD(currentProject, progressbar(), progressText(), infoArea(), 10);
    });
}
updateSelection();