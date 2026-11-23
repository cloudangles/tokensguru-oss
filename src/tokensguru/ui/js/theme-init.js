try {
  const theme = window.localStorage.getItem("tokensguru-docs-theme");
  if (theme === "light" || theme === "dark") document.documentElement.setAttribute("data-theme", theme);
} catch {
  /* storage can be blocked; the system theme is used */
}
