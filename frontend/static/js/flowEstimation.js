import { getState, CENTER, ZOOM, L } from "./constants.js";


const leafletMap = () => document.getElementById('leaflet-map');
const compass = () => document.getElementById('compass');


let map = null;

function setupTabs(root) {
    const buttonPanels = root.querySelectorAll('.tab-btn');
    const panels = root.querySelectorAll('.main-panel');



    function activate(target) {
        const name = target.getAttribute('data-tab');
        // Set button aria-selected (highlighted)
        buttonPanels.forEach(btn => btn.setAttribute('aria-selected', String(btn === target)));
        // Show corresponding panel and hide others
        panels.forEach(p => {
            const panelNameActive = p.getAttribute('data-panel') === name;
            p.setAttribute('aria-hidden', String(!panelNameActive));
        })


    }


    // Click to change tab
    if(buttonPanels.length > 0) activate(buttonPanels[0]);
    buttonPanels.forEach(btn => {
        btn.addEventListener('click', () => { activate(btn); });
    });
    

}

function createMap() {
    map = L.map(leafletMap(), { center: CENTER, zoom: ZOOM, zoomControl: false, attributionControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
    L.control.scale({imperial: false, metric: true, maxWidth: 200}).addTo(map);
    setTimeout(() => { map.invalidateSize(); }, 100);
}

function update() {
    if (!map) { createMap(); }; compass().style.display = 'flex';






}

setupTabs(document); update();