console.log("Dark/Light theme switcher loaded into DOM.");
// Create or find the theme toggle button
function createThemeToggleButton() {
  if (document.getElementById("theme-toggle")) return;
  const btn = document.createElement("button");
  btn.id = "theme-toggle";
  btn.style.position = "fixed";
  btn.style.bottom = "20px";
  btn.style.right = "20px";
  btn.style.zIndex = "10000";
  btn.style.background = "#23272a";
  btn.style.color = "#fff";
  btn.style.border = "none";
  btn.style.borderRadius = "6px";
  btn.style.padding = "10px 18px";
  btn.style.fontSize = "1rem";
  btn.style.cursor = "pointer";
  btn.style.boxShadow = "0 2px 8px #0004";
  btn.style.transition = "background 0.2s";
  document.body.appendChild(btn);
}

// Theme logic
function setTheme(dark) {
  if (dark) {
    document.body.classList.add("dark-theme");
    localStorage.setItem("theme", "dark");
    document.getElementById("theme-toggle").textContent = "☀️ Light Mode";
  } else {
    document.body.classList.remove("dark-theme");
    localStorage.setItem("theme", "light");
    document.getElementById("theme-toggle").textContent = "🌙 Dark Mode";
  }
}

// On DOM ready
console.log("DOM for Themeswitcher Loaded");
document.addEventListener("DOMContentLoaded", function () {
  createThemeToggleButton();
  const saved = localStorage.getItem("theme");
  setTheme(saved === "dark");
  document.getElementById("theme-toggle").onclick = function () {
    setTheme(!document.body.classList.contains("dark-theme"));
  };
});
