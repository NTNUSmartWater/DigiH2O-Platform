async function loadTooltips(jsonPath) {
  const response = await fetch(jsonPath);
  const tooltips = await response.json();
  // Add tooltips
  Object.entries(tooltips).forEach(([description, ids]) => {
    ids.forEach(id => {
      const element = document.getElementById(id);
      if (element) {
        // Customize tooltip
        element.addEventListener("mouseenter", (e) => {
          const tooltip = document.createElement("div");
          tooltip.className = "custom-tooltip";
          tooltip.innerText = description;
          tooltip.style.position = "absolute";
          tooltip.style.background = "#2c2a2aff";
          tooltip.style.color = "#fceb03ff";
          tooltip.style.padding = "5px 10px";
          tooltip.style.borderRadius = "4px";
          tooltip.style.fontSize = "14px";
          tooltip.style.pointerEvents = "none";
          tooltip.style.zIndex = "1000";
          tooltip.style.lineHeight = "1.8";
          // Set tooltip position
          const rect = element.getBoundingClientRect();
          tooltip.style.top = rect.bottom + window.scrollY + 5 + "px";
          tooltip.style.left = rect.left + window.scrollX + 5 + "px";
          document.body.appendChild(tooltip);
          // Hide tooltip after 2 seconds
          const hideTimer = setTimeout(() => { tooltip.remove(); }, 10000);
          element.addEventListener("mouseleave", () => {
            clearTimeout(hideTimer); tooltip.remove();
          }, { once: true });
          element.addEventListener("click", () => {});
        });
      }
    });
  });
}
loadTooltips('/static_backend/samples/tooltips.json');