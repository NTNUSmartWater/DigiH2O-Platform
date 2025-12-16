const projectSelector = () => document.getElementById("options");
const runBtn = () => document.getElementById("run-button");
const progressbar = () => document.getElementById("progressbar");
const progressText = () => document.getElementById("progress-text");
const infoArea = () => document.getElementById('textarea');
const checkboxContainer = () => document.getElementById('checkbox-container');
const showCheckbox = () => document.getElementById('show-checkbox');
const textareaWrapper = () => document.getElementById('form-row-textarea');

let ws = null, content = '', currentProject = null, height = 0, isRunning = false, logInterval = null;

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

// function statusUpdate(info, barObject, textObject) {
//     if (info.startsWith("[ERROR]")) { 
//         alert(info.replace('[ERROR]','')); 
//         textObject().innerText = "Simulation finished unsuccessfully.";
//         if (logInterval) { clearInterval(logInterval); logInterval = null; }
//     }
//     if (info.startsWith("[PROGRESS]")) {
//         // Update progress
//         const values = info.replace('[PROGRESS] ', '').trim().split('|');
//         const percent = parseFloat(values[0] || 0), time_used = values[1] || 'N/A', time_left = values[2] || 'N/A';
//         textObject().innerText = `Completed: ${percent}% [Used: ${time_used} → Left: ${time_left}]`;
//         barObject().value = percent;
//     }
//     if (info.startsWith("[POSTPROCESS]")) {
//         textObject().innerText = info.replace('[POSTPROCESS]',''); barObject().value = 100; 
//     }
//     if (info.startsWith("[FINISHED]")) {
//         textObject().innerText = info.replace('[FINISHED]',''); isRunning = false; barObject().value = 100;
//         if (logInterval) { clearInterval(logInterval); logInterval = null; }
//     }
// }

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
            const res = await fetch(`/sim_log_full/${projectName}`);
            if (res.ok) {
                const data = await res.json();
                infoArea().value = data.content || '';
                progressText().innerText = statusRes.complete || '';
                progressbar().value = statusRes.progress || 0;
            }
            showCheckbox().checked = true;
        } else {
            progressText().innerText = "No simulation running."; 
            showCheckbox().checked = false; progressbar().value = 0;
        }
        checkboxUpdate();
    });
    // Run new simulation
    runBtn().addEventListener('click', async () => {
        let lastContent = '';
        if (isRunning) return; 
        isRunning = true; currentProject = projectSelector().value;
        if (!currentProject) {alert('Please select a project.'); return;}
        // Check if simulation is running
        const statusRes = await sendQuery('check_sim_status_hyd', {projectName: currentProject});
        if (statusRes.status === "running") {
            alert("Simulation is already running for this project."); return;
        }
        const res = await sendQuery('check_folder', {projectName: currentProject, folder: ['output']});
        if (res.status === "ok") {
            if (!confirm("Output exists. Re-run will overwrite it. Continue?")) return;
        }
        const start = await sendQuery('start_sim_hyd', {projectName: currentProject});
        if (start.status === "error") {alert(start.message); return;}
        content = ''; infoArea().value = ''; progressbar().value = 0;
        progressText().innerText = 'Start running hydrodynamic simulation...';
        // // Run hydrodynamics simulation
        // const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        // if (ws) ws.close();
        // ws = new WebSocket(`${protocol}://${window.location.host}/sim_progress_hyd/${currentProject}`);
        // Update logs every 5 seconds
        logInterval = setInterval(async () => {
            const res = await fetch(`/sim_log_tail/${currentProject}`);
            if (!res.ok) return;
            const data = await res.json();
            for (const line of data.lines) {
                infoArea().value += line + "\n";
                // statusUpdate(line, progressbar, progressText);
            }
            const statusRes = await sendQuery('check_sim_status_hyd', {projectName: currentProject});
            if (statusRes.status === "running") {
                progressText().innerText = statusRes.complete || '';
                progressbar().value = statusRes.progress || 0;
            } else if (statusRes.status === "postprocessing") {
                progressText().innerText = 'Reorganizing outputs. Please wait...'; progressbar().value = 100;
            } else if (statusRes.status === "finished") {
                progressText().innerText = 'Finished running hydrodynamic simulation.'; isRunning = false; progressbar().value = 100;
                if (logInterval) { clearInterval(logInterval); logInterval = null; }
            } else {
                // alert(info.replace('[ERROR]','')); 
                progressText().innerText = "Simulation finished unsuccessfully.";
                if (logInterval) { clearInterval(logInterval); logInterval = null; }
            }


            // try {
            //     const res = await fetch(`/sim_temp_log/${currentProject}`);
            //     if (!res.ok) return;
            //     const data = await res.json();
            //     const newContent = data.content;
            //     console.log('New content:', newContent);
            //     if (newContent !== lastContent && newContent) {
            //         if (!newContent.includes("[PROGRESS]")) { content += newContent + '\n';}
            //         infoArea().value = content;
            //         statusUpdate(newContent, progressbar, progressText);
            //         lastContent = newContent;
            //     }
            // } catch (error) { 
            //     console.error("Fetch log failed:", error); 
            //     if (logInterval) { clearInterval(logInterval); logInterval = null; }
            // }
        }, 3000);
    });
}
updateSelection();