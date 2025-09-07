import { startLoading, showLeafletMap } from "./mapManager.js";
import { getMapLayer, n_decimals, getFeatureMap, getScalerValue} from "./constants.js";
import { getLastFeatureColors, setLastFeatureColors } from "./constants.js";
import { superscriptMap } from "./constants.js";


export const colorbar_container = () => document.getElementById("custom-colorbar");
export const colorbar_vector_container = () => document.getElementById("custom-colorbar-vector");
export let colorbar_title = () => document.getElementById("colorbar-title");

let colorbar_color = () => document.getElementById("colorbar-gradient");
let colorbar_label = () => document.getElementById("colorbar-labels");
let colorbar_vector_title = () => document.getElementById("colorbar-title-vector");
let colorbar_vector_color = () => document.getElementById("colorbar-gradient-vector");
let colorbar_vector_label = () => document.getElementById("colorbar-labels-vector");
let colorbar_vector_scaler = () => document.getElementById("custom-colorbar-scaler");


function toSuperscript(num) {
    return String(num).split('').map(ch => superscriptMap[ch] || ch).join('');
}

function valueFormatter(value, minDiff) {
    const absVal = Math.abs(value);
    let decimalPlaces = 2;
    if (minDiff >= 0.01) decimalPlaces = 2;
    else if (minDiff >= 0.001) decimalPlaces = 3;
    else if (minDiff >= 0.0001) decimalPlaces = 4;
    else decimalPlaces = 6;
    if (absVal < 0.01) {
        const expStr = value.toExponential(n_decimals);
        const [mantissa, exponent] = expStr.split('e');
        const expNum = parseInt(exponent, 10);
        return `${mantissa}×10${toSuperscript(expNum)}`;
    } else {
        return value.toFixed(decimalPlaces);
    }
}

export function interpolateJet(t) {
    const jetColors = [
        [0.0, [0, 0, 128]], [0.35, [0, 255, 255]],
        [0.5, [0, 255, 0]], [0.75, [255, 255, 0]], [1.0, [255, 0, 0]]
    ];
    for (let i = 0; i < jetColors.length - 1; i++) {
        const [t1, c1] = jetColors[i];
        const [t2, c2] = jetColors[i + 1];
        if (t >= t1 && t <= t2) {
            const f = (t - t1) / (t2 - t1);
            const r = Math.round(c1[0] + (c2[0] - c1[0]) * f);
            const g = Math.round(c1[1] + (c2[1] - c1[1]) * f);
            const b = Math.round(c1[2] + (c2[2] - c1[2]) * f);
            return `rgb(${r},${g},${b})`;
        }
    }
    return `rgb(255,0,0)`;
}

// Interpolate value using inverse distance weighting
export function interpolateValue(location, centroids, power = 5, maxDistance = Infinity) {
    const weights = [], values = [];
    for (const c of centroids){
        const d = turf.distance(
            turf.point([location.lng, location.lat]),
            turf.point([c.lng, c.lat]), {unit: 'meters'}
        );
        if (d > maxDistance || d === 0) continue;
        const w = 1 / Math.pow(d, power);
        weights.push(w); values.push(c.value * w);
    }
    if (weights.length === 0) return null;
    const sumWeughts = weights.reduce((a, b) => a + b, 0);
    const sumValues = values.reduce((a, b) => a + b, 0);
    return (sumValues / sumWeughts);
}

// Convert value to color
export function getColorFromValue(value, vmin, vmax, colorbarKey, swap) {
    if (typeof value !== 'number' || isNaN(value)) {
        return { r: 150, g: 150, b: 150, a: 0 };
    }
    if (vmin === vmax) return { r: 0, g: 0, b: 100, a: 1 };
    // Minimum difference
    const minDiff = 1e-2, epsilon = 1e-6;
    if (vmax - vmin < minDiff) vmax = vmin + minDiff;
    let t;
    if (vmin + epsilon <=0 || vmax + epsilon <=0) { // avoid zero division error for vmin or vmax = 0
        t = (value - vmin) / (vmax - vmin);
    } else {
        t = (Math.log(value + epsilon) - Math.log(vmin + epsilon)) / (Math.log(vmax + epsilon) - Math.log(vmin + epsilon));
    }
    t = Math.max(0, Math.min(1, t));
    if (swap) t = 1 - t;
    let colors;
    if (colorbarKey === "depth") { // used for depth
        colors = [
            { r: 0,   g: 51,  b: 102 }, // dark blue
            { r: 0,   g: 119, b: 190 }, // light blue
            { r: 160, g: 216, b: 239 }  // very light blue
        ];
    }else if (colorbarKey === "velocity") { // used for velocity
        colors = [
            { r: 255, g: 255, b: 255 },  // White
            { r: 255, g: 255, b: 85  },  // Yellow
            { r: 255, g: 4,   b: 0   }   // Red
        ];
    }else { // used for temperature, salinity, contaminant, ...
        colors = [
            { r: 0,   g: 0,   b: 255 }, // blue
            { r: 255, g: 165, b: 0   }, // orange
            { r: 255, g: 0,   b: 0   }  // red
        ];
    }
    const binCount = colors.length - 1;
    const scaledT = t * binCount;
    const lower = Math.floor(scaledT);
    const upper = Math.min(colors.length - 1, lower + 1);
    const frac = scaledT - lower;
    const c1 = colors[lower], c2 = colors[upper];
    const r = Math.round(c1.r + (c2.r - c1.r) * frac);
    const g = Math.round(c1.g + (c2.g - c1.g) * frac);
    const b = Math.round(c1.b + (c2.b - c1.b) * frac);
    return { r, g, b, a: 1 };
}

// Update color for colorbar
export function updateColorbar(min, max, title, colorbarKey, colorbarScaler, swap) {
    let color_colorbar = colorbar_color();
    let title_colorbar = colorbar_title();
    let label_colorbar = colorbar_label();
    if (colorbarScaler === 'vector') {
        color_colorbar = colorbar_vector_color();
        title_colorbar = colorbar_vector_title();
        label_colorbar = colorbar_vector_label();
        colorbar_vector_scaler().innerHTML = `Scaler: ${getScalerValue()}`;
    }
    title_colorbar.textContent = title;
    // Minimum difference
    const minDiff = 1e-2, epsilon = 1e-6;
    if (max - min < minDiff) max = min + minDiff;
    // Update 5 labels
    const labels = label_colorbar.children;
    for (let i = 0; i < 5; i++) {
        const percent = i / 4; // 0,0.25,0.5,0.75,1
        let value;
        if (min + epsilon > 0 && max + epsilon > 0) {
            const logMin = Math.log(min + epsilon);
            const logMax = Math.log(max + epsilon);
            value = Math.exp(logMax - percent * (logMax - logMin));
        } else {
            value = max - percent * (max - min);
        }
        labels[i].textContent = valueFormatter(value, minDiff);
    }
    // Generate color for colorbar
    const minColor = getColorFromValue(min, min, max, colorbarKey, swap);
    const midColor = getColorFromValue((min + max) / 2, min, max, colorbarKey, swap);
    const maxColor = getColorFromValue(max, min, max, colorbarKey, swap);
    // Update gradient
    const gradient = `linear-gradient(to top,
        rgb(${minColor.r}, ${minColor.g}, ${minColor.b}) 0%,
        rgb(${midColor.r}, ${midColor.g}, ${midColor.b}) 50%,
        rgb(${maxColor.r}, ${maxColor.g}, ${maxColor.b}) 100%
    )`;
    color_colorbar.style.background = gradient;
}

export function updateMapByTime(layerMap, timestamp, currentIndex, vmin, vmax, colorbarKey, swap) {
    const getColumnName = () => timestamp[currentIndex];
    const colorsCache = getLastFeatureColors();
    const featureMap = getFeatureMap();
    const featureIds = getMapLayer();
    for (let i = 0; i < featureIds.length; i++) {
        const id = featureIds[i];
        const feature = featureMap[id];
        if (!feature) continue;
        const value = feature.properties[getColumnName()];
        if (value === null || value === undefined) continue;
        const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey, swap);
        const colorKey = `${r},${g},${b},${a}`;
        if (colorsCache[id] === colorKey) continue;
        colorsCache[id] = colorKey;
        layerMap.setFeatureStyle(id, { 
            fill: true, fillColor: `rgb(${r},${g},${b})`, 
            fillOpacity: a, weight: 0, opacity: 1 
        });
    }
    setLastFeatureColors(colorsCache);
}

// Get min and max values from GeoJSON
export function getMinMaxFromGeoJSON(data, columns) {
    let globalMin = Infinity, globalMax = -Infinity;
    data.features.forEach(feature => {
        columns.forEach(field => {
            const value = feature.properties[field];
            if (typeof value === "number" && !isNaN(value)) {
                if (value < globalMin) globalMin = value;
                if (value > globalMax) globalMax = value;
            } else if (typeof value === 'string') {
                const temp = value.replace(/[()]/g, '');
                const parts = temp.split(',').map(s => parseFloat(s.trim()));
                const c = parts[2];
                if (typeof c === 'number') {
                    if (c < globalMin) globalMin = c;
                    if (c > globalMax) globalMax = c;
                }
            }
        });
    });
    if (!isFinite(globalMin)) globalMin = null;
    if (!isFinite(globalMax)) globalMax = null;
    return { min: globalMin, max: globalMax };
}

// Load data (including JSON and GeoJSON)
export async function loadData(filename, key){
    const response = await fetch('/process_data', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({data_filename: filename, key: key})});
    const data = await response.json();
    if (data.status === "error") {
        alert(data.message); return null;
    }
    return data;
}

export async function initOptions(comboBox, key) {
    startLoading(); 
    try {
        const response = await fetch('/initiate_options', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({key: key})});
        const data = await response.json();
        if (data.status === "ok") {
            // Add options to the object
            comboBox().innerHTML = '';
            // Add hint to the velocity object
            const hint = document.createElement('option');
            hint.value = ''; hint.selected = true;
            hint.text = '- No Selection -'; 
            comboBox().add(hint);
            // Add options
            data.content.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                comboBox().add(option);
            });
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    showLeafletMap();
}