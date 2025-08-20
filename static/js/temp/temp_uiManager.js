// Import necessary functions
import { initializeMap, baseMapButtonFunctionality } from './temp_mapManager.js';
import { plotChart, plotEvents } from './temp_chartManager.js';
import { plot2DMapStatic } from "./temp_2DMapManager.js";
import { deactivePointQuery, deactivePathQuery } from "./temp_queryManager.js";
import { generalObtionsManager } from './temp_generalOptionManager.js';
import { dynamicMapManager } from './temp_dynamicMapManager.js';


const popupMenu = () => document.getElementById('popup-menu');
const popupContent = () => document.getElementById('popup-content');



initializeMap();
baseMapButtonFunctionality();
initializeMenu();
updateEvents();
plotEvents();

// ============================ Functions ============================
async function showPopupMenu(id, htmlFile) {
    try {
        const response = await fetch(`/load_popupMenu?htmlFile=${htmlFile}`);
        const html = await response.text();
        popupContent().innerHTML = html;
        if (id === '0') generalObtionsManager('summary.json', 'stations.geojson'); // Events on general options submenu
        if (id === '1') measuredPointManager(); // Events on measured points submenu
        if (id === '2') dynamicMapManager(); // Events on dynamic map submenu
        if (id === '3') staticMapManager(); // Events on static map submenu
    } catch (error) {alert(error);}
}

function initializeMenu(){
    // Work with pupup menu
    document.querySelectorAll('.nav ul li a').forEach(link => {
        link.addEventListener('click', async(event) => {
            event.stopPropagation(); event.preventDefault();
            const rect = link.getBoundingClientRect();
            const pm = popupMenu();
            if (pm.classList.contains('show')) {
                pm.classList.remove('show');
            }
            const info = link.dataset.info;
            if (info === 'home') { history.back(); return; }
            if (info === 'help') { alert('This function is not implemented yet.'); return;}
            const [id, htmlFile] = info.split('|');
            showPopupMenu(id, htmlFile);
            pm.style.top = `${rect.bottom + 10 + window.scrollY}px`;
            pm.style.left = `${rect.left + window.scrollX}px`;
            pm.classList.add('show');
        });
    })
}

function updateEvents() {
    // Check if events are already bound
    if (window.__menuEventsBound) return;
    window.__menuEventsBound = true;
    const pm = popupMenu();
    if (pm){
        pm.addEventListener('mouseenter', () => pm.classList.add('show'));
        pm.addEventListener('mouseleave', () => pm.classList.remove('show'));
    }
    document.addEventListener('click', (e) => {
        // Close the popup menu if clicked outside
        if (pm && !pm.contains(e.target)) pm.classList.remove('show');
        // Toogle the menu if click on menu-link
        const link = e.target.closest('.menu-link');
        if (link){
            e.preventDefault(); e.stopPropagation();
            const submenu = link.nextElementSibling;
            if (submenu && submenu.classList.contains('submenu')){
                // Close other submenus and remove active on menu-links
                document.querySelectorAll('.submenu.open').forEach(s => {
                    if (s !== submenu) s.classList.remove('open');
                });
                document.querySelectorAll('.menu-link.active').forEach(l => {
                    if (l !== link) l.classList.remove('active');
                });
                // Toggle class open
                submenu.classList.toggle('open');
                link.classList.toggle('active');
            }
            return;
        }
        const link1 = e.target.closest('.menu-link-1');
        if (link1){
            e.preventDefault(); e.stopPropagation();
            const submenu1 = link1.nextElementSibling;
            if (submenu1 && submenu1.classList.contains('submenu-1')){
                // Close other submenus and remove active on menu-links
                document.querySelectorAll('.submenu-1.open').forEach(s => {
                    if (s !== submenu1) s.classList.remove('open');
                });
                document.querySelectorAll('.menu-link-1.active').forEach(l => {
                    if (l !== link1) l.classList.remove('active');
                });
                // Toggle class open
                submenu1.classList.toggle('open');
                link1.classList.toggle('active');
            }
            return;
        }
    });
    // Load default map
    plot2DMapStatic('depth_static.geojson', 'depth_static', 'Depth (m)', 'depth');
}

function measuredPointManager() {
    // Set function for plot using Plotly
    document.querySelectorAll('.function').forEach(plot => {
        plot.addEventListener('click', () => {
            const [filename, key, titleY, chartTitle] = plot.dataset.info.split('|');
            plotChart(filename, key, chartTitle, 'Time', titleY, false);
        });
    });
    
}

function staticMapManager() {
    deactivePathQuery(); deactivePointQuery(); 
    document.querySelectorAll('.map2D_static').forEach(plot => {
        plot.addEventListener('click', () => {
            const [filename, key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapStatic(filename, key, colorbarTitle, colorbarKey);
        });
    });
}
