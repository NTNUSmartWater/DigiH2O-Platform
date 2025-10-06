import { plot2DMapDynamic, plot2DVectorMap, layerAbove } from './map2DManager.js';
import { initOptions, colorbar_vector_container } from './utils.js';
import { setState, getState } from './constants.js';
import { map } from './mapManager.js';
import { sendQuery } from './tableManager.js';

export const scaler_value = () => document.getElementById("scaler-value");
const vectorObjectMain = () => document.getElementById("vector-object-main");
const vectorObjectSubMain = () => document.getElementById("vector-object-submain");
const vectorPlotBtn = () => document.getElementById("plotVectorBtn");
const substanceWindow = () => document.getElementById('substance-window');
const substanceWindowContent = () => document.getElementById('substance-window-content');
const substanceWindowCloseBtn = () => document.getElementById('substance-window-close');

let newKey = '', queryKey = '';

async function checkVectorComponents() {
    if (getState().vectorMain){
        vectorObjectMain().value = getState().vectorMain;
        if (getState().vectorMain === 'Velocity'){
            await initOptions(vectorObjectSubMain, 'velocity');
            vectorObjectSubMain().value = getState().vectorSelected;
            vectorObjectSubMain().style.display = 'block';
        } else {
            setState({vectorSelected: ''});
            vectorObjectSubMain().style.display = 'none';
        }
    } else {
        colorbar_vector_container().style.display = 'none';
        if (layerAbove) map.removeLayer(layerAbove);
        setState({vectorSelected: ''});
        vectorObjectSubMain().style.display = 'none';
        return;
    }
}

export async function dynamicMapManager() {
    await initOptions(vectorObjectMain, 'vector'); // Initiate objects for vector object  
    checkVectorComponents();
    // Set function for 2D plot
    document.querySelectorAll('.map2D_dynamic').forEach(plot => {
        plot.addEventListener('click', () => {
            const [key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapDynamic(false, '', key, colorbarTitle, colorbarKey);
        });
    });
    // Set function for Vector plot
    vectorPlotBtn().addEventListener('click', () => {
        const filename = `${getState().vectorSelected}_velocity`, key = 'velocity';
        const colorbarTitle = 'Velocity (m/s)', colorbarKey = 'velocity';
        plot2DVectorMap(filename, key, colorbarTitle, colorbarKey);
    });
    // Set function for water quality
    document.querySelectorAll('.waq-function').forEach(obj => {
        obj.addEventListener('click', async() => {
            const [query, type] = obj.dataset.info.split('|');
            const data = await sendQuery('process_data', {query: query, key: 'substance_check'});
            if (data.status === "error") { alert(data.message); substanceWindow().style.display = 'none'; return; }
            substanceWindowContent().innerHTML = '';
            // Add content
            substanceWindowContent().innerHTML = data.content.map((substance, i) => {
                return `<label for="${substance[0]}"><input type="radio" name="waq-substance" id="${substance[0]}"
                    value="${substance[0]}|${type}" ${i === 0 ? 'checked' : ''}>${substance[1]}</label>`;
            }).join('');
            substanceWindow().style.display = 'flex';
            const name = data.content[0][0];
            if (type === 'single') {newKey = `${name}_waq_dynamic`; queryKey = `mesh2d_${name}`;}
            else {newKey = `${name}_waq_multi_dynamic`; queryKey = `mesh2d_2d_${name}`;}
            const colorbarTitle = data.content[0][1];
            plot2DMapDynamic(true, queryKey, newKey, colorbarTitle, '');
        });
    });
    // Listen to substance selection
    substanceWindowContent().addEventListener('change', (e) => {
        if (e.target && e.target.name === "waq-substance") {
            const [value, type] = e.target.value.split('|');
            if (type === 'single') {newKey = `${value}_waq_dynamic`; queryKey = `mesh2d_${value}`;}
            else {newKey = `${value}_waq_multi_dynamic`; queryKey = `mesh2d_2d_${value}`;}
            const label = e.target.closest('label');
            const colorbarTitle = label ? label.textContent.trim() : value;
            plot2DMapDynamic(true, queryKey, newKey, colorbarTitle, '');
        }
    });
    // Close windows
    substanceWindowCloseBtn().addEventListener('click', () => { 
        substanceWindow().style.display = 'none';
    });
    // Add event listener for vector objects
    vectorObjectMain().addEventListener('change', () => {
        setState({vectorMain: vectorObjectMain().value});
        checkVectorComponents();
    });
    vectorObjectSubMain().addEventListener('change', () => {
        setState({vectorSelected: vectorObjectSubMain().value});
    });
    // Initialize vector scale
    if (getState().scalerValue === null) setState({scalerValue: 1000});
    scaler_value().value = getState().scalerValue;
}