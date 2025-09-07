export function copyPaste(table, nCols){
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    table.addEventListener('paste', (e) => {
        e.preventDefault();
        const text = (e.clipboardData || window.Clipboard).getData('text'); // Get clipboard data
        const rows = text.split(/\r?\n/).filter(row => row.trim() !== ''); // Split into rows
        if (rows.length === 0) return;
        const data_arr = rows.map(row => row.split(/\t|,/).slice(0, nCols)); // Split into columns
        fillTable(data_arr, table);
    });
}

export function fillTable(data2D, table, clear=true){
    const numRows = data2D.length;
    const numCols = data2D[0].length;
    let tbody = table.querySelector("tbody");
    if (clear) {
        // Delete old table
        const newTbody = document.createElement("tbody");
        tbody.replaceWith(newTbody);
        tbody = newTbody;
    }
    // Add new rows to table
    for (let i = 0; i < numRows; i++) {
        const row = document.createElement("tr");
        for (let j = 0; j < numCols; j++) {
            const td = document.createElement("td");
            const input = document.createElement("input");
            input.type = "text";
            input.value = data2D[i][j];
            td.appendChild(input);
            row.appendChild(td);
        }
        tbody.appendChild(row);
    }
}

export function getDataFromTable(table, isZeroIndexString=false){
    const columns = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim());
    const rows = Array.from(table.querySelectorAll("tbody tr")).map(tr => {
        return Array.from(tr.querySelectorAll("td input")).map((input, idx) => {
            const val = input.value.trim();
            if (isZeroIndexString) return val; // Keep as string
            // Convert to number if possible
            if (idx === 0 && val) {
                const isoString = val.replace(/\//g, "-").replace(" ", "T");
                return new Date(isoString);
            }
            // if (!isNaN(val) && val !== "") return parseFloat(val);
            return val;
        });
    });
    return {columns, rows};
}

export function removeRowFromTable(table, name){
    if (name.trim() === '') { alert('Please define name of the observation point to remove.'); return; }
    // Remove row with matching name
    const tbody = table.querySelector("tbody");
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll("tr"));
    const rowToRemove = rows.find(row => {{
        const firstCell = row.querySelector("td");
        if (!firstCell) return false;
        const input = firstCell.querySelector("input");
        if (!input) return false;
        const cellText = input ? input.value.trim() : firstCell.textContent.trim();
        return cellText === name;
    }});
    if (rowToRemove) { rowToRemove.remove(); alert(`Observation point "${name}" removed.`);
    } else { alert(`Observation point "${name}" not found.`); }
}

export function tableClear(target, table){
    target.addEventListener('change', () => {
        const tbody = table.querySelector("tbody");
        tbody.innerHTML = "";
        document.getElementById('observation-point-csv').value = "";
    });
}

export function deleteTable(target, table, name=null, type=''){
    target.addEventListener('click', () => {
        const tbody = table.querySelector("tbody");
        tbody.innerHTML = ""; 
        if (name != null) name.value = '';
        window.parent.postMessage({type: type}, '*');
    });
}

export function renderProjects(object, fullList, filter) {
    object.innerHTML = ""; // clear
    const filtered = fullList.filter(p => p.toLowerCase().includes(filter.toLowerCase()));
    filtered.forEach(p => {
        const li = document.createElement("li");
        li.textContent = p;
        object.appendChild(li);
    });
    object.style.display = filter ? "block" : "none";
}

export function csvUploader(target, table, nCols, isIgnoreHeader=true, objName=null, latitude=null, longitude=null){
    target.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const lines = text.split('\n').map(line => line.trim()).filter(line => line !== '');
            const parts = lines[0].split(',').map(item => item.trim());
            if (parts.length !== nCols) { alert('Number of columns should be ' + nCols + '.'); target.value = ''; return; }
            let dataLines = lines;
            if (isIgnoreHeader) dataLines = dataLines.slice(1); // Skip header
            dataLines.forEach((line, idx) => {
                const parts = line.split(',').map(item => item.trim());
                let data_arr = [];
                if (parts.length === 2) {
                    data_arr = [[parts[0], parseFloat(parts[1])]];
                } else if (parts.length === 3) {
                    data_arr = [[parts[0], parseFloat(parts[1]), parseFloat(parts[2])]];
                } else if (parts.length === 5) {
                    objName.value = file.name.replace('.csv', ''); 
                    if (idx === 0) {
                        latitude.value = parts[0]; longitude.value = parts[1];
                    } else if (idx === 1) {
                        return;
                    } else {
                        data_arr = [[parts[0], parseFloat(parts[1]), parseFloat(parts[2]), 
                                parseFloat(parts[3]), parseFloat(parts[4])]];
                    }
                }
                if (data_arr.length === 0) return;
                fillTable(data_arr, table, false);
            })
        }
        reader.readAsText(file);
    })
}
export function mapPicker(obj, type, content=null){
    const handler = () => {
        const freshData = typeof content === 'function' ? content() : content;
        window.parent.postMessage({type: type, data: freshData}, '*');
    };
    if (obj.__mapPickerHandler) {
        obj.removeEventListener('click', obj.__mapPickerHandler);
    }
    obj.__mapPickerHandler = handler;
    obj.addEventListener('click', handler);
}
