import { plot2DMapStatic, plot2DVectorMap, plot2DMapDynamic } from "./map2DManager.js";
import { timeControl, colorbar_container, colorbar_vector_container } from "./map2DManager.js";
import { map } from './mapManager.js';
import { initOptions } from './utils.js';
import { setState, getState } from './constants.js';
import { sendQuery } from './tableManager.js';
import { plotWindow } from "./chartManager.js";

export const layerSelector = () => document.getElementById("layer-selector");
const vectorSelector = () => document.getElementById("vector-selector");
const vectorPlotBtn = () => document.getElementById("plotVectorBtn");
const sigmaSelector = () => document.getElementById("sigma-selector");
export const substanceWindowHis = () => document.getElementById('substance-window-his');
export const substanceWindowMap = () => document.getElementById('substance-window-map');
const substanceWindowContentMap = () => document.getElementById('substance-window-content-map');

let newKey = '', newQuery = '', colorbarTitle = ''; 

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
    await checkVectorComponents();
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
            document.querySelector('.hide-maps').click(); return;
        }
        const vectorName = vectorSelector().value, layerName = layerSelector().value;
        let colorbarTitle = '', colorbarKey = '';
        if (vectorName === '0') {colorbarTitle = 'Velocity (m/s)'; colorbarKey = 'vector';}
        plot2DVectorMap('load', layerName, colorbarTitle, colorbarKey);
    });    
    // Set function for 2D dynamic map plot
    document.querySelectorAll('.map2D_dynamic').forEach(plot => {
        plot.addEventListener('click', () => {
            if (substanceWindowHis().style.display !== 'none') {substanceWindowHis().style.display = 'none';}
            if (substanceWindowMap().style.display !== 'none') {substanceWindowMap().style.display = 'none';}
            const [key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            let titleColorbar = colorbarTitle;
            if (!key.includes('single')) {
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
            substanceWindowHis().style.display = 'none';
            if (plotWindow().style.display !== 'none') plotWindow().style.display = 'none';
            const [query, type] = obj.dataset.info.split('|');
            const data = await sendQuery('process_data', {query: query, key: 'substance_check', projectName: getState().projectName});
            if (data.status === "error") { 
                map.eachLayer((layer) => { if (!(layer instanceof L.TileLayer)) map.removeLayer(layer); });
                alert(data.message); substanceWindowMap().style.display = 'none'; return; 
            }
            substanceWindowContentMap().innerHTML = ''; substanceWindowMap().style.display = 'flex'; 
            // Add content
            substanceWindowContentMap().innerHTML = data.content.map((substance, i) => {
                return `<label for="map-${substance}"><input type="radio" name="waq-substance-map" id="map-${substance}"
                    value="${data.content[i]}|${type}" ${i === 0 ? 'checked' : ''}>${data.message[i]}</label>`;
            }).join('');
            const name = data.content[0]; colorbarTitle = data.message[0];
            if (type === 'single') {
                newKey = `${name}_waq_single_dynamic`; newQuery = `mesh2d_2d_${name}|${sigmaSelector().value}`;
            } else {
                newKey = `${name}_waq_multi_dynamic`; newQuery = `mesh2d_${name}|${sigmaSelector().value}`;
                colorbarTitle = sigmaSelector().value==='-1' ? `${colorbarTitle}\nSigma layer: ${sigmaSelector().selectedOptions[0].text}`
                    : `${colorbarTitle}\n${sigmaSelector().selectedOptions[0].text}`;
            }
            setState({sigma: sigmaSelector()});
            plot2DMapDynamic(true, newQuery, newKey, colorbarTitle, '');
        });
    });
    // Listen to substance selection
    substanceWindowContentMap().addEventListener('change', (e) => {
        if (e.target && e.target.name === "waq-substance-map") {
            if (plotWindow().style.display !== 'none') plotWindow().style.display = 'none';
            const [value, type] = e.target.value.split('|');
            const label = e.target.closest('label');
            let colorbarTitle = label ? label.textContent.trim() : value;
            const sigma = getState().sigma;
            if (type === 'single') {
                newKey = `${value}_waq_single_dynamic`; newQuery = `mesh2d_2d_${value}|${sigma.value}`;
            } else {
                newKey = `${value}_waq_multi_dynamic`; newQuery = `mesh2d_${value}|${sigma.value}`;
                colorbarTitle = sigma.value==='-1'
                    ? `${colorbarTitle}\nLayer: ${sigma.selectedOptions[0].text}`
                    : `${colorbarTitle}\n${sigma.selectedOptions[0].text}`;
            }
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
        if (substanceWindowHis().style.display !== 'none') {substanceWindowHis().style.display = 'none';}
        if (substanceWindowMap().style.display !== 'none') {substanceWindowMap().style.display = 'none';}
    });
}