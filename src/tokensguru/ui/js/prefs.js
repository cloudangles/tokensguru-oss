const KEY = "tokensguru-docs-theme";
const ORDER = ["system", "light", "dark"];

export function storedTheme() {
  try {
    const value = window.localStorage.getItem(KEY);
    return ORDER.includes(value) ? value : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(theme) {
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
  try {
    window.localStorage.setItem(KEY, theme);
  } catch {
    /* storage can be blocked; the theme still applies for this visit */
  }
}

export function nextTheme(theme) {
  return ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
}

applyTheme(storedTheme());

export function readFlag(key) {
  try {
    return window.localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

export function writeFlag(key) {
  try {
    window.localStorage.setItem(key, "1");
  } catch {
    /* storage can be blocked; the choice only lasts for this visit */
  }
}
