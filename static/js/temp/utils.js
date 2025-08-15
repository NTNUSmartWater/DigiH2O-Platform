import { startLoading, showLeafletMap } from "./temp_mapManager.js";
import { getMapLayer, n_decimals } from "./temp_constants.js";


export let colorbar_title = () => document.getElementById("colorbar-title");
let colorbar_color = () => document.getElementById("colorbar-gradient");
let colorbar_label = () => document.getElementById("colorbar-labels");
const superscriptMap = {
    '-': '⁻', '0': '⁰', '1': '¹', '2': '²', '3': '³',
    '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
};
function toSuperscript(num) {
    return String(num).split('').map(ch => superscriptMap[ch] || ch).join('');
}

// Convert string to number
export function toNumber(val) {
    if (typeof val === 'string') {
        const num = Number(val);
        return isNaN(num) ? null : num;
    }
  return val;
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
    return Number((sumValues / sumWeughts).toFixed(n_decimals));
}

// Convert value to color
export function getColorFromValue(value, vmin, vmax, colorbarKey, swap) {
    if (typeof value !== 'number' || isNaN(value)) {
        return { r: 150, g: 150, b: 150, a: 0 };
    }
    if (vmin === vmax) return { r: 0, g: 0, b: 100, a: 1 };
    // Clamp value
    value = Math.max(vmin, Math.min(vmax, value));
    let t = (value - vmin) / (vmax - vmin);
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
export function updateColorbar(min, max, title, colorbarKey, swap) {
    colorbar_title().textContent = title;
    const midValue = (min + max) / 2;
    const minColor = getColorFromValue(min, min, max, colorbarKey, swap);
    const midColor = getColorFromValue(midValue, min, max, colorbarKey, swap);
    const maxColor = getColorFromValue(max, min, max, colorbarKey, swap);
    // Update gradient
    const gradient = `linear-gradient(to top,
        rgb(${minColor.r}, ${minColor.g}, ${minColor.b}) 0%,
        rgb(${midColor.r}, ${midColor.g}, ${midColor.b}) 50%,
        rgb(${maxColor.r}, ${maxColor.g}, ${maxColor.b}) 100%
    )`;
    colorbar_color().style.background = gradient;
    // Update 5 labels
    const labels = colorbar_label().children;
    let diffs = [];
    for (let i = 0; i < 4; i++) {
        const v1 = min + (max - min) * (1 - i / 4);
        const v2 = min + (max - min) * (1 - (i + 1) / 4);
        diffs.push(Math.abs(v1 - v2));
    }
    const minDiff = Math.min(...diffs);
    for (let i = 0; i < 5; i++) {
        const percent = i / 4; // 0.0, 0.25, ..., 1.0
        const value = min + (max - min) * (1 - percent); // Top to bottom
        labels[i].textContent = valueFormatter(value, minDiff);
    }
}

export function updateMapByTime(data, layerMap, timestamp, currentIndex, vmin, vmax, colorbarKey, swap) {
    const getColumnName = () => timestamp[currentIndex];
    getMapLayer().forEach(id => {
        const feature = data.features.find(f => f.properties.index === id);
        if (!feature) return;
        const value = feature.properties[getColumnName()];
        const { r, g, b, a } = getColorFromValue(value, vmin, vmax, colorbarKey, swap);
        layerMap.setFeatureStyle(id, { 
            fill: true, fillColor: `rgb(${r},${g},${b})`, 
            fillOpacity: a, weight: 0, opacity: 1 
        });
    });
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
            comboBox.innerHTML = '';
            // Add hint to the velocity object
            const hint_velocity = document.createElement('option');
            hint_velocity.value = ''; hint_velocity.selected = true;
            hint_velocity.textContent = '-- No Selected --'; 
            comboBox.add(hint_velocity);
            // Add options
            data.content.forEach(item => {
                const option = document.createElement('option');
                option.value = item; option.text = item;
                comboBox.add(option);
            });
        } else if (data.status === "error") {alert(data.message);}
    } catch (error) {alert(error);}
    showLeafletMap();
}

