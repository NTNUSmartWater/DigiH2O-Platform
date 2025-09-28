import { initOptions, colorbar_vector_container } from './utils.js';
import { startLoading, showLeafletMap, map } from './mapManager.js';
import { plot2DMapDynamic, plot2DVectorMap, layerAbove, timeControl } from './map2DManager.js';
import { setState, getState } from './constants.js';

const vectorObjectMain = () => document.getElementById("vector-object-main");
const vectorObjectSubMain = () => document.getElementById("vector-object-submain");
const vectorPlotBtn = () => document.getElementById("plotVectorBtn");
export const scaler_value = () => document.getElementById("scaler-value");

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
        timeControl().style.display = 'none';
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
            plot2DMapDynamic(false, key, colorbarTitle, colorbarKey);
        });
    });
    // Set function for Vector plot
    vectorPlotBtn().addEventListener('click', () => {
        const filename = `${getState().vectorSelected}_velocity`, key = 'velocity';
        const colorbarTitle = 'Velocity (m/s)', colorbarKey = 'velocity';
        plot2DVectorMap(filename, key, colorbarTitle, colorbarKey);
    });

    // Set function for water quality
    document.querySelectorAll('.wq-function').forEach(obj => {
        obj.addEventListener('change', () => {
            const [filename, key, colorbarTitle, colorbarKey] = obj.dataset.info.split('|');
            let newKey = `${key}_dynamic`;
            const selectedIndex = obj.selectedIndex;
            if (selectedIndex === 0) return;
            if (selectedIndex === 2) {newKey = `${key}_multi_dynamic`;}
            plot2DMapDynamic(true, filename, newKey, colorbarTitle, colorbarKey);
        });
    });
    // Add event listener for vector objects
    vectorObjectMain().addEventListener('change', () => {
        setState({vectorMain: vectorObjectMain().value});
        checkVectorComponents();
    });
    vectorObjectSubMain().addEventListener('change', () => {
        setState({vectorSelected: vectorObjectSubMain().value});
    });
    initWaterQualityObjects(); // Initiate objects for water quality object
    // Initialize vector scale
    if (getState().scalerValue === null) setState({scalerValue: 1000});
    scaler_value().value = getState().scalerValue;
}

function initWaterQualityObjects() {
    startLoading();
    document.querySelectorAll('.wq-function').forEach(obj => {
        obj.innerHTML = '';
        // Add hint to the velocity object
        const hint = document.createElement('option');
        hint.value = ''; hint.selected = true;
        hint.textContent = '- No Selection -'; 
        obj.add(hint);
        const items = ['Average', 'Each Layer']
        // Add options
        items.forEach(item => {
            const option = document.createElement('option');
            option.value = item; option.text = item;
            obj.add(option);
        });
    });
    showLeafletMap();
}