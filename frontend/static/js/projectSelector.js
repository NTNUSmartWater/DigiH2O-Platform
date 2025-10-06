const projectSelector = () => document.getElementById("project");
const hydOptions = () => document.getElementById("hyd-option");
const waqOptions = () => document.getElementById("waq-option");
const confirmButton = () => document.getElementById("button");
const deleteButton = () => document.getElementById("delete-button");

const defaultOption = `<option value="">--- No selected ---</option>`;
let hydHis = '', hydMap = '', waqHis = '', waqMap = '';

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
    const hydFiles = data.content.hyd, waqFiles = data.content.waq;
    // Assign files to components
    if (hydFiles.length === 0) { hydOptions().innerHTML = defaultOption; 
    } else { hydOptions().innerHTML = hydFiles.map(file => `<option value="${file}">${file}</option>`).join(''); }
    if (waqFiles.length > 0) { waqOptions().innerHTML = waqFiles.map(file => `
        <label for="${file}"><input type="radio" name="waq" value="${file}" id="${file}">${file}</label>`).join(''); 
    } else { waqOptions().innerHTML = `<p style="size: 10px; text-align: center;">No Water Quality files found.</p>`; }
}

async function confirmSelection(){
    if (projectSelector().value === '') { alert('No project selected.'); return; }
    // Check if at least one file is selected
    const waq = document.querySelector('input[name="waq"]:checked') ? 
        document.querySelector('input[name="waq"]:checked').value : '';
    if (hydOptions().value === '' && waq === '') { 
        alert('No file selected.\nSelect a Hydrodynamic and/or Water Quality simulation.'); return; }
    if (hydOptions().value !== '') {
        hydHis = `${hydOptions().value}_his.nc`; hydMap = `${hydOptions().value}_map.nc`; }
    if (waq !== '') { waqHis = `${waq}_his.nc`; waqMap = `${waq}_map.nc`; }
    const params = [hydHis, hydMap, waqHis, waqMap];
    // Send message and data to parent
    window.parent.postMessage({type: 'projectConfirmed',
        project: projectSelector().value, values: params}, '*');
}

function projectOption(){
    projectSelector().addEventListener('change', () => {
        if (projectSelector().value === '') { 
            waqOptions().innerHTML = `<p style="size:10px; text-align:center;">No Water Quality files found.</p>`; 
            hydOptions().innerHTML = defaultOption; return; }
        projectDefinition(projectSelector().value);
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

loadProjectList(); projectOption();