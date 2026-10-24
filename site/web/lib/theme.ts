export const THEME_STORAGE_KEY = "xi-archive:theme";

// Run before the body is painted so a saved dark theme does not flash light.
export const THEME_INIT_SCRIPT = `(() => {
  let theme;
  try {
    const saved = localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});
    if (saved === "light" || saved === "dark") theme = saved;
  } catch {}
  if (!theme) theme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
})();`;
