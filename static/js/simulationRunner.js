const projectSelector = () => document.getElementById("options");
const runBtn = () => document.getElementById("run-button");
const infoArea = () => document.getElementById("textarea");


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
        const ws = new WebSocket(`ws://${window.location.host}/run_sim/${projectName}`);
        let content = '';
        ws.onmessage = (event) => {
            content += event.data + '\n';
            infoArea().value = content;
            // infoArea().scrollTop = infoArea().scrollHeight;
        };
    })
}
updateSelection();