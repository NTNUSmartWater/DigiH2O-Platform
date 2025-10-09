import { plot2DMapStatic } from "./map2DManager.js";

export function spatialMapManager() {
    





    
    // Select static map
    document.querySelectorAll('.map2D_static').forEach(plot => {
        plot.addEventListener('click', () => {
            const [key, colorbarTitle, colorbarKey] = plot.dataset.info.split('|');
            plot2DMapStatic(key, colorbarTitle, colorbarKey);
        });
    });
}