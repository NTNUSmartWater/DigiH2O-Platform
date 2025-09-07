
// async function uploadData(file, projectName, gridName){
//     const formData = new FormData();
//     formData.append('file', file);
//     formData.append('projectName', projectName);
//     formData.append('gridName', gridName);
//     const response = await fetch('/upload_data', {
//     method: 'POST', body: formData});
//     const data = await response.json();
//     if (data.status === "error") alert(data.message);
// }

async function mduCreator(content){
    const response = await fetch('/generate_mdu', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content: Array.from(content)})});
    const data = await response.json();
    if (data.status === "error") alert(data.message);
}



export async function saveProject() {
    // Check conditions before saving
    const name = projectName().value.trim();
    if (name === '') { alert('Please check project name.'); return; }
    const fileInput = gridPath();
    if (!fileInput || fileInput.files.length === 0) { alert('Please select a grid file!'); return; }
    // Get reference date
    const refDate = referenceDate().value;
    if (!refDate || refDate === '') { alert('Please select a reference date for the simulation!'); return; }
    // Get start date
    const start_ = startDate().value, stop_ = stopDate().value;
    if (!start_ || start_ === '' || !stop_ || stop_ === '') { alert('Please select a start/stop date for the simulation!'); return; }
    // Save start/stop date
    const refSimulation = new Date(`${refDate.split('T')[0]}T00:00:00`);
    const startSimulation = new Date(start_) - refSimulation;            
    const stopSimulation = new Date(stop_) - refSimulation;
    // Check if start/stop is after reference date
    if(startSimulation<0 || stopSimulation<0 || stopSimulation<=startSimulation){
        alert('Start/Stop date must be after reference date!'); return;
    }
    const obsPoints = getDataFromTable(obsPointTable(), true)
    if (obsPoints.rows.length === 0) alert('No data to plot. Please check the table.'); return;





    // // Start saving project
    // let data = new Map();
    // const saveProject = saveProjectBtn();
    // saveProject.textContent = 'Preparing data to save...';
    // // Send message and data to parent
    // window.parent.postMessage({type: 'projectPreparation', name: name}, '*');
    // data.set('project_name', name);
    // saveProject.textContent = 'Saving Latitude...';
    // data.set('ang_lat', latitude().value);
    // saveProject.textContent = 'Saving number of layers...';
    // data.set('n_layers', nLayers().value);
    // saveProject.textContent = 'Uploading grid...';
    // // Copy file to server
    // const file = fileInput.files[0];
    // const gridName = 'FlowFM_net.nc';
    // await uploadData(file, name, gridName);
    // data.set('netNC_file', gridName);
    // // Save reference date
    // const refDateFormatted = refDate.split('T')[0].replace(/-/g,"");
    // data.set('ref_date', refDateFormatted);
    // // Convert to seconds
    // const startSimulationSec = Math.floor(startSimulation/1000);
    // const stopSimulationSec = Math.floor(stopSimulation/1000);
    // // Add to data
    // data.set('start_time_s', startSimulationSec);
    // data.set('end_time_s', stopSimulationSec);
    // // Get user time step
    // const userTime = userTimestepTime().value;
    // const userTimestep = parseInt(userTimestepDate().value)*86400 +
    //                 parseInt(userTime.split(':')[0])*3600 +
    //                 parseInt(userTime.split(':')[1])*60 +
    //                 parseInt(userTime.split(':')[2]);
    // const nodalTime = nodalTimestepTime().value;
    // const nodalTimestep = parseInt(nodalTimestepDate().value)*86400 +
    //                 parseInt(nodalTime.split(':')[0])*3600 +
    //                 parseInt(nodalTime.split(':')[1])*60 +
    //                 parseInt(nodalTime.split(':')[2]);
    // data.set('user_time_s', userTimestep);
    // data.set('nodal_time_s', nodalTimestep);
    // // Get other parameters
    // const salinity = document.getElementById('use-salinity').checked ? 1 : 0;
    // data.set('processes_salinity', salinity);
    // const temperature = document.getElementById('option-temperature').value;
    // data.set('processes_temperature', temperature);
    // const initWaterLevel = document.getElementById('initial-water-level').value;
    // data.set('initial_waterlevel', initWaterLevel);
    // const initSalinity = document.getElementById('initial-salinity').value;
    // data.set('initial_salinity', initSalinity);
    // const initTemperature = document.getElementById('initial-temperature').value;
    // data.set('initial_temperature', initTemperature);
    // // Get output parameters
    // // Get his output
    // const outputHis = document.getElementById('write-his-file').checked ? 1 : 0;
    // if (outputHis === 1) {
    //     const hisInterval = parseInt(hisIntervalDate().value)*86400 +
    //                     parseInt(hisIntervalTime().value.split(':')[0])*3600 +
    //                     parseInt(hisIntervalTime().value.split(':')[1])*60 +
    //                     parseInt(hisIntervalTime().value.split(':')[2]);
    //     data.set('his_interval', hisInterval);
    //     const hisStart = document.getElementById('his-output-start').value;
    //     if (!hisStart || hisStart === '') { data.set('his_start', ''); }
    //     else {
    //         const hisStartFormatted = new Date(hisStart) - refSimulation;
    //         const hisStartSec = Math.floor(hisStartFormatted/1000);
    //         data.set('his_start', hisStartSec);
    //     }
    //     const hisEnd = document.getElementById('his-output-stop').value;
    //     if (!hisEnd || hisEnd === '') { data.set('his_end', ''); }
    //     else {
    //         const hisEndFormatted = new Date(hisEnd) - refSimulation;
    //         const hisEndSec = Math.floor(hisEndFormatted/1000);
    //         data.set('his_end', hisEndSec);
    //     }
    // } else {
    //     data.set('his_interval', '');
    //     data.set('his_start', '');
    //     data.set('his_end', '');
    // }
    // // Get map output
    // const outputMap = document.getElementById('write-map-file').checked ? 1 : 0;
    // if (outputMap === 1) {
    //     const mapInterval = parseInt(mapIntervalDate().value)*86400 +
    //                     parseInt(mapIntervalTime().value.split(':')[0])*3600 +
    //                     parseInt(mapIntervalTime().value.split(':')[1])*60 +
    //                     parseInt(mapIntervalTime().value.split(':')[2]);
    //     data.set('map_interval', mapInterval);
    //     const mapStart = document.getElementById('map-output-start').value;
    //     if (!mapStart || mapStart === '') { data.set('map_start', ''); }
    //     else {
    //         const mapStartFormatted = new Date(mapStart) - refSimulation;
    //         const mapStartSec = Math.floor(mapStartFormatted/1000);
    //         data.set('map_start', mapStartSec);
    //     }
    //     const mapEnd = document.getElementById('map-output-stop').value;
    //     if (!mapEnd || mapEnd === '') { data.set('map_end', ''); }
    //     else {
    //         const mapEndFormatted = new Date(mapEnd) - refSimulation;
    //         const mapEndSec = Math.floor(mapEndFormatted/1000);
    //         data.set('map_end', mapEndSec);
    //     }

    // } else {
    //     data.set('map_interval', '');
    //     data.set('map_start', '');
    //     data.set('map_end', '');
    // }
    // // Get water quality output
    // const outputWQ = document.getElementById('write-water-quality-file').checked ? 1 : 0;
    // if (outputWQ === 1) {
    //     const wqInterval = parseInt(wqIntervalDate().value)*86400 +
    //                     parseInt(wqIntervalTime().value.split(':')[0])*3600 +
    //                     parseInt(wqIntervalTime().value.split(':')[1])*60 +
    //                     parseInt(wqIntervalTime().value.split(':')[2]);
    //     data.set('wq_interval', wqInterval);
    //     const wqStart = document.getElementById('water-quality-ouput-start').value;
    //     if (!wqStart || wqStart === '') { data.set('wq_start', ''); }
    //     else {
    //         const wqStartFormatted = new Date(wqStart) - refSimulation;
    //         const wqStartSec = Math.floor(wqStartFormatted/1000);
    //         data.set('wq_start', wqStartSec);
    //     }
    //     const wqEnd = document.getElementById('water-quality-ouput-end').value;
    //     if (!wqEnd || wqEnd === '') { data.set('wq_end', ''); }
    //     else {
    //         const wqEndFormatted = new Date(wqEnd) - refSimulation;
    //         const wqEndSec = Math.floor(wqEndFormatted/1000);
    //         data.set('wq_end', wqEndSec);
    //     }
    // } else {
    //     data.set('wq_interval', '');
    //     data.set('wq_start', '');
    //     data.set('wq_end', '');
    // }
    // // Get restart output
    // const outputRst = document.getElementById('write-restart-file').checked ? 1 : 0;
    // if (outputRst === 1) {
    //     const rstInterval = parseInt(rstIntervalDate().value)*86400 +
    //                     parseInt(rstIntervalTime().value.split(':')[0])*3600 +
    //                     parseInt(rstIntervalTime().value.split(':')[1])*60 +
    //                     parseInt(rstIntervalTime().value.split(':')[2]);
    //     data.set('rst_interval', rstInterval);
    //     const rstStart = document.getElementById('restart-output-start').value;
    //     if (!rstStart || rstStart === '') { data.set('rst_start', ''); }
    //     else {
    //         const rstStartFormatted = new Date(rstStart) - refSimulation;
    //         const rstStartSec = Math.floor(rstStartFormatted/1000);
    //         data.set('rst_start', rstStartSec);
    //     }
    //     const rstEnd = document.getElementById('restart-output-end').value;
    //     if (!rstEnd || rstEnd === '') { data.set('rst_end', ''); }
    //     else {
    //         const rstEndFormatted = new Date(rstEnd) - refSimulation;
    //         const rstEndSec = Math.floor(rstEndFormatted/1000);
    //         data.set('rst_end', rstEndSec);
    //     }
    // } else {
    //     data.set('rst_interval', '');
    //     data.set('rst_start', '');
    //     data.set('rst_end', '');
    // }
    // // Get other options
    // const statisticInterval = parseInt(statisticDate().value)*86400 +
    //                 parseInt(statisticTime().value.split(':')[0])*3600 +
    //                 parseInt(statisticTime().value.split(':')[1])*60 +
    //                 parseInt(statisticTime().value.split(':')[2]);
    // data.set('stats_interval', statisticInterval);
    // const timingInterval = parseInt(timingDate().value)*86400 +
    //                 parseInt(timingTime().value.split(':')[0])*3600 +
    //                 parseInt(timingTime().value.split(':')[1])*60 +
    //                 parseInt(timingTime().value.split(':')[2]);
    // data.set('timings_interval', timingInterval);

    // Work with observation points



    
    // Create boundary conditions _bnd.ext


    














    // // Get time
    // const formatted = new Date().toISOString().slice(0,19).replace('T',' ');
    // data.set('gen_date', formatted);
    // // Generate MDU file
    // saveProject.textContent = 'Generating MDU file...';
    // await mduCreator(data);
    // Return name of button
    // saveProject.textContent = 'Save Project - Success';
    // alert('Project saved successfully!');
}