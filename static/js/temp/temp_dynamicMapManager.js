import { initOptions, colorbar_vector_container } from './utils.js';
import { startLoading, showLeafletMap, map } from './temp_mapManager.js';
import { plot2DMapDynamic, plot2DVectorMap, layerAbove } from './temp_2DMapManager.js';
import { getVectorMain, setVectorMain, getScalerValue, setScalerValue } from './temp_constants.js';
import { getVectorSelected, setVectorSelected } from './temp_constants.js';

const vectorObjectMain = () => document.getElementById("vector-object-main");
const vectorObjectSubMain = () => document.getElementById("vector-object-submain");
const vectorPlotBtn = () => document.getElementById("plotVectorBtn");
export const scaler_value = () => document.getElementById("scaler-value");

async function checkVectorComponents() {
    const selectedValue = getVectorMain();
    if (selectedValue){
        vectorObjectMain().value = selectedValue;
        if (selectedValue === 'Velocity'){
            await initOptions(vectorObjectSubMain, 'velocity');
            vectorObjectSubMain().value = getVectorSelected();
            vectorObjectSubMain().style.display = 'block';
        } else {
            setVectorSelected('');
            vectorObjectSubMain().style.display = 'none';
        }
    } else {
        colorbar_vector_container().style.display = 'none';
        if (layerAbove()) map.removeLayer(layerAbove());
        setVectorSelected('');
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
            const [filename, key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapDynamic(false, filename, key, colorbarTitle, colorbarKey);
        });
    });
    // Set function for Vector plot
    vectorPlotBtn().addEventListener('click', () => {
        const filename = `${getVectorSelected()}_velocity`, key = 'velocity';
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
        setVectorMain(vectorObjectMain().value);
        checkVectorComponents();
    });
    vectorObjectSubMain().addEventListener('change', () => {
        setVectorSelected(vectorObjectSubMain().value);
    });
    initWaterQualityObjects(); // Initiate objects for water quality object
    // Initialize vector scale
    if (getScalerValue() === null) {setScalerValue(1000);}
    scaler_value().value = getScalerValue();
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