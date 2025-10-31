import { plot2DMapStatic, plot2DVectorMap, plot2DMapDynamic } from "./map2DManager.js";
import { timeControl, colorbar_container } from "./map2DManager.js";
import { colorbar_vector_container } from "./map2DManager.js";
import { map } from './mapManager.js';
import { initOptions } from './utils.js';
import { setState, getState } from './constants.js';
import { sendQuery } from './tableManager.js';

const vectorObjectMain = () => document.getElementById("vector-object-main");
const vectorObjectSubMain = () => document.getElementById("vector-object-submain");
const subVectorContainer = () => document.getElementById("vector-container");
const vectorPlotBtn = () => document.getElementById("plotVectorBtn");
const substanceWindow = () => document.getElementById('substance-window');
const substanceWindowContent = () => document.getElementById('substance-window-content');

let newKey = '', queryKey = '';

async function checkVectorComponents() {
    if (getState().vectorMain !== ''){
        vectorObjectMain().value = getState().vectorMain;
        subVectorContainer().style.display = 'flex';
        if (getState().vectorMain === 'Velocity'){
            await initOptions(vectorObjectSubMain, 'velocity');
            vectorObjectSubMain().value = getState().vectorSelected;
            subVectorContainer().style.display = 'flex';
        } else { setState({vectorSelected: ''}); subVectorContainer().style.display = 'none'; }
    }
}

export async function spatialMapManager() {
    await initOptions(vectorObjectMain, 'vector'); // Initiate objects for vector object
    checkVectorComponents();
    // Add event listener for vector objects
    vectorObjectMain().addEventListener('change', () => {
        setState({vectorMain: vectorObjectMain().value}); checkVectorComponents();
    });
    // Plot vector map
    vectorPlotBtn().addEventListener('click', () => {
        if (!getState().vectorSelected) { alert('Please select a layer.'); return; }
        const query = `${getState().vectorSelected}_velocity`;
        const colorbarTitle = 'Velocity (m/s)', colorbarKey = 'velocity';
        plot2DVectorMap(query, 'velocity', colorbarTitle, colorbarKey);
    });
    // Set function for 2D dynamic map plot
    document.querySelectorAll('.map2D_dynamic').forEach(plot => {
        plot.addEventListener('click', () => {
            const [key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapDynamic(false, '', key, colorbarTitle, colorbarKey);
        });
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
    vectorObjectSubMain().addEventListener('change', () => { setState({vectorSelected: vectorObjectSubMain().value}); });
    // Select static map
    document.querySelectorAll('.map2D_static').forEach(plot => {
        plot.addEventListener('click', () => {
            const [key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapStatic(key, colorbarTitle, colorbarKey);
        });
    });
    // Hide maps
    document.querySelector('.hide-maps').addEventListener('click', () => {
        // Clear map
        map.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) map.removeLayer(layer); });
        timeControl().style.display = 'none'; colorbar_container().style.display = 'none';
        colorbar_vector_container().style.display = 'none'; setState({vectorSelected: ''});
        setState({vectorMain: ''}); checkVectorComponents();
    });
}