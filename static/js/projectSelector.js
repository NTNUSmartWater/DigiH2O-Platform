const projectSelector = () => document.getElementById("project");
const generalHisSelector = () => document.getElementById("general-option-his");
const generalMapSelector = () => document.getElementById("general-option-map");
const waterQualityHisSelector = () => document.getElementById("water-quality-his");
const waterQualityMapSelector = () => document.getElementById("water-quality-map");
const confirmButton = () => document.getElementById("button");
const deleteButton = () => document.getElementById("delete-button");

const defaultOption = `<option value="" selected>--- No selected ---</option>`;

async function loadProjectList(){
    const data = await loadList('', 'getProjects', 'output');
    if (data.status === "error") return;
    // Add more options
    const options = data.content.map(value => `<option value="${value}">${value}</option>`).join('');
    projectSelector().innerHTML = defaultOption + options;
}

async function projectDefinition(projectName){
    // Get project files
    const data = await loadList(projectName, 'getFiles');
    if (data.status === "error") {alert(data.message);}
    // Get NC files
    const files = data.content;
    const hisContents = files.filter(file => file.endsWith('_his.nc'));
    const mapContents = files.filter(file => file.endsWith('_map.nc'));
    // Assign files to components
    const hisFiles = hisContents.map(file => `<option value="${file}">${file}</option>`).join('');
    const mapFiles = mapContents.map(file => `<option value="${file}">${file}</option>`).join('');
    generalHisSelector().innerHTML = defaultOption + hisFiles;
    generalMapSelector().innerHTML = defaultOption + mapFiles;
    waterQualityHisSelector().innerHTML = defaultOption + hisFiles;
    waterQualityMapSelector().innerHTML = defaultOption + mapFiles;
}

async function confirmSelection(){
    if (projectSelector().value === '') {
        alert('No project selected.'); return;
    }
    const params = [generalHisSelector().value, generalMapSelector().value,
        waterQualityHisSelector().value, waterQualityMapSelector().value];
    if (params.every(v => v === '')) {
        alert('No file selected.\nAt least one file (history or map) must be selected.');
        return;
    }
    // Send message and data to parent
    window.parent.postMessage({type: 'projectConfirmed',
        project: projectSelector().value, values: params}, '*');
}

function projectOption(){
    loadProjectList();
    projectSelector().addEventListener('change', () => {
        if (projectSelector().value === '') {
            const comboBox = [generalHisSelector, generalMapSelector, 
                waterQualityHisSelector, waterQualityMapSelector];
            comboBox.forEach(comboBox => comboBox().innerHTML = defaultOption);
            return;
        } else { projectDefinition(projectSelector().value); }
    });
    confirmButton().addEventListener('click', () => { confirmSelection(); });
    deleteButton().addEventListener('click', async () => {
        if (projectSelector().value === '') { alert('No project selected.'); return; }
        const confirmDelete = confirm(`Are you sure to delete project '${projectSelector().value}'?\nThis action cannot be undone.`);
        if (!confirmDelete) return;
        // Send delete request
        const response = await fetch('/delete_project', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({projectName: projectSelector().value})});
        const data = await response.json();
        alert(data.message);
        loadProjectList();
    });
}

async function loadList(fileName, key, folder_check = '') {
    const response = await fetch('/select_project', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: fileName, key: key, folder_check:folder_check})});
    const data = await response.json();
    if (data.status === "error") { alert(data.message); return null; }
    return data;
}

projectOption();