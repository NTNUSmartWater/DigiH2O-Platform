import { getState } from "./constants.js";

export let map;
let currentTileLayer = null, timerCounter;
const CENTER = [62.476969, 6.471598];
export const ZOOM = 13;
export const L = window.L;
export const loading = () => document.getElementById('loadingOverlay');
export const leaflet_map = () => document.getElementById('leaflet_map');

export async function initializeMap() {
    startLoading('Setting up map...');
    map = setupMap();
    setupMapEventListeners();
    showLeafletMap();
    map.invalidateSize(); // Ensure map is displayed correctly after loading
}

// Show spinner when loading
export function startLoading(str = 'Processing Data. Please wait...') {
    loading().querySelector('.loading-text').textContent = str;
    loading().style.display = 'flex';
    leaflet_map().style.display = 'none';
}
export function showLeafletMap() {
    leaflet_map().style.display = "block";
    loading().style.display = "none";
}

export function baseMapButtonFunctionality() {
    const baseMapBtn = document.getElementById('custom_map_background_btn');
    const popup = document.getElementById('basemap-popup');
    baseMapBtn.addEventListener('mouseenter', () => {
        popup.classList.add('show');
        clearTimeout(timerCounter);
        // Hide the popup after 2 seconds
        timerCounter = setTimeout(() => {
            popup.classList.remove('show');
        }, 2000);
    });
    // Add event listeners to the base map buttons
    document.querySelectorAll('.basemap-option').forEach(button => {
        button.addEventListener('click', () => {
            const url = button.getAttribute('data-url');
            switchBaseMapLayer(url);
            popup.classList.remove('show');
            clearTimeout(timerCounter);
        });
    });
}

// change the base map
export function switchBaseMapLayer(url) {
    if (currentTileLayer) map.removeLayer(currentTileLayer);
    currentTileLayer = L.tileLayer(url, {zIndex: 0});
    currentTileLayer.addTo(map);
}

// Generate the map
export function setupMap() {
    map = L.map('leaflet_map', {center:CENTER, zoom: ZOOM,
        zoomControl: false, attributionControl: true});
    currentTileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    // Add scale bar
    L.control.scale({imperial: false, metric: true, maxWidth: 200}).addTo(map);
    return map;
}

export function setupMapEventListeners() {
    const hoverTooltip = L.tooltip({
        permanent: false, direction: 'bottom',
        sticky: true, offset: [0, 10], className: 'custom-tooltip'
    });
    // Add tooltip
    map.on('mousemove', function (e) {
        if (getState().isPathQuery) {
            const html = `- Click the left mouse button to draw lines.<br>- Right-click to finish the selection.`;
            hoverTooltip.setLatLng(e.latlng).setContent(html);
            map.openTooltip(hoverTooltip);
        } else if (getState().isThemocline) {
            const html = `- Click the left mouse button to select a point.<br>- Then change the name (optional).`;
            hoverTooltip.setLatLng(e.latlng).setContent(html);
            map.openTooltip(hoverTooltip);
        } 
        if (!getState().isPathQuery && !getState().isThemocline) { map.closeTooltip(hoverTooltip); return; }
    });
}
