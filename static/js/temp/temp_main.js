// Import necessary functions
import { initializeMap, baseMapButtonFunctionality } from './temp_mapManager.js';
import { stationCheck, initiateQueryManager } from './temp_queryManager.js';
import { openMenu, clickEvents, thermoclinePlot, chartPlots, plot2DStaticMap, plot2DDynamicMap } from './temp_uiManager.js';
import { toggleProjectSummary, projectSummaryEvents, closeProjectSummary } from './temp_projectSummaryManager.js';
import { plotEvents, closePlotChart } from './temp_chartManager.js';


// Events for map
initializeMap();
baseMapButtonFunctionality();
// Events for Menu
openMenu(); clickEvents();
// Events for Project Summary
toggleProjectSummary('summary.json');
projectSummaryEvents(); closeProjectSummary();
// Events for Points
stationCheck('stations.geojson');
initiateQueryManager();
// Plot Thermoclines
thermoclinePlot();
// Plot Charts
chartPlots();
// Plot 2D Maps
plot2DStaticMap(); plot2DDynamicMap();
// Actions for plots
plotEvents(); closePlotChart();
