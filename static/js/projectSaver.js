import { sendQuery, getDataFromTable } from "./tableManager.js";

export function toUTC(dateStr){
    const [datePart, timePart] = dateStr.split(' ');
    const [year, month, day] = datePart.split('-').map(Number);
    let hours = 0, minutes = 0, seconds = 0;
    if (timePart) [hours, minutes, seconds] = timePart.split(':').map(Number);
    return Date.UTC(year, month - 1, day, hours, minutes, seconds);
}

export function timeStepCalculator(daysString, timeString){
    return parseInt(daysString)*86400 + parseInt(timeString.split(':')[0])*3600 +
    parseInt(timeString.split(':')[1])*60 + parseInt(timeString.split(':')[2]);
}

export async function saveProject(elements) {
    const { projectName, latitude, nLayers, gridPath, startDate, stopDate,
        userTimeSec, nodalTimeSec, obsPointTable, crossSectionName, crossSectionTable, salinity, 
        temperature, initWaterLevel, initSalinity, initTemperature , outputHis, hisInterval, hisStart, 
        hisStop, outputMap, mapInterval, mapStart, mapStop, outputWQ, wqInterval, wqStart, wqStop, 
        outputRestart, rtsInterval, rtsStart, rtsStop, sttInterval, timingInterval } = elements;
    sendQuery('save_obs', {projectName: projectName().value.trim()});
    let data = new Map();
    // Get time
    const formatted = new Date().toISOString().slice(0,19).replace('T',' ');
    data.set('gen_date', formatted);
    // Get project name
    const name = projectName().value.trim();
    if (name === '') { alert('Please check project name.'); return; }
    data.set('project_name', name);
    // Check latitude
    const lat = latitude().value;
    if (!lat || lat === '') { alert('Please check latitude.'); return; }
    data.set('ang_lat', latitude().value);
    // Check number of layers
    if (!nLayers || nLayers === '') { alert('Please check number of layers.'); return; }
    data.set('n_layers', nLayers().value);
    // Check grid
    const fileInput = gridPath();
    if (!fileInput || fileInput.files.length === 0) { alert('Please select a grid file!'); return; }
    data.set('netNC_file', 'FlowFM_net.nc');
    // Get start date
    const start_ = startDate().value, stop_ = stopDate().value;
    if (!startDate() || start_ === '' || !stopDate() || stop_ === '') {
        alert('Please select a start/stop date for the simulation!'); return; }
    // Save start/stop date
    const startSimulation = toUTC(start_);            
    const stopSimulation = toUTC(stop_);   
    // Check if start/stop is after reference date
    if(startSimulation<0 || stopSimulation<0 || stopSimulation<=startSimulation){
        alert('Start/Stop date must be after reference date!'); return; }
    // Convert to seconds
    const startSimulationSec = Math.floor(startSimulation/1000.0);
    const stopSimulationSec = Math.floor(stopSimulation/1000.0);
    // Add to data
    data.set('start_time_s', startSimulationSec);
    data.set('end_time_s', stopSimulationSec);
    // Get user time step
    data.set('user_time_s', userTimeSec);
    data.set('nodal_time_s', nodalTimeSec);
    // Get obs points
    const obsPoints = getDataFromTable(obsPointTable(), true)
    if (obsPoints.rows.length > 0) { 
        // Write obs points
        const obsFileName = 'FlowFM_obs.xyn';
        const content = {projectName: name, fileName: obsFileName, data: obsPoints.rows, key: 'obs'};
        const output = await sendQuery('save_obs', content);
        if (output.error) { alert(output.error); return; }
        // Add to data
        data.set('obs_file', obsFileName);
    } else data.set('obs_file', '');
    // Get cross sections
    const crossSections = getDataFromTable(crossSectionTable(), true);
    const crossName = crossSectionName().value.trim();
    if (crossSections.rows.length > 0 && crossName !== '') {
        // Write cross sections
        const crossFileName = `${crossName}_crs.pli`;
        const content = {projectName: name, fileName: crossFileName, data: crossSections.rows, key: 'crs'};
        const output = await sendQuery('save_obs', content);
        if (output.error) { alert(output.error); return; }
        // Add to data
        data.set('crs_file', crossFileName);
    } else data.set('crs_file', '');
    // Get boundary conditions
    const checkBoundary = await sendQuery('check_condition', {projectName: name, forceName: 'FlowFM_bnd.ext'});
    if (checkBoundary.status === 'ok') data.set('external_forcing_new', 'FlowFM_bnd.ext'); 
    else data.set('external_forcing_new', '');
    // Get other parameters
    const isSalinity = salinity().checked ? 1 : 0;
    data.set('processes_salinity', isSalinity);
    data.set('processes_temperature', temperature().value);
    data.set('initial_waterlevel', initWaterLevel().value);
    data.set('initial_salinity', initSalinity().value);
    data.set('initial_temperature', initTemperature().value);
    // Get hydrological parameters
    const checkHydro = await sendQuery('check_condition', {projectName: name, forceName: 'FlowFM.ext'});
    if (checkHydro.status === 'ok') data.set('external_forcing', 'FlowFM.ext'); 
    else data.set('external_forcing', '');
    // Get output parameters
    data.set('his_interval', '0'); data.set('his_start', ''); data.set('his_end', '');
    if (outputHis().checked) {
        data.set('his_interval', hisInterval);
        const start = hisStart().value, stop = hisStop().value;
        if (start !== '') {
            const hisStartSec = Math.floor(toUTC(start)/1000);
            data.set('his_start', hisStartSec);
        }
        if (stop !== '') {
            const hisStopSec = Math.floor(toUTC(stop)/1000);
            data.set('his_end', hisStopSec);
        }
    }
    data.set('map_interval', '0'); data.set('map_start', ''); data.set('map_end', '');
    if (outputMap().checked) {
        data.set('map_interval', mapInterval);
        const start = mapStart().value, stop = mapStop().value;
        if (start !== '') {
            const mapStartSec = Math.floor(toUTC(start)/1000);
            data.set('map_start', mapStartSec);
        }
        if (stop !== '') {
            const mapStopSec = Math.floor(toUTC(stop)/1000);
            data.set('map_end', mapStopSec);
        }
    }
    data.set('wq_interval', '0'); data.set('wq_start', ''); data.set('wq_end', ''); data.set('wq_output_dir', '');
    if (outputWQ().checked) {
        data.set('wq_interval', wqInterval); data.set('wq_output_dir', 'DFM_DELWAQ');
        const start = wqStart().value, stop = wqStop().value;
        if (start !== '') {
            const wqStartSec = Math.floor(toUTC(start)/1000);
            data.set('wq_start', wqStartSec);
        }
        if (stop !== '') {
            const wqStopSec = Math.floor(toUTC(stop)/1000);
            data.set('wq_end', wqStopSec);
        }
    }
    data.set('rst_interval', '0'); data.set('rst_start', ''); data.set('rst_end', '');
    if (outputRestart().checked) {
        data.set('rst_interval', rtsInterval);
        const start = rtsStart().value, stop = rtsStop().value;
        if (start !== '') {
            const rstStartSec = Math.floor(toUTC(start)/1000);
            data.set('rst_start', rstStartSec);
        }
        if (stop !== '') {
            const rstStopSec = Math.floor(toUTC(stop)/1000);
            data.set('rst_end', rstStopSec);
        }
    }
    data.set('stats_interval', sttInterval);
    data.set('timings_interval', timingInterval);
    // Generate MDU file
    // Convert to object
    const dataObj = Object.fromEntries(data);
    const content = await sendQuery('generate_mdu', {params: dataObj});
    alert(content.message);
}