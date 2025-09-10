const projectSelector = () => document.getElementById("options");
const runBtn = () => document.getElementById("run-button");
const stopBtn = () => document.getElementById("stop-button");
const infoArea = () => document.getElementById("textarea");

let ws = null, content = '', currentProject = null;;


async function sendQuery(functionName, content){
    const response = await fetch(`/${functionName}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(content)});
    const data = await response.json();
    return data;
}

async function getProjectList(target){
    // Update project
    const data = await sendQuery('select_project', {filename: '', key: 'getProjects', folder_check: ''});
    const options = data.content.map(row => `<option value="${row}">${row}</option>`).join(' ');
    const defaultOption = `<option value="" selected>--- No selected ---</option>`;
    target.innerHTML = defaultOption + options;
}

function updateSelection(){
    getProjectList(projectSelector());
    runBtn().addEventListener('click', async () => {
        const projectName = projectSelector().value;
        if (projectName === '') {alert('Please select a project.'); return;}
        const data = await sendQuery('check_project', {projectName: projectName});
        if (data.status === "ok") {
            const result = confirm("Output is available in this project." + 
                "\nRe-run simulation will overwrite the existing output." +
                "\nDo you want to continue?"
            );
            if (!result) return;
        }
        currentProject = projectName;
        ws = new WebSocket(`ws://${window.location.host}/run_sim/${projectName}`);
        content = '';
        ws.onmessage = (event) => {
            content += event.data + '\n';
            infoArea().value = content;
        };
    });
    stopBtn().addEventListener('click', async () => {
        if (ws) { ws.close(); ws = null; }
        if (currentProject) {
            const data = await sendQuery('stop_sim', {projectName: currentProject});
            alert(data.message);
        }
    });
}
updateSelection();