import { getIsMenuOpen, setIsMenuOpen } from './temp_constants.js';
import { plotChart } from './temp_chartManager.js';
import { plot2DMapStatic, plot2DMapDynamic } from './temp_2DMapManager.js';
import { initOptions } from './utils.js';



const menuBtn = () => document.getElementById('menuBtn');
const menuPanel = () => document.getElementById('offCanvasMenu');
export const vectorObjectMain = () => document.getElementById("vector-object-main");
export const vectorObjectSubMain = () => document.getElementById("vector-object-submain");


// Close the menu if it is open
export function closeMenu() {
    menuPanel().style.width = "0"; setIsMenuOpen(false); 
}

// Function to toggle the menu
export function openMenu() {
    menuBtn().addEventListener('click', () => {
        menuPanel().style.width = getIsMenuOpen() ? "0" : "350px";
        setIsMenuOpen(!getIsMenuOpen());
    });
}

export function clickEvents() {
    // Move the control to the top right corner
    const scaleElem = document.querySelector('.leaflet-control-scale');
    document.getElementById('right-side-controls').appendChild(scaleElem);
    document.addEventListener('click', function(event) {       
        // Check if the menu button was clicked and close the menu if it was
        const isClickedInsideMenu = menuPanel().contains(event.target) || menuBtn().contains(event.target);
        if (!isClickedInsideMenu && getIsMenuOpen()) closeMenu();
    });

    // Get all menu-link having submenu
    document.querySelectorAll('.menu-link').forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            const submenu = this.nextElementSibling;
            if (!submenu) return; // No submenu found
            // Close other submenus and remove active on menu-links
            document.querySelectorAll('.submenu.open').forEach(openSubmenu => {
                if (openSubmenu !== submenu) {
                    openSubmenu.classList.remove('open');
                }
            });
            document.querySelectorAll('.menu-link.active').forEach(activeLink => {
                if (activeLink !== this) {
                    activeLink.classList.remove('active');
                }
            });
            // Toggle class open
            submenu.classList.toggle('open'); this.classList.toggle('active');
        });
    });

    document.querySelectorAll('.menu-link-1').forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            const submenu = this.nextElementSibling;
            if (!submenu) return; // No submenu found
            // Close other submenus and remove active on menu-links
            document.querySelectorAll('.submenu-1.open').forEach(openSubmenu => {
                if (openSubmenu !== submenu) {
                    openSubmenu.classList.remove('open');
                }
            });
            document.querySelectorAll('.menu-link-1.active').forEach(activeLink => {
                if (activeLink !== this) {
                    activeLink.classList.remove('active');
                }
            });
            // Toggle class open
            submenu.classList.toggle('open'); this.classList.toggle('active');
        });
    });

    vectorObjectMain().addEventListener('change', () => {
        changeVectorObject(vectorObjectMain().value);
    });

    // Initiate objects for vector object
    initOptions(vectorObjectMain(), 'vector');
    // Load default map
    plot2DMapStatic('depth_static.geojson', 'depth_static', 'Depth (m)', 'depth');
}

function changeVectorObject(value) {
    if (value === 'Velocity') {
        initOptions(vectorObjectSubMain(), 'velocity');
        vectorObjectSubMain().style.display = 'flex';
    } else {
        vectorObjectSubMain().innerHTML = '';
        vectorObjectSubMain().style.display = 'none';
    }
}

export function thermoclinePlot() {
    // Set function for plot using Plotly
    document.querySelectorAll('.thermocline').forEach(plot => {
        plot.addEventListener('click', () => {
            closeMenu();
            const [filename, titleY, chartTitle] = plot.dataset.info.split('|');
            plotChart(filename, 'thermocline', chartTitle, 'Temperature (°C)', titleY, 'All', true);
        });
    });
}

export function chartPlots(){
    // Set function for plot using Plotly
    document.querySelectorAll('.function').forEach(plot => {
        plot.addEventListener('click', () => {
            closeMenu();
            const [filename, key, titleY, chartTitle] = plot.dataset.info.split('|');
            plotChart(filename, key, chartTitle, 'Time', titleY, 'All', false);
        });
    });
}

export function plot2DDynamicMap(){
    // Set function for 2D plot
    document.querySelectorAll('.map2D_dynamic').forEach(plot => {
        plot.addEventListener('click', () => {
            closeMenu();
            const [filename, key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapDynamic(filename, key, colorbarTitle, colorbarKey);
        });
    });
}

export function plot2DStaticMap(){
    // Set function for 2D plot
    document.querySelectorAll('.map2D_static').forEach(plot => {
        plot.addEventListener('click', () => {
            closeMenu();
            const [filename, key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapStatic(filename, key, colorbarTitle, colorbarKey);
        });
    });
}