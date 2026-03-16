export function getChartThemeColors() {
  const isLight = document.documentElement.dataset.theme === "light";
  return {
    grid: isLight ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.1)",
    accent: isLight ? "#8a7e74" : "#818cf8",
    refLine: isLight ? "rgba(0,0,0,0.25)" : "rgba(255,255,255,0.5)",
  };
}
