import { loadList } from './utils.js';

const projectSelector = () => document.getElementById("project");
const hydOptions = () => document.getElementById("hyd-option");
const waqOptions = () => document.getElementById("waq-option");
const confirmButton = () => document.getElementById("button");

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
    if (waqFiles.length > 0) { 
        waqOptions().innerHTML = waqFiles.map(file => `
            <div style="display:flex; justify-content:space-between; margin:2px 0 2px 0;">
                <label for="${file}"><input type="radio" name="waq" value="${file}" id="${file}">${file}</label>
            </div>
        `).join('');
    } else { waqOptions().innerHTML = `<p style="font-size: 15px; text-align: center;">No Water Quality files found</p>`; }
}

async function confirmSelection(){
    if (projectSelector().value === '') { alert('No project selected.'); return; }
    // Check if at least one file is selected
    const waq = document.querySelector('input[name="waq"]:checked') ? 
        document.querySelector('input[name="waq"]:checked').value : '';
    if (hydOptions().value === '' && waq === '') { 
        alert('No file selected.\nSelect a Hydrodynamic and/or Water Quality simulation.'); return; }
    if (hydOptions().value !== '') {
        hydHis = `${hydOptions().value}_his.zarr`; hydMap = `${hydOptions().value}_map.zarr`; }
    if (waq !== '') { waqHis = `${waq}_his.zarr`; waqMap = `${waq}_map.zarr`; }
    const params = [hydHis, hydMap, waqHis, waqMap];
    // Send message and data to parent
    window.parent.postMessage({type: 'projectConfirmed', project: projectSelector().value, values: params}, '*');
}

function projectOption(){
    projectSelector().addEventListener('change', () => {
        if (projectSelector().value === '') { 
            waqOptions().innerHTML = `<p style="font-size:10px; text-align:center;">No Water Quality files found</p>`; 
            hydOptions().innerHTML = defaultOption; return; }
        projectDefinition(projectSelector().value);
    });
    confirmButton().addEventListener('click', () => { confirmSelection(); });
}

loadProjectList(); projectOption();