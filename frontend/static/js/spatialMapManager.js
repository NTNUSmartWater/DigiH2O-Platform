import { plot2DMapStatic, plot2DVectorMap, plot2DMapDynamic } from "./map2DManager.js";
import { timeControl, colorbar_container } from "./map2DManager.js";
import { colorbar_vector_container } from "./map2DManager.js";
import { map } from './mapManager.js';
import { initOptions } from './utils.js';
import { setState, getState } from './constants.js';
import { sendQuery } from './tableManager.js';

export const layerSelector = () => document.getElementById("layer-selector");
const vectorSelector = () => document.getElementById("vector-selector");
const vectorPlotBtn = () => document.getElementById("plotVectorBtn");
const sigmaSelector = () => document.getElementById("sigma-selector");
const substanceWindow = () => document.getElementById('substance-window');
const substanceWindowContent = () => document.getElementById('substance-window-content');

let newKey = '', newQuery = '', titleColorbar = ''; 

async function checkVectorComponents() {
    // Initiate objects for vector object
    if (getState().layerSelected !== '') layerSelector().value = getState().layerSelected; 
    if (getState().vectorSelected !== '') vectorSelector().value = getState().vectorSelected; 
    if (getState().sigmaSelected !== '') sigmaSelector().value = getState().sigmaSelected; 
}

function reAssign(target, key){
    target().addEventListener('change', () => { 
        setState({[key]: target().value});
        document.querySelector('.hide-maps').click();
    });
}

export async function spatialMapManager() {
    await initOptions(layerSelector, 'layer_hyd');
    await initOptions(vectorSelector, 'vector');
    await initOptions(sigmaSelector, 'sigma_waq');
    checkVectorComponents();
    setState({layerSelected: layerSelector().value});
    setState({vectorSelected: vectorSelector().value});
    setState({sigmaSelected: sigmaSelector().value});
    // Add event listener for objects
    reAssign(layerSelector, 'layerSelected');
    reAssign(vectorSelector, 'vectorSelected');
    reAssign(sigmaSelector, 'sigmaSelected');
    // Plot vector map
    vectorPlotBtn().addEventListener('click', () => {
        if (vectorSelector().value === '') { 
            alert('Please select a vector.'); 
            document.querySelector('.hide-maps').click(); return; }
        const vectorName = vectorSelector().value, layerName = layerSelector().value;
        let colorbarTitle = '', colorbarKey = '';
        if (vectorName === '0') {colorbarTitle = 'Velocity (m/s)'; colorbarKey = 'vector';}
        plot2DVectorMap(`${layerName}|load`, 'vector', colorbarTitle, colorbarKey);
    });    
    // Set function for 2D dynamic map plot
    document.querySelectorAll('.map2D_dynamic').forEach(plot => {
        plot.addEventListener('click', () => {
            if (substanceWindow().style.display === 'flex') {substanceWindow().style.display = 'none';}
            const [key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            if (key.includes('single')) {titleColorbar = colorbarTitle;}
            else {
                titleColorbar = layerSelector().value==='-1' ? `${colorbarTitle}\nLayer: ${layerSelector().selectedOptions[0].text}`
                        : `${colorbarTitle}\n${layerSelector().selectedOptions[0].text}`;
            }
            const query = `|${layerSelector().value}`;
            plot2DMapDynamic(false, query, key, titleColorbar, colorbarKey);
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
            substanceWindow().style.display = 'flex'; const name = data.content[0][0];
            if (type === 'single') {
                newKey = `${name}_waq_single_dynamic`; newQuery = `mesh2d_2d_${name}|${sigmaSelector().value}`;
            } else {
                newKey = `${name}_waq_multi_dynamic`; newQuery = `mesh2d_${name}|${sigmaSelector().value}`;
            }
            const title = data.content[0][1];
            const colorbarTitle = sigmaSelector().value==='-1' ? `${title}\nLayer: ${sigmaSelector().selectedOptions[0].text}`
                        : `${title}\n${sigmaSelector().selectedOptions[0].text}`;
            plot2DMapDynamic(true, newQuery, newKey, colorbarTitle, '');
        });
    });

    // Listen to substance selection
    substanceWindowContent().addEventListener('change', (e) => {
        if (e.target && e.target.name === "waq-substance") {
            const [value, type] = e.target.value.split('|');
            if (type === 'single') {
                newKey = `${value}_waq_single_dynamic`; newQuery = `mesh2d_2d_${value}|${sigmaSelector().value}`;
            } else {
                newKey = `${value}_waq_multi_dynamic`; newQuery = `mesh2d_${value}|${sigmaSelector().value}`;
            }
            const label = e.target.closest('label');
            const title = label ? label.textContent.trim() : value;
            const colorbarTitle = sigmaSelector().value==='-1' ? `${title}\nLayer: ${sigmaSelector().selectedOptions[0].text}`
                        : `${title}\n${sigmaSelector().selectedOptions[0].text}`;
            plot2DMapDynamic(true, newQuery, newKey, colorbarTitle, '');
        }
    });
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
        map.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) map.removeLayer(layer); layer = null; });
        timeControl().style.display = 'none'; colorbar_container().style.display = 'none';
        colorbar_vector_container().style.display = 'none';
        document.getElementById('substance-window').style.display = 'none';
    });
}